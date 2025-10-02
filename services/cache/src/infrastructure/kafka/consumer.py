import asyncio
import json
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from src.core.config import settings
from src.core.logger import get_logger
from src.domain.operations import Operation
from src.infrastructure.redis.repository import CacheRepository

from .message_parser import parse_message
from .metrics import KAFKA_RECORDS_TOTAL
from .worker import redis_batch_worker

logger = get_logger("cache.consumer")


async def start_consumer_with_retries(consumer: Any, ensure_topics_cb=None) -> None:
    """Start Kafka consumer with exponential backoff and optional topic ensure.

    Raises RuntimeError after exhausting retries.
    """
    delay = 1.0
    for attempt in range(1, 8):
        try:
            if attempt == 1 and ensure_topics_cb is not None:
                await ensure_topics_cb()
            await consumer.start()
            logger.info(
                "kafka_consumer_started",
                extra={
                    "topics": list(settings.cache_kafka_topics),
                    "attempt": attempt,
                },
            )
            return
        except Exception as e:  # noqa
            logger.warning(
                "kafka_consumer_start_failed",
                extra={"attempt": attempt, "error": str(e), "retry_in": delay},
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)
    raise RuntimeError("Kafka consumer could not start after retries")


async def consume_loop(repo: CacheRepository, app_state: Any) -> None:
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

    async def _ensure_topics(max_retries: int = 30, initial_delay: int = 5):
        topics = list(settings.cache_kafka_topics)
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=settings.kafka_bootstrap_servers
        )
        await admin_client.start()

        missing_topics = set(topics)  # Ensure missing_topics is always defined
        for attempt in range(max_retries):
            try:
                # Get cluster metadata
                metadata = await admin_client.list_topics()
                available_topics = set(metadata)
                missing_topics = set(topics) - available_topics

                if not missing_topics:
                    logger.info(
                        "all topics available",
                        extra={"topics": topics, "attempt": attempt},
                    )
                    return True

                logger.warning(
                    "missing topics",
                    extra={
                        "missing_topics": list(missing_topics),
                        "attempt": attempt,
                        "max_retries": max_retries,
                    },
                )
                # Exponential backoff with jitter
                delay = min(initial_delay * (2**attempt), 60)  # Cap at 60 seconds
                await asyncio.sleep(delay)

            except Exception as e:
                logger.warning(
                    "topic check error", extra={"attempt": attempt, "error": str(e)}
                )
                await asyncio.sleep(initial_delay)

        # If we fall through, we failed
        logger.error(
            "topics unavailable after_retries",
            extra={
                "required_topics": topics,
                "missing_topics": list(missing_topics),
                "max_retries": max_retries,
            },
        )
        raise Exception(
            f"Topics not available after {max_retries} attempts: {missing_topics}"
        )

    await start_consumer_with_retries(consumer, _ensure_topics)
    first = True
    worker_coro = redis_batch_worker(
        queue=queue,
        repo=repo,
        stop_event=stop_event,
        kafka_consumer=consumer,
    )
    worker_task = asyncio.create_task(worker_coro)
    try:
        async for msg in consumer:
            KAFKA_RECORDS_TOTAL.inc()
            payload = msg.value or {}
            op = parse_message(msg.topic, payload)
            if op:
                await queue.put(op)
            if first:
                first = False
                if getattr(app_state, "ready_event", None):
                    app_state.ready_event.set()
    except asyncio.CancelledError:  # graceful cancellation
        logger.info("consume_loop_cancelled")
        raise
    except Exception as e:  # noqa
        logger.exception("consume_loop_fatal", extra={"error": str(e)})
        raise
    finally:
        stop_event.set()
        await worker_task
        await consumer.stop()
        logger.info("kafka_consumer_stopped")
