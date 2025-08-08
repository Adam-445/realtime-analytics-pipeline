import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.redis.client import RedisMetricsRepository
from src.metrics.bucketing import enumerate_bucket_starts
from src.metrics.key_hash import dimensions_hash
from src.services.cache_warming import CacheWarmingService

router = APIRouter()
logger = get_logger(__name__)


def get_redis_repo() -> RedisMetricsRepository:
    """Dependency to get Redis repository"""
    return RedisMetricsRepository()


def get_cache_warmer() -> CacheWarmingService:
    """Dependency to get cache warming service"""
    if not settings.enable_cache_warming:
        raise HTTPException(status_code=503, detail="Cache warming service is disabled")
    return CacheWarmingService()


@router.get("/event_count")
async def get_event_count(
    app_id: str | None = Query(None),
    event_type: str | None = Query(None),
    country: str | None = Query(None),
    window_seconds: int = Query(60),
    use_flink_cache: bool = Query(False, description="Use Flink processed metrics"),
    repo: RedisMetricsRepository = Depends(get_redis_repo),
):
    """Get event count with multi-layer caching support"""
    if window_seconds not in settings.supported_windows_seconds:
        raise HTTPException(status_code=400, detail="Unsupported window")

    dimensions = {}
    if app_id:
        dimensions["app_id"] = app_id
    if event_type:
        dimensions["event_type"] = event_type
    if country:
        dimensions["country"] = country

    now_s = int(time.time())

    # Try Flink cache first if requested and event_type is provided
    if use_flink_cache and event_type:
        try:
            flink_data = repo.get_flink_event_metrics_window(event_type, window_seconds)
            if flink_data["event_count"] > 0:
                return {
                    "metric": "event_count",
                    "dimensions": dimensions,
                    "window_seconds": window_seconds,
                    "value": flink_data["event_count"],
                    "source": "flink_cache",
                    "as_of_epoch_s": now_s,
                }
        except Exception:
            pass  # Fallback to raw metrics

    # Fallback to raw metrics aggregation
    dim_hash = dimensions_hash(dimensions)
    bucket_starts = enumerate_bucket_starts(
        end_timestamp_seconds=now_s,
        window_seconds=window_seconds,
        granularity_seconds=settings.bucket_granularity_seconds,
    )

    # Try raw cache
    value = repo.get_event_count_window(dim_hash, bucket_starts)

    # If no data in cache and window is large, try historical data
    if (
        value == 0 and window_seconds > 300 and settings.enable_cache_warming
    ):  # 5+ minutes
        try:
            cache_warmer = CacheWarmingService()
            value = await cache_warmer.get_or_cache_historical_event_count(
                dimensions, window_seconds
            )
            source = "historical_cache"
        except Exception as e:
            logger.warning(f"Failed to get historical data: {e}")
            source = "raw_cache"
    else:
        source = "raw_cache"

    return {
        "metric": "event_count",
        "dimensions": dimensions,
        "window_seconds": window_seconds,
        "value": value,
        "buckets_aggregated": len(bucket_starts),
        "granularity_seconds": settings.bucket_granularity_seconds,
        "source": source,
        "as_of_epoch_s": now_s,
    }


@router.get("/performance_metrics")
async def get_performance_metrics(
    window: str = "5m", repo: RedisMetricsRepository = Depends(get_redis_repo)
):
    """Get performance metrics with multi-layer caching fallback"""
    try:
        # First, try L2 cache (Flink metrics)
        l2_key = f"flink:performance_metrics:window:{window}"
        l2_data = repo._client.get(l2_key)

        if l2_data:
            metrics = json.loads(l2_data)
            metrics["source"] = "flink_cache"
            return metrics

        # Return empty metrics if no data available
        return {
            "avg_response_time": 0,
            "event_throughput": 0,
            "error_rate": 0.0,
            "active_sessions": 0,
            "window": window,
            "source": "empty",
        }

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.get("/cache_stats")
async def get_cache_stats(repo: RedisMetricsRepository = Depends(get_redis_repo)):
    """Get cache statistics and health info"""
    try:
        stats = repo.get_cache_stats()

        # Calculate hit ratio
        total_ops = stats["keyspace_hits"] + stats["keyspace_misses"]
        hit_ratio = stats["keyspace_hits"] / total_ops if total_ops > 0 else 0

        return {
            "cache_stats": stats,
            "hit_ratio": round(hit_ratio, 4),
            "total_operations": total_ops,
            "supported_windows": settings.supported_windows_seconds,
            "max_window": settings.max_window_seconds,
            "as_of_epoch_s": int(time.time()),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve cache stats: {str(e)}"
        )


def _common_hll_lookup(
    metric: str,
    app_id: str | None,
    event_type: str | None,
    country: str | None,
    window_seconds: int,
    repo: RedisMetricsRepository,
):
    if window_seconds not in settings.supported_windows_seconds:
        raise HTTPException(status_code=400, detail="Unsupported window")
    dimensions = {}
    if app_id:
        dimensions["app_id"] = app_id
    if event_type:
        dimensions["event_type"] = event_type
    if country:
        dimensions["country"] = country
    dim_hash = dimensions_hash(dimensions)
    now_s = int(time.time())
    bucket_starts = enumerate_bucket_starts(
        end_timestamp_seconds=now_s,
        window_seconds=window_seconds,
        granularity_seconds=settings.bucket_granularity_seconds,
    )
    value = repo.merge_hll_window(metric, dim_hash, bucket_starts)
    return {
        "metric": metric,
        "dimensions": dimensions,
        "window_seconds": window_seconds,
        "value": value,
        "buckets_aggregated": len(bucket_starts),
        "granularity_seconds": settings.bucket_granularity_seconds,
        "source": "raw_cache",
        "as_of_epoch_s": now_s,
    }


@router.get("/unique_users")
def get_unique_users(
    app_id: str | None = Query(None),
    event_type: str | None = Query(None),
    country: str | None = Query(None),
    window_seconds: int = Query(60),
    repo: RedisMetricsRepository = Depends(get_redis_repo),
):
    return _common_hll_lookup(
        metric="unique_users",
        app_id=app_id,
        event_type=event_type,
        country=country,
        window_seconds=window_seconds,
        repo=repo,
    )


@router.get("/active_sessions")
def get_active_sessions(
    app_id: str | None = Query(None),
    event_type: str | None = Query(None),
    country: str | None = Query(None),
    window_seconds: int = Query(60),
    repo: RedisMetricsRepository = Depends(get_redis_repo),
):
    return _common_hll_lookup(
        metric="active_sessions",
        app_id=app_id,
        event_type=event_type,
        country=country,
        window_seconds=window_seconds,
        repo=repo,
    )
