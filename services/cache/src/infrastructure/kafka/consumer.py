import asyncio
import json
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
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
                f"Kafka consumer started for topics {settings.cache_kafka_topics} "
                f"on attempt {attempt}"
            )
            return
        except Exception as e:  # noqa
            logger.warning(
                "Kafka consumer start failed attempt %d: %s (retrying in %.1fs)",
                attempt,
                e,
                delay,
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

    async def _ensure_topics():
        topics = list(settings.cache_kafka_topics)
        try:
            admin = AIOKafkaAdminClient(
                bootstrap_servers=settings.kafka_bootstrap_servers
            )
            await admin.start()
            try:
                new_topics = [
                    NewTopic(name=t, num_partitions=1, replication_factor=1)
                    for t in topics
                ]
                await admin.create_topics(new_topics=new_topics, validate_only=False)
                logger.info("Ensured Kafka topics exist: %s", topics)
            except Exception as e:
                # Many errors here are benign: TopicAlreadyExistsError,
                # autovivification during race, etc.
                logger.debug(
                    "Topic creation result: %s (likely benign if already exists)",
                    e,
                )
            finally:
                await admin.close()
        except Exception as e:
            # Don't fail startup; consumer will still retry
            logger.debug("Kafka admin ensure_topics skipped due to error: %s", e)

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
