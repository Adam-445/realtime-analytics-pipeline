import asyncio
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from src.api.router import api_router
from src.core.config import settings
from src.core.logger import configure_logging, get_logger
from src.infrastructure.kafka.consumer import consume_loop
from src.infrastructure.redis.repository import CacheRepository

from shared.utils.retry import retry_async

# Configure logging once and get service logger
configure_logging()
logger = get_logger("cache.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("cache_service_starting")
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
    try:
        yield
    finally:
        logger.info("cache_service_stopping")
        app.state.consumer_task.cancel()
        try:
            await app.state.consumer_task
        except asyncio.CancelledError:  # expected during shutdown
            logger.debug("consumer_task_cancelled")
        except Exception:  # noqa
            logger.debug("consumer_task_non_critical_exit", exc_info=True)
        await app.state.redis.close()


app = FastAPI(title="Real-time Analytics Cache", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


async def _init_redis_with_retry():
    async def _connect():
        r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
        await r.ping()
        return r

    async def _on_retry(
        attempt: int, exc: BaseException, sleep_for: float
    ):  # type: ignore[override]
        logger.warning(
            "redis_connect_retry",
            extra={
                "attempt": attempt,
                "error": str(exc),
                "sleep_for": round(sleep_for, 2),
            },
        )

    r = await retry_async(
        _connect,
        retries=6,
        base_delay=0.5,
        max_delay=8.0,
        jitter=0.2,
        on_retry=_on_retry,
    )
    logger.info("redis_connected")
    return r


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
