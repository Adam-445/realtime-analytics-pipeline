from typing import Dict

from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.clickhouse.client import ClickHouseCacheWarmer
from src.infrastructure.redis.client import RedisMetricsRepository

logger = get_logger("cache_warmer")


class CacheWarmingService:
    """Service to warm cache with historical data from ClickHouse"""

    def __init__(
        self,
        clickhouse_client: ClickHouseCacheWarmer | None = None,
        redis_repo: RedisMetricsRepository | None = None,
    ):
        self.ch_client = clickhouse_client or ClickHouseCacheWarmer()
        self.redis_repo = redis_repo or RedisMetricsRepository()

    async def warm_cache_on_startup(self):
        """Warm cache with recent historical data on service startup"""
        if not settings.enable_cache_warming:
            logger.info("Cache warming disabled, skipping")
            return

        logger.info(
            "Starting cache warming process",
            extra={"window_hours": settings.cache_warming_window_hours},
        )

        try:
            # Warm event metrics
            await self._warm_event_metrics()

            # Warm session metrics
            await self._warm_session_metrics()

            # Warm performance metrics
            await self._warm_performance_metrics()

            logger.info("Cache warming completed successfully")

        except Exception as e:
            logger.error("Cache warming failed", extra={"error": str(e)})

    async def _warm_event_metrics(self):
        """Warm cache with event metrics from ClickHouse"""
        logger.info("Warming event metrics cache")

        try:
            metrics = await self.ch_client.warm_event_metrics()
            if metrics:
                # Convert and cache the metrics
                formatted_metrics = []
                for metric in metrics:
                    # Convert datetime objects to strings for Redis storage
                    formatted_metric = {
                        "event_type": metric["event_type"],
                        "event_count": metric["event_count"],
                        "user_count": metric["user_count"],
                        "window_start": int(metric["window_start"].timestamp()),
                        "window_end": int(metric["window_end"].timestamp()),
                    }
                    formatted_metrics.append(formatted_metric)

                self.redis_repo.cache_flink_event_metrics(formatted_metrics)
                logger.info(
                    "Event metrics cache warmed",
                    extra={"metrics_count": len(formatted_metrics)},
                )
            else:
                logger.info("No event metrics found for warming")

        except Exception as e:
            logger.error("Failed to warm event metrics cache", extra={"error": str(e)})

    async def _warm_session_metrics(self):
        """Warm cache with session metrics from ClickHouse"""
        logger.info("Warming session metrics cache")

        try:
            metrics = await self.ch_client.warm_session_metrics()
            if metrics:
                # Convert and cache the metrics
                formatted_metrics = []
                for metric in metrics:
                    formatted_metric = {
                        "session_id": metric["session_id"],
                        "user_id": metric["user_id"],
                        "start_time": metric["start_time"],
                        "end_time": metric["end_time"],
                        "duration": metric["duration"],
                        "page_count": metric["page_count"],
                        "device_category": metric["device_category"],
                    }
                    formatted_metrics.append(formatted_metric)

                self.redis_repo.cache_flink_session_metrics(formatted_metrics)
                logger.info(
                    "Session metrics cache warmed",
                    extra={"metrics_count": len(formatted_metrics)},
                )
            else:
                logger.info("No session metrics found for warming")

        except Exception as e:
            logger.error(
                "Failed to warm session metrics cache", extra={"error": str(e)}
            )

    async def _warm_performance_metrics(self):
        """Warm cache with performance metrics from ClickHouse"""
        logger.info("Warming performance metrics cache")

        try:
            metrics = await self.ch_client.warm_performance_metrics()
            if metrics:
                # Convert and cache the metrics
                formatted_metrics = []
                for metric in metrics:
                    formatted_metric = {
                        "device_category": metric["device_category"],
                        "avg_load_time": metric["avg_load_time"],
                        "p95_load_time": metric["p95_load_time"],
                        "window_start": int(metric["window_start"].timestamp()),
                        "window_end": int(metric["window_end"].timestamp()),
                    }
                    formatted_metrics.append(formatted_metric)

                self.redis_repo.cache_flink_performance_metrics(formatted_metrics)
                logger.info(
                    "Performance metrics cache warmed",
                    extra={"metrics_count": len(formatted_metrics)},
                )
            else:
                logger.info("No performance metrics found for warming")

        except Exception as e:
            logger.error(
                "Failed to warm performance metrics cache", extra={"error": str(e)}
            )

    async def get_or_cache_historical_event_count(
        self, dimensions: Dict[str, str], window_seconds: int
    ) -> int:
        """Get event count with fallback to ClickHouse and caching"""
        # Create cache key
        dim_str = "&".join(f"{k}={v}" for k, v in sorted(dimensions.items()))
        cache_key = f"event_count:{dim_str}:{window_seconds}"

        # Try cache first
        cached_value = self.redis_repo.get_historical_data(cache_key)
        if cached_value is not None:
            logger.debug(
                "Cache hit for historical event count",
                extra={"cache_key": cache_key, "value": cached_value},
            )
            return cached_value

        # Fallback to ClickHouse
        logger.debug(
            "Cache miss, fetching from ClickHouse", extra={"cache_key": cache_key}
        )

        try:
            value = await self.ch_client.get_historical_event_count(
                dimensions, window_seconds
            )

            # Cache the result
            self.redis_repo.cache_historical_data(cache_key, value)

            logger.debug(
                "Historical event count cached",
                extra={"cache_key": cache_key, "value": value},
            )

            return value

        except Exception as e:
            logger.error(
                "Failed to get historical event count",
                extra={"error": str(e), "dimensions": dimensions},
            )
            return 0

    def cleanup(self):
        """Clean up resources"""
        try:
            self.ch_client.close()
        except Exception as e:
            logger.warning("Error during cache warmer cleanup", extra={"error": str(e)})
