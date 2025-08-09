import asyncio
import json
import time
from typing import Any

from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Gauge, Histogram
from src.core.config import settings
from src.core.logger import get_logger

from .repository import CacheRepository, Operation

logger = get_logger("cache.consumer")


RECORDS_PROCESSED = Counter("cache_records_total", "Kafka records processed")
BATCH_COMMITS = Counter("cache_kafka_commits_total", "Kafka batch commits")
QUEUE_SIZE = Gauge("cache_queue_size", "Current size of processing queue")
PENDING_COMMITS = Gauge(
    "cache_pending_commit_messages", "Messages consumed but not yet committed"
)
REDIS_BATCH_LAT = Histogram("cache_redis_batch_seconds", "Redis batch write latency")


async def consume_loop(repo: CacheRepository, app_state: Any):
    """Main consumption loop.

    Consumes Kafka records, translates them to Operation objects, places them on
    a bounded queue processed by a Redis pipeline worker with batching and
    commit aggregation.
    """
    queue: asyncio.Queue[Operation] = asyncio.Queue(
        maxsize=settings.redis_queue_max_size
    )
    stop_event = asyncio.Event()

    async def redis_worker():
        """Drain queue and apply batched Redis writes + commit offsets."""
        batch: list[Operation] = []
        last_flush = time.monotonic()
        commit_pending = 0
        while not stop_event.is_set() or not queue.empty():
            timeout = settings.kafka_commit_interval_ms / 1000
            try:
                item = await asyncio.wait_for(queue.get(), timeout)
                batch.append(item)
                commit_pending += 1
                QUEUE_SIZE.set(queue.qsize())
                PENDING_COMMITS.set(commit_pending)
            except asyncio.TimeoutError:
                pass

            now = time.monotonic()
            flush_due_time = (now - last_flush) >= (
                settings.kafka_commit_interval_ms / 1000
            )
            flush_due_size = len(batch) >= settings.redis_write_batch_size
            commit_due = (
                commit_pending >= settings.kafka_commit_batch_size or flush_due_time
            )
            if batch and (flush_due_time or flush_due_size):
                with REDIS_BATCH_LAT.time():
                    await repo.pipeline_apply(batch)
                batch.clear()
                last_flush = now
            if commit_due and consumer is not None:
                try:
                    await consumer.commit()
                    BATCH_COMMITS.inc()
                    commit_pending = 0
                except Exception as e:
                    logger.warning("Kafka commit failed: %s", e)
                PENDING_COMMITS.set(commit_pending)
        # Final flush after loop exit
        if batch:
            with REDIS_BATCH_LAT.time():
                await repo.pipeline_apply(batch)
        if commit_pending and consumer is not None:
            try:
                await consumer.commit()
                BATCH_COMMITS.inc()
            except Exception:
                pass
        PENDING_COMMITS.set(0)

    consumer = AIOKafkaConsumer(
        *settings.cache_kafka_topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.cache_kafka_consumer_group,
        enable_auto_commit=False,
        auto_offset_reset=settings.cache_consume_from,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    # Retry start with backoff (handles broker not ready yet)
    delay = 1.0
    for attempt in range(1, 8):
        try:
            await consumer.start()
            logger.info(
                f"Kafka consumer started for topics {settings.cache_kafka_topics} "
                f"on attempt {attempt}"
            )
            break
        except Exception as e:
            logger.warning(
                "Kafka consumer start failed attempt %d: %s (retrying in %.1fs)",
                attempt,
                e,
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)
    else:
        raise RuntimeError("Kafka consumer could not start after retries")
    first = True
    worker_task = asyncio.create_task(redis_worker())
    try:
        async for msg in consumer:
            RECORDS_PROCESSED.inc()
            payload = msg.value or {}
            op = parse_message(msg.topic, payload)
            if op:
                try:
                    queue.put_nowait(op)  # backpressure via QueueFull handling
                except asyncio.QueueFull:
                    logger.warning("Queue full; dropping metric window update")
            if first:
                first = False
                if getattr(app_state, "ready_event", None):
                    app_state.ready_event.set()
    except asyncio.CancelledError:  # graceful cancellation
        logger.info("consume_loop cancelled")
        raise
    except Exception as e:  # noqa
        logger.exception("Fatal error in consume_loop: %s", e)
        raise
    finally:
        stop_event.set()
        await worker_task
        await consumer.stop()
        logger.info("Kafka consumer stopped")


def parse_message(topic: str, payload: dict) -> Operation | None:
    """Translate a raw Kafka topic/payload into an Operation.

    Returns None for topics we intentionally ignore (e.g. session_metrics for now).
    """
    if topic == "event_metrics":
        window_start = _coerce_ts(payload.get("window_start"))
        event_type = payload.get("event_type")
        if not event_type:
            return None
        fields = {
            f"{event_type}.count": int(payload.get("event_count", 0)),
            f"{event_type}.users": int(payload.get("user_count", 0)),
        }
        return Operation(type="event", window_start=window_start, fields=fields)
    if topic == "performance_metrics":
        window_start = _coerce_ts(payload.get("window_start"))
        device_category = payload.get("device_category")
        if not device_category:
            return None
        fields = {
            f"{device_category}.avg_load_time": float(
                payload.get("avg_load_time", 0.0)
            ),
            f"{device_category}.p95_load_time": float(
                payload.get("p95_load_time", 0.0)
            ),
        }
        return Operation(type="perf", window_start=window_start, fields=fields)
    if topic == "session_metrics":
        return None
    logger.warning("Unhandled topic %s", topic)
    return None


def _coerce_ts(value: Any) -> int:
    # If value already int (ms), return; if ISO8601 convert to epoch ms
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # naive parse: expect '2025-08-09T12:34:56.123Z'
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except Exception:
            logger.warning("Unable to parse window_start %s", value)
    return 0
