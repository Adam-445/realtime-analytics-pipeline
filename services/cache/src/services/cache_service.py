from typing import Any, Dict, List

from src.domain.operations import Operation
from src.infrastructure.redis.repository import CacheRepository


class CacheService:
    """High-level cache operations aggregating repository calls.

    This layer is intentionally thin now but gives a seam for future
    business logic (e.g., filtering, authorization, projections,
    websocket fan-out, derived metrics calculations).
    """

    def __init__(self, repository: CacheRepository):
        self.repo = repository

    async def apply_operations(self, ops: List[Operation]):
        if ops:
            await self.repo.pipeline_apply(ops)

    async def get_event_latest(self) -> Dict[str, Any]:
        return await self.repo.get_latest_event_window() or {}

    async def get_event_windows(self, limit: int) -> List[Dict[str, Any]]:
        return await self.repo.get_last_event_windows(limit)

    async def get_performance_windows(self, limit: int) -> List[Dict[str, Any]]:
        return await self.repo.get_last_performance_windows(limit)

    async def get_overview(self) -> Dict[str, Any]:
        event_latest = await self.repo.get_latest_event_window()
        perf_latest_list = await self.repo.get_last_performance_windows(1)
        perf_latest = perf_latest_list[0] if perf_latest_list else None
        return {
            "event_latest": event_latest or {},
            "performance_latest": perf_latest or {},
        }
