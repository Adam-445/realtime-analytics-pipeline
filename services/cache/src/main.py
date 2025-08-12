import asyncio
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from src.api.router import api_router
from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.kafka.consumer import consume_loop
from src.infrastructure.redis.repository import CacheRepository

logger = get_logger("cache.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    try:
        yield
    finally:
        logger.info("Shutting down cache service")
        app.state.consumer_task.cancel()
        try:
            await app.state.consumer_task
        except asyncio.CancelledError:  # expected during shutdown
            logger.debug("Consumer task cancelled cleanly")
        except Exception:  # noqa
            logger.debug(
                "Consumer task exited with non-critical exception",
                exc_info=True,
            )
        await app.state.redis.close()


app = FastAPI(title="Real-time Analytics Cache", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


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


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# TODO: WebSocket streaming endpoint (/ws/stream).
# TODO: Active session tracking & summary endpoints.
