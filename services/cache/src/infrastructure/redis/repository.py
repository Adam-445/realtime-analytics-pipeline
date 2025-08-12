from typing import Any, Dict, List, Optional

from redis.asyncio import Redis
from src.domain.operations import Operation

from . import constants


class CacheRepository:
    """Redis-backed repository for metrics windows & related entities.

    Notes:
        - Uses simple sorted-set indices to maintain recency ordering.
        - Keeps retention bounded by window_retention_count per type.
        - Performs batched writes via pipeline for efficiency.
    """

    def __init__(self, redis: Redis, window_retention_count: int, window_hash_ttl: int):
        self.r = redis
        self.window_retention_count = window_retention_count
        self.window_hash_ttl = window_hash_ttl

    # Store methods
    async def store_event_window(self, window_start_ms: int, fields: Dict[str, Any]):
        key = constants.WINDOW_EVENT_HASH.format(window_start=window_start_ms)
        await self.r.hset(key, mapping=fields)  # type: ignore[arg-type]
        await self.r.expire(key, self.window_hash_ttl)
        await self.r.zadd(
            constants.WINDOW_EVENT_INDEX,
            {str(window_start_ms): window_start_ms},
        )
        await self._trim_index(constants.WINDOW_EVENT_INDEX)

    async def store_performance_window(
        self, window_start_ms: int, fields: Dict[str, Any]
    ):
        key = constants.WINDOW_PERF_HASH.format(window_start=window_start_ms)
        await self.r.hset(key, mapping=fields)  # type: ignore[arg-type]
        await self.r.expire(key, self.window_hash_ttl)
        await self.r.zadd(
            constants.WINDOW_PERF_INDEX,
            {str(window_start_ms): window_start_ms},
        )
        await self._trim_index(constants.WINDOW_PERF_INDEX)

    # Batch / Pipeline
    async def pipeline_apply(self, ops: List[Operation]):
        """Apply a batch of operations using a pipeline.

        Each op dict: {"type": "event"|"perf", "window_start": int, "fields": {...}}
        """
        if not ops:
            return
        pipe = self.r.pipeline(transaction=False)
        saw_event = False
        saw_perf = False
        for op in ops:
            w = op["window_start"]
            if op["type"] == "event":
                saw_event = True
                key = constants.WINDOW_EVENT_HASH.format(window_start=w)
                pipe.hset(key, mapping=op["fields"])  # type: ignore[arg-type]
                pipe.expire(key, self.window_hash_ttl)
                pipe.zadd(constants.WINDOW_EVENT_INDEX, {str(w): w})
            elif op["type"] == "perf":
                saw_perf = True
                key = constants.WINDOW_PERF_HASH.format(window_start=w)
                pipe.hset(key, mapping=op["fields"])  # type: ignore[arg-type]
                pipe.expire(key, self.window_hash_ttl)
                pipe.zadd(constants.WINDOW_PERF_INDEX, {str(w): w})
        # Execute writes
        await pipe.execute()
        # Trim only indices that were touched in this batch
        if saw_event:
            await self._trim_index(constants.WINDOW_EVENT_INDEX)
        if saw_perf:
            await self._trim_index(constants.WINDOW_PERF_INDEX)

    # Retrieval
    async def get_latest_event_window(self) -> Optional[Dict[str, Any]]:
        ids = await self.r.zrevrange(constants.WINDOW_EVENT_INDEX, 0, 0)
        if not ids:
            return None
        key = constants.WINDOW_EVENT_HASH.format(window_start=ids[0])
        data = await self.r.hgetall(key)  # type: ignore[func-returns-value]
        if not data:
            return None
        return {"window_start": int(ids[0]), **self._convert_types(data)}

    async def get_last_event_windows(self, limit: int) -> List[Dict[str, Any]]:
        return await self._get_last_windows(
            constants.WINDOW_EVENT_INDEX,
            constants.WINDOW_EVENT_HASH,
            limit,
        )

    async def get_last_performance_windows(self, limit: int) -> List[Dict[str, Any]]:
        return await self._get_last_windows(
            constants.WINDOW_PERF_INDEX,
            constants.WINDOW_PERF_HASH,
            limit,
        )

    # PubSub
    async def publish_update(self, payload: Dict[str, Any]):
        import json

        await self.r.publish(constants.PUBSUB_CHANNEL_UPDATES, json.dumps(payload))

    # Internals
    async def _trim_index(self, index_key: str):
        size = await self.r.zcard(index_key)
        if size > self.window_retention_count:
            excess = size - self.window_retention_count
            await self.r.zremrangebyrank(index_key, 0, excess - 1)

    def _convert_types(self, data: Dict[str, str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in data.items():
            try:
                out[k] = int(v)
            except ValueError:
                try:
                    out[k] = float(v)
                except ValueError:
                    out[k] = v
        return out

    async def _get_last_windows(
        self, index_key: str, hash_pattern: str, limit: int
    ) -> List[Dict[str, Any]]:
        ids = await self.r.zrevrange(index_key, 0, limit - 1)
        results: List[Dict[str, Any]] = []
        for wid in ids:
            key = hash_pattern.format(window_start=wid)
            data = await self.r.hgetall(key)  # type: ignore[func-returns-value]
            if data:
                results.append({"window_start": int(wid), **self._convert_types(data)})
        return results
