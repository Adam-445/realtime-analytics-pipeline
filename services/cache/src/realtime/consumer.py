import asyncio
import json
import time
from typing import Any, Optional

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
REDIS_BATCH_ERRORS = Counter(
    "cache_redis_batch_errors_total", "Redis batch write errors"
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

    consumer = AIOKafkaConsumer(
        *settings.cache_kafka_topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.cache_kafka_consumer_group,
        enable_auto_commit=False,
        auto_offset_reset=settings.cache_consume_from,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    async def redis_worker(kafka_consumer: AIOKafkaConsumer):
        """Drain queue and apply batched Redis writes + commit offsets."""
        batch: list[Operation] = []
        last_flush = time.monotonic()
        while not stop_event.is_set() or not queue.empty():
            timeout = settings.kafka_commit_interval_ms / 1000
            try:
                item = await asyncio.wait_for(queue.get(), timeout)
                batch.append(item)
                QUEUE_SIZE.set(queue.qsize())
                PENDING_COMMITS.set(len(batch))
            except asyncio.TimeoutError:
                pass

            now = time.monotonic()
            flush_due_time = (now - last_flush) >= timeout
            flush_due_size = len(batch) >= settings.redis_write_batch_size
            if batch and (flush_due_time or flush_due_size):
                try:
                    with REDIS_BATCH_LAT.time():
                        await repo.pipeline_apply(batch)
                except Exception as e:
                    REDIS_BATCH_ERRORS.inc()
                    logger.error(
                        "Redis batch apply failed (will retry same batch)",
                        extra={"error": str(e), "batch_size": len(batch)},
                    )
                    # brief yield before retry
                    await asyncio.sleep(0.2)
                    continue  # keep batch intact for retry

                # Success path: commit offsets up to what we consumed
                if kafka_consumer is not None:
                    try:
                        await kafka_consumer.commit()
                        BATCH_COMMITS.inc()
                    except Exception as e:
                        logger.warning(f"Kafka commit failed after batch flush: {e}")
                        # Keep batch cleared, will reprocess on restart
                batch.clear()
                last_flush = now
                PENDING_COMMITS.set(0)
        # Final flush after loop exit
        if batch:
            try:
                with REDIS_BATCH_LAT.time():
                    await repo.pipeline_apply(batch)
                if kafka_consumer is not None:
                    try:
                        await kafka_consumer.commit()
                        BATCH_COMMITS.inc()
                    except Exception as e:
                        logger.warning(f"Kafka commit failed on final flush {e}")
            except Exception as e:
                REDIS_BATCH_ERRORS.inc()
                logger.error(
                    "Final Redis batch failed (batch dropped)",
                    extra={"error": str(e), "batch_size": len(batch)},
                )
        PENDING_COMMITS.set(0)

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
    worker_task = asyncio.create_task(redis_worker(consumer))
    try:
        async for msg in consumer:
            RECORDS_PROCESSED.inc()
            payload = msg.value or {}
            op = parse_message(msg.topic, payload)
            if op:
                # Block instead of drop to avoid commiting past unwritted data
                await queue.put(op)
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
        if not window_start:
            return None
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
        if not window_start:
            return None
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


def _coerce_ts(value: Any) -> Optional[int]:
    """Convert int ms or ISO8601 string to epoch ms; return None if invalid."""
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
    return None
