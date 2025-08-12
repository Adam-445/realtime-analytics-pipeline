"""Background worker that drains the operation queue and applies Redis batches."""

from __future__ import annotations

import asyncio
import time
from typing import List

from aiokafka import AIOKafkaConsumer
from src.core.config import settings
from src.core.logger import get_logger
from src.domain.operations import Operation
from src.infrastructure.redis.repository import CacheRepository

from .metrics import (
    KAFKA_COMMIT_BATCHES_TOTAL,
    KAFKA_PENDING_MESSAGES,
    QUEUE_CURRENT_SIZE,
    REDIS_BATCH_ERRORS_TOTAL,
    REDIS_BATCH_LATENCY_SECONDS,
)

logger = get_logger("cache.redis_worker")


async def redis_batch_worker(
    queue: asyncio.Queue[Operation],
    repo: CacheRepository,
    stop_event: asyncio.Event,
    kafka_consumer: AIOKafkaConsumer | None,
):
    """Drain queue and apply batched Redis writes + commit offsets.

    Retries the same batch after a short delay on Redis failure.
    Commits Kafka offsets only after successful Redis persistence.
    """

    batch: List[Operation] = []
    last_flush = time.monotonic()
    timeout = settings.kafka_commit_interval_ms / 1000

    while not stop_event.is_set() or not queue.empty():
        try:
            item = await asyncio.wait_for(queue.get(), timeout)
            batch.append(item)
            QUEUE_CURRENT_SIZE.set(queue.qsize())
            KAFKA_PENDING_MESSAGES.set(len(batch))
        except asyncio.TimeoutError:
            pass

        now = time.monotonic()
        flush_due_time = (now - last_flush) >= timeout
        flush_due_size = len(batch) >= settings.redis_write_batch_size
        if batch and (flush_due_time or flush_due_size):
            try:
                with REDIS_BATCH_LATENCY_SECONDS.time():
                    await repo.pipeline_apply(batch)
            except Exception as e:
                REDIS_BATCH_ERRORS_TOTAL.inc()
                logger.error(
                    "Redis batch apply failed (will retry same batch)",
                    extra={"error": str(e), "batch_size": len(batch)},
                )
                await asyncio.sleep(0.2)
                continue

            if kafka_consumer is not None:
                try:
                    await kafka_consumer.commit()
                    KAFKA_COMMIT_BATCHES_TOTAL.inc()
                except Exception as e:
                    logger.warning(f"Kafka commit failed after batch flush: {e}")
            batch.clear()
            last_flush = now
            KAFKA_PENDING_MESSAGES.set(0)

    # Final flush
    if batch:
        try:
            with REDIS_BATCH_LATENCY_SECONDS.time():
                await repo.pipeline_apply(batch)
            if kafka_consumer is not None:
                try:
                    await kafka_consumer.commit()
                    KAFKA_COMMIT_BATCHES_TOTAL.inc()
                except Exception as e:
                    logger.warning(f"Kafka commit failed on final flush {e}")
        except Exception as e:  # noqa
            REDIS_BATCH_ERRORS_TOTAL.inc()
            logger.error(
                "Final Redis batch failed (batch dropped)",
                extra={"error": str(e), "batch_size": len(batch)},
            )
    KAFKA_PENDING_MESSAGES.set(0)
