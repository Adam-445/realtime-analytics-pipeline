"""Batch processing orchestration (extracted from legacy batch_processor)."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, TypedDict

from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.clickhouse.client import ClickHouseClient
from src.infrastructure.kafka.consumer import KafkaBatchConsumer
from src.core.metrics import (
    BATCH_SIZE,
    CONSUME_CYCLE,
    IN_FLIGHT_INSERTS,
    INSERT_LATENCY,
    STORAGE_BATCHES,
    STORAGE_COMMITS,
    STORAGE_ERRORS,
    STORAGE_RECORDS,
    STORAGE_RETRIES,
)
from src.utils.concurrency import run_blocking

logger = get_logger("storage.processor")


class BatchRecord(TypedDict, total=False):
    # Define expected fields of records if known; left open for flexibility.
    # Example: user_id: str; event_type: str
    pass


BatchMap = Dict[str, List[BatchRecord]]  # internal mutable representation


def _as_batch_map(raw: Any) -> BatchMap:  # runtime helper for loose producer typing
    return raw  # trust upstream; lightweight cast


async def _consume_batches(consumer: KafkaBatchConsumer) -> BatchMap:
    data = await run_blocking(consumer.consume_batch)
    return _as_batch_map(data)


async def _insert_batch(
    ch_client: ClickHouseClient, topic: str, batch: List[BatchRecord]
) -> None:
    await run_blocking(ch_client.insert_rows, topic, batch)


async def _close_safe(obj, name: str = "") -> None:
    if obj is None:
        return
    close_fn = getattr(obj, "close", None)
    if not callable(close_fn):
        logger.debug("no close() method", extra={"obj": name or repr(obj)})
        return
    try:
        await run_blocking(close_fn)
    except Exception:  # noqa: BLE001
        logger.exception("error closing resource", extra={"resource": name})


async def process_batches(shutdown_event: asyncio.Event) -> None:
    """Main processing loop: poll batches, insert, commit until shutdown."""
    ch_client = ClickHouseClient()
    consumer = KafkaBatchConsumer(settings.kafka_consumer_topics)
    poll_interval = settings.storage_poll_interval_seconds or 1
    logger.info(
        "consuming_topics",
        extra={
            "topics": settings.kafka_consumer_topics,
            "poll_interval": poll_interval,
        },
    )

    try:
        while not shutdown_event.is_set():
            try:
                cycle_start = time.perf_counter()
                batches = await _consume_batches(consumer)
                total = sum(len(b) for b in batches.values())
                # Debug log removed to reduce noise; metrics provide visibility.
                if total == 0:
                    # Shorter idle sleeps in testing to reduce warm-up latency.
                    sleep_for = (
                        0.2 if settings.app_environment == "testing" else poll_interval
                    )
                    await asyncio.sleep(sleep_for)
                    continue

                semaphore = asyncio.Semaphore(settings.storage_max_concurrent_inserts)
                any_insert_failed = False
                insert_tasks: list[asyncio.Task] = []

                async def _insert_topic(topic: str, batch: list[BatchRecord]):
                    nonlocal any_insert_failed
                    if any_insert_failed:
                        return
                    async with semaphore:
                        BATCH_SIZE.observe(len(batch))
                        insert_start = time.perf_counter()
                        IN_FLIGHT_INSERTS.inc()
                        try:
                            # Simple bounded retry loop with exponential backoff
                            attempts = 0
                            max_retries = 3
                            while True:
                                try:
                                    await _insert_batch(ch_client, topic, batch)
                                    break
                                except Exception:
                                    attempts += 1
                                    STORAGE_RETRIES.inc()
                                    if attempts >= max_retries:
                                        raise
                                    # Exponential backoff with max cap
                                    await asyncio.sleep(min(0.5 * attempts, 2.0))
                            INSERT_LATENCY.observe(time.perf_counter() - insert_start)
                            STORAGE_BATCHES.inc()
                            STORAGE_RECORDS.inc(len(batch))
                            logger.info(
                                "batch_inserted",
                                extra={
                                    "topic": topic,
                                    "batch_size": len(batch),
                                    "conc": settings.storage_max_concurrent_inserts,
                                },
                            )
                        except Exception as exc:  # noqa: BLE001
                            any_insert_failed = True
                            STORAGE_ERRORS.inc()
                            logger.exception(
                                "insert_failed",
                                extra={
                                    "topic": topic,
                                    "batch_size": len(batch),
                                    "error": str(exc),
                                },
                            )
                        finally:
                            try:
                                IN_FLIGHT_INSERTS.dec()
                            except ValueError:
                                pass

                for topic, batch in batches.items():
                    if not batch:
                        continue
                    insert_tasks.append(
                        asyncio.create_task(_insert_topic(topic, batch))
                    )

                if insert_tasks:
                    await asyncio.gather(*insert_tasks)

                if not any_insert_failed:
                    try:
                        await run_blocking(consumer.commit)
                        STORAGE_COMMITS.inc()
                    except Exception:  # noqa: BLE001
                        STORAGE_ERRORS.inc()
                        logger.exception(
                            "commit_failed", extra={"note": "messages will reprocess"}
                        )

                cycle_duration = time.perf_counter() - cycle_start
                CONSUME_CYCLE.observe(cycle_duration)

                # Conditional sleep: skip if any batch is full and flag enabled
                if settings.storage_skip_sleep_if_full and any(
                    len(batch) >= settings.storage_batch_size
                    for batch in batches.values()
                ):
                    continue
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:  # pragma: no cover - control path
                raise
            except Exception as e:  # noqa: BLE001
                STORAGE_ERRORS.inc()
                logger.exception("processing_loop_error", extra={"error": str(e)})
                await asyncio.sleep(5)
    finally:
        await _close_safe(consumer, "kafka_consumer")
        await _close_safe(ch_client, "clickhouse_client")
        logger.info("processing_loop_stopped")
