import asyncio

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from src.core.config import settings
from src.core.logger import get_logger
from src.realtime.consumer import consume_loop
from src.realtime.repository import CacheRepository

logger = get_logger("cache.main")

app = FastAPI(title="Real-time Analytics Cache", version="0.1.0")


async def _init_redis_with_retry():
    """Attempt Redis connection with exponential backoff."""
    delay = 0.5
    for attempt in range(1, 6):
        try:
            r = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
            )
            await r.ping()
            logger.info("Redis connected on attempt %d", attempt)
            return r
        except Exception as e:  # noqa
            logger.warning(
                "Redis connection failed attempt %d: %s (retrying in %.1fs)",
                attempt,
                e,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("Could not connect to Redis after retries")


@app.on_event("startup")
async def startup():
    logger.info("Starting cache service")
    app.state.redis = await _init_redis_with_retry()
    app.state.repo = CacheRepository(
        app.state.redis,
        settings.window_retention_count,
        settings.window_hash_ttl_seconds,
    )
    app.state.ready_event = asyncio.Event()
    app.state.consumer_task = asyncio.create_task(
        consume_loop(app.state.repo, app.state)
    )


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down cache service")
    app.state.consumer_task.cancel()
    try:
        await app.state.consumer_task
    except Exception:  # noqa
        pass
    await app.state.redis.close()


@app.get("/healthz")
async def healthz():
    """Liveness probe."""
    try:
        pong = await app.state.redis.ping()
        return {"status": "ok", "redis": pong}
    except Exception as e:  # noqa
        return Response(status_code=503, content=str(e))


@app.get("/readyz")
async def readyz():
    """Readiness: first Kafka message processed."""
    if app.state.ready_event.is_set():  # type: ignore[attr-defined]
        return {"status": "ready"}
    return Response(status_code=503, content="not ready")


@app.get("/metrics/event/latest")
async def get_event_latest():
    latest = await app.state.repo.get_latest_event_window()
    return latest or {}


@app.get("/metrics/event/windows")
async def get_event_windows(limit: int = 20):
    windows = await app.state.repo.get_last_event_windows(limit)
    return {"windows": windows}


@app.get("/metrics/performance/windows")
async def get_performance_windows(limit: int = 20):
    windows = await app.state.repo.get_last_performance_windows(limit)
    return {"windows": windows}


@app.get("/metrics/overview")
async def get_overview():
    event_latest = await app.state.repo.get_latest_event_window()
    perf_latest_list = await app.state.repo.get_last_performance_windows(1)
    perf_latest = perf_latest_list[0] if perf_latest_list else None
    return {
        "event_latest": event_latest or {},
        "performance_latest": perf_latest or {},
    }


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# TODO: WebSocket streaming endpoint (/ws/stream) in follow-up PR.
# TODO: Active session tracking & summary endpoints.

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=False)
