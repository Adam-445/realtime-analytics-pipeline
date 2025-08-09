import asyncio
import json
from typing import Any, Dict

from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Gauge, Histogram
from src.core.config import settings
from src.core.logger import get_logger

from .repository import CacheRepository

logger = get_logger("cache.consumer")

RECORDS_PROCESSED = Counter("cache_records_total", "Kafka records processed")
BATCH_COMMITS = Counter("cache_kafka_commits_total", "Kafka batch commits")
QUEUE_SIZE = Gauge("cache_queue_size", "Current size of processing queue")
REDIS_BATCH_LAT = Histogram("cache_redis_batch_seconds", "Redis batch write latency")


async def consume_loop(repo: CacheRepository, app_state: Any):
    queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(
        maxsize=settings.redis_queue_max_size
    )
    stop_event = asyncio.Event()

    async def redis_worker():
        batch: list[dict] = []
        last_flush = asyncio.get_event_loop().time()
        commit_pending = 0
        while not stop_event.is_set() or not queue.empty():
            timeout = settings.kafka_commit_interval_ms / 1000
            try:
                item = await asyncio.wait_for(queue.get(), timeout)
                batch.append(item)
                commit_pending += 1
                QUEUE_SIZE.set(queue.qsize())
            except asyncio.TimeoutError:
                pass

            now = asyncio.get_event_loop().time()
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
                except Exception as e:  # noqa
                    logger.warning("Kafka commit failed: %s", e)
        # Final flush
        if batch:
            with REDIS_BATCH_LAT.time():
                await repo.pipeline_apply(batch)
        if commit_pending and consumer is not None:
            try:
                await consumer.commit()
                BATCH_COMMITS.inc()
            except Exception:
                pass

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
        except Exception as e:  # noqa
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
            try:
                op = parse_message(msg.topic, msg.value or {})
                if op:
                    try:
                        queue.put_nowait(op)
                    except asyncio.QueueFull:
                        logger.warning("Queue full; dropping metric window update")
            except Exception as e:  # noqa
                logger.exception("Failed processing message: %s", e)
            if first:
                first = False
                # signal readiness
                if getattr(app_state, "ready_event", None):
                    app_state.ready_event.set()
    finally:
        stop_event.set()
        await worker_task
        await consumer.stop()
        logger.info("Kafka consumer stopped")


def parse_message(topic: str, payload: dict) -> Dict[str, Any] | None:
    # Return op dict or None
    if topic == "event_metrics":
        # window_start may be ms epoch or ISO string
        window_start = _coerce_ts(payload.get("window_start"))
        event_type = payload.get("event_type")
        event_count = int(payload.get("event_count", 0))
        user_count = int(payload.get("user_count", 0))
        key_prefix = f"{event_type}"  # fields flattened per design e.g. page_view.count
        fields = {
            f"{key_prefix}.count": event_count,
            f"{key_prefix}.users": user_count,
        }
        return {"type": "event", "window_start": window_start, "fields": fields}
    elif topic == "performance_metrics":
        window_start = _coerce_ts(payload.get("window_start"))
        device_category = payload.get("device_category")
        avg_load_time = float(payload.get("avg_load_time", 0))
        p95_load_time = float(payload.get("p95_load_time", 0))
        fields = {
            f"{device_category}.avg_load_time": avg_load_time,
            f"{device_category}.p95_load_time": p95_load_time,
        }
        return {"type": "perf", "window_start": window_start, "fields": fields}
    elif topic == "session_metrics":
        # For MVP we'll push completed sessions into a capped list (optional future)
        return None
    else:
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
