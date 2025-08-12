import asyncio

import pytest
from fastapi.testclient import TestClient
from src.api.dependencies import get_cache_service
from src.main import app
from src.services.cache_service import CacheService


class DummyRepo:
    def __init__(self):
        self._event_latest = {"window_start": 1000, "foo": 1}
        self._perf_windows = [{"window_start": 1005, "bar": 2}]

    async def get_latest_event_window(self):
        return self._event_latest

    async def get_last_event_windows(self, limit: int):  # pragma: no cover - unused
        return [self._event_latest]

    async def get_last_performance_windows(self, limit: int):
        return self._perf_windows[:limit]


class DummyCacheService(CacheService):  # inherits behavior
    pass


def override_cache_service():
    return DummyCacheService(DummyRepo())  # type: ignore[arg-type]


app.dependency_overrides[get_cache_service] = override_cache_service


@pytest.fixture(scope="module", autouse=True)
def setup_app_state():
    # Provide minimal app state for health/ready endpoints
    # Health endpoint awaits redis.ping(), so provide async ping
    async def _ping(self):
        return "PONG"

    app.state.redis = type("R", (), {"ping": _ping})()
    app.state.ready_event = asyncio.Event()
    app.state.ready_event.set()  # mark ready
    yield


def test_event_latest():
    client = TestClient(app)
    resp = client.get("/metrics/event/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["foo"] == 1


def test_overview():
    client = TestClient(app)
    resp = client.get("/metrics/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["event_latest"]["foo"] == 1
    assert body["performance_latest"]["bar"] == 2


def test_health_ready():
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_readyz_not_ready(monkeypatch):
    client = TestClient(app)
    # Temporarily mark not ready
    app.state.ready_event.clear()
    try:
        resp = client.get("/readyz")
        assert resp.status_code == 503
    finally:
        app.state.ready_event.set()


def test_healthz_error(monkeypatch):
    client = TestClient(app)
    # Make redis.ping raise

    async def _boom(self):
        raise RuntimeError("redis down")

    from types import MethodType

    orig = app.state.redis.ping
    # Bind function as a bound method so `self` is provided when called
    app.state.redis.ping = MethodType(  # type: ignore[assignment]
        _boom, app.state.redis
    )
    try:
        resp = client.get("/healthz")
        assert resp.status_code == 503
        assert "redis down" in resp.text
    finally:
        app.state.redis.ping = orig  # type: ignore[assignment]
