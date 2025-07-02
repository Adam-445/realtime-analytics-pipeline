import logging
import time

from confluent_kafka.admin import AdminClient
from src.clickhouse_client import ClickHouseClient
from src.core.config import settings
from src.core.logging_config import configure_logging
from src.kafka_batch_consumer import KafkaBatchConsumer


def wait_for_topics(topics: list[str], max_retries: int = 30, initial_delay: int = 5):
    """Wait for Kafka topics to be available with exponential backoff"""
    logger = logging.getLogger("batch_processor")
    admin_client = AdminClient({"bootstrap.servers": settings.kafka_bootstrap})

    for attempt in range(max_retries):
        try:
            # Get cluster metadata
            metadata = admin_client.list_topics(timeout=10)
            available_topics = set(metadata.topics.keys())
            missing_topics = set(topics) - available_topics

            if not missing_topics:
                logger.info(f"All required topics are available: {topics}")
                return True

            logger.warning(
                f"Missing topics: {missing_topics}. Attempt {attempt + 1}/{max_retries}"
            )

            # Exponential backoff with jitter
            delay = min(initial_delay * (2**attempt), 60)  # Cap at 60 seconds
            time.sleep(delay)

        except Exception as e:
            logger.warning(f"Error checking topics (attempt {attempt + 1}): {e}")
            time.sleep(initial_delay)

    raise Exception(
        f"Topics not available after {max_retries} attempts: {missing_topics}"
    )


def main():
    configure_logging()
    logger = logging.getLogger("batch_processor")
    logger.info("Starting Clickhouse storage service")

    # Wait for topics to be available before creating consumer
    logger.info(f"Waiting for topics: {settings.topics}")
    wait_for_topics(settings.topics)

    ch_client = ClickHouseClient()
    consumer = KafkaBatchConsumer(settings.topics)

    logger.info(f"Consuming from topics {', '.join(settings.topics)}")

    while True:
        try:
            batches = consumer.consume_batch()
            for topic, batch in batches.items():
                if not batch:
                    continue

                ch_client.insert_batch(topic, batch)
                logger.info(f"Inserted {len(batch)} records into {topic}")

            consumer.commit()
            time.sleep(settings.poll_interval_seconds)

        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            time.sleep(10)


if __name__ == "__main__":
    main()
