import pytest
from src.services.cache_service import CacheService


class DummyRepo:
    def __init__(self):
        self._event_latest = {"window_start": 1000, "foo": 1}
        self._perf_windows = [{"window_start": 1005, "bar": 2}]

    async def pipeline_apply(self, ops):  # pragma: no cover - trivial
        self._last_ops = ops

    async def get_latest_event_window(self):
        return self._event_latest

    async def get_last_event_windows(self, limit: int):  # pragma: no cover - unused
        return [self._event_latest]

    async def get_last_performance_windows(self, limit: int):
        return self._perf_windows[:limit]


@pytest.mark.asyncio
async def test_get_overview():
    svc = CacheService(DummyRepo())  # type: ignore[arg-type]
    overview = await svc.get_overview()
    assert overview["event_latest"]["foo"] == 1
    assert overview["performance_latest"]["bar"] == 2
