import time
from typing import Any, Dict, List, Union

import redis
from src.core.config import settings


class RedisMetricsRepository:
    def __init__(self):
        self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self._raw_ttl = settings.raw_metrics_ttl_seconds
        self._flink_ttl = settings.flink_metrics_ttl_seconds
        self._historical_ttl = settings.historical_cache_ttl_seconds

    # ===== Real-time Raw Event Metrics (L1 Cache) =====
    def incr_event_count(self, dim_hash: str, bucket_start: int, amount: int = 1):
        key = f"metrics:event_count:{dim_hash}:{bucket_start}"
        pipe = self._client.pipeline()
        pipe.incrby(key, amount)
        pipe.expire(key, self._raw_ttl)
        pipe.execute()

    def add_hll(self, metric: str, dim_hash: str, bucket_start: int, value: str):
        key = f"metrics:{metric}:{dim_hash}:{bucket_start}"
        pipe = self._client.pipeline()
        pipe.pfadd(key, value)
        pipe.expire(key, self._raw_ttl)
        pipe.execute()

    def get_event_count_window(self, dim_hash: str, bucket_starts: List[int]) -> int:
        keys = [f"metrics:event_count:{dim_hash}:{b}" for b in bucket_starts]
        if not keys:
            return 0
        values = self._client.mget(keys)
        total = 0
        for v in values:
            if v is not None:
                try:
                    total += int(v)
                except (ValueError, TypeError):
                    continue
        return total

    def merge_hll_window(
        self, metric: str, dim_hash: str, bucket_starts: List[int]
    ) -> int:
        keys = [f"metrics:{metric}:{dim_hash}:{b}" for b in bucket_starts]
        if not keys:
            return 0
        if len(keys) == 1:
            try:
                result = self._client.pfcount(keys[0])
                return int(result) if result else 0
            except (ValueError, TypeError):
                return 0

        temp_key = f"tmp:merge:{metric}:{dim_hash}:{int(time.time()*1000)}"
        self._client.execute_command("PFMERGE", temp_key, *keys)
        try:
            count = self._client.pfcount(temp_key)
            self._client.delete(temp_key)
            return int(count) if count else 0
        except (ValueError, TypeError):
            self._client.delete(temp_key)
            return 0

    # ===== Flink Processed Metrics (L2 Cache) =====
    def cache_flink_event_metrics(self, metrics: List[Dict[str, Any]]):
        """Cache Flink-processed event metrics"""
        if not metrics:
            return
        pipe = self._client.pipeline()
        for metric in metrics:
            key = f"flink:event_metrics:{metric['event_type']}:{metric['window_start']}"
            pipe.hset(
                key,
                mapping={
                    "event_count": str(metric["event_count"]),
                    "user_count": str(metric["user_count"]),
                    "window_end": str(metric["window_end"]),
                },
            )
            pipe.expire(key, self._flink_ttl)
        pipe.execute()

    def cache_flink_session_metrics(self, metrics: List[Dict[str, Any]]):
        """Cache Flink-processed session metrics"""
        if not metrics:
            return
        pipe = self._client.pipeline()
        for metric in metrics:
            key = f"flink:session_metrics:{metric['session_id']}"
            pipe.hset(
                key,
                mapping={
                    "user_id": str(metric["user_id"]),
                    "start_time": str(metric["start_time"]),
                    "end_time": str(metric["end_time"]),
                    "duration": str(metric["duration"]),
                    "page_count": str(metric["page_count"]),
                    "device_category": str(metric["device_category"]),
                },
            )
            pipe.expire(key, self._flink_ttl)
        pipe.execute()

    def cache_flink_performance_metrics(self, metrics: List[Dict[str, Any]]):
        """Cache Flink-processed performance metrics"""
        if not metrics:
            return
        pipe = self._client.pipeline()
        for metric in metrics:
            device_cat = metric["device_category"]
            window_start = metric["window_start"]
            key = f"flink:performance_metrics:{device_cat}:{window_start}"
            pipe.hset(
                key,
                mapping={
                    "avg_load_time": str(metric["avg_load_time"]),
                    "p95_load_time": str(metric["p95_load_time"]),
                    "window_end": str(metric["window_end"]),
                },
            )
            pipe.expire(key, self._flink_ttl)
        pipe.execute()

    # ===== Historical Data Cache (L3 Cache) =====
    def cache_historical_data(self, cache_key: str, data: Any):
        """Cache historical data from ClickHouse with shorter TTL"""
        key = f"historical:{cache_key}"
        self._client.setex(key, self._historical_ttl, str(data))

    def get_historical_data(self, cache_key: str) -> Union[int, None]:
        """Get cached historical data"""
        key = f"historical:{cache_key}"
        try:
            data = self._client.get(key)
            return int(data) if data else None
        except (ValueError, TypeError):
            return None

    def get_flink_event_metrics_window(
        self, event_type: str, window_seconds: int
    ) -> Dict[str, Any]:
        """Get aggregated Flink event metrics for a time window"""
        end_time = int(time.time())
        start_time = end_time - window_seconds

        pattern = f"flink:event_metrics:{event_type}:*"
        keys = []
        for key in self._client.scan_iter(match=pattern):
            try:
                timestamp = int(key.split(":")[-1])
                if start_time <= timestamp <= end_time:
                    keys.append(key)
            except (ValueError, IndexError):
                continue

        if not keys:
            return {"event_count": 0, "user_count": 0}

        total_events = 0
        total_users = 0

        for key in keys:
            try:
                data = self._client.hgetall(key)
                if data:
                    event_count = data.get("event_count", "0")
                    user_count = data.get("user_count", "0")
                    total_events += int(event_count)
                    total_users += int(user_count)
            except (ValueError, TypeError):
                continue

        return {"event_count": total_events, "user_count": total_users}

    def get_flink_performance_metrics_window(
        self, device_category: str, window_seconds: int
    ) -> Dict[str, Any]:
        """Get aggregated Flink performance metrics for a time window"""
        end_time = int(time.time())
        start_time = end_time - window_seconds

        pattern = f"flink:performance_metrics:{device_category}:*"
        keys = []
        for key in self._client.scan_iter(match=pattern):
            try:
                timestamp = int(key.split(":")[-1])
                if start_time <= timestamp <= end_time:
                    keys.append(key)
            except (ValueError, IndexError):
                continue

        if not keys:
            return {"avg_load_time": 0, "p95_load_time": 0}

        load_times = []
        p95_times = []

        for key in keys:
            try:
                data = self._client.hgetall(key)
                if data:
                    avg_load = float(data.get("avg_load_time", "0"))
                    p95_load = float(data.get("p95_load_time", "0"))
                    if avg_load > 0:
                        load_times.append(avg_load)
                    if p95_load > 0:
                        p95_times.append(p95_load)
            except (ValueError, TypeError):
                continue

        return {
            "avg_load_time": sum(load_times) / len(load_times) if load_times else 0,
            "p95_load_time": sum(p95_times) / len(p95_times) if p95_times else 0,
        }

    # ===== Cache Management =====
    def invalidate_pattern(self, pattern: str):
        """Invalidate cache keys matching a pattern"""
        keys = list(self._client.scan_iter(match=pattern))
        if keys:
            self._client.delete(*keys)

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        try:
            info = self._client.info()
            return {
                "connected_clients": int(info.get("connected_clients", 0)),
                "used_memory": int(info.get("used_memory", 0)),
                "keyspace_hits": int(info.get("keyspace_hits", 0)),
                "keyspace_misses": int(info.get("keyspace_misses", 0)),
            }
        except Exception:
            return {
                "connected_clients": 0,
                "used_memory": 0,
                "keyspace_hits": 0,
                "keyspace_misses": 0,
            }
