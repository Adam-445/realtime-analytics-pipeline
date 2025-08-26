import random
import time
from typing import Iterable

from confluent_kafka.admin import AdminClient
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("topic_waiter")


def ensure_topics_available(
    topics: Iterable[str], max_retries: int = 30, initial_delay: int = 5
) -> None:
    """Block until all topics exist or raise after retries.

    Exponential backoff with jitter. Extracted to isolate Kafka Admin usage.
    """
    topics = list(topics)
    admin_client = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
    missing = set(topics)

    for attempt in range(max_retries):
        try:
            metadata = admin_client.list_topics(timeout=10)
            available = set(metadata.topics.keys())
            missing = set(topics) - available
            if not missing:
                logger.info(
                    "topics_available", extra={"topics": topics, "attempt": attempt}
                )
                return
            logger.warning(
                "topics_missing",
                extra={
                    "missing": sorted(missing),
                    "attempt": attempt,
                    "max_retries": max_retries,
                },
            )
            base = min(initial_delay * (2**attempt), 60)
            sleep_for = base + random.uniform(0, base * 0.1)
            time.sleep(sleep_for)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "topic_check_error",
                extra={"attempt": attempt, "error": str(exc)},
            )
            time.sleep(initial_delay)

    logger.error(
        "topics_unavailable_final",
        extra={
            "required": topics,
            "missing": sorted(missing),
            "max_retries": max_retries,
        },
    )
    raise RuntimeError(f"Topics not available after {max_retries} attempts: {missing}")
