import time

from confluent_kafka.admin import AdminClient
from prometheus_client import Counter, start_http_server
from src.clickhouse_client import ClickHouseClient
from src.core.config import settings
from src.core.logger import get_logger
from src.core.logging_config import configure_logging
from src.kafka_batch_consumer import KafkaBatchConsumer

STORAGE_BATCHES = Counter("storage_batches_total", "Total batches processed")
STORAGE_RECORDS = Counter("storage_records_total", "Total records stored")
STORAGE_ERRORS = Counter("storage_errors_total", "Storage processing errors")

logger = get_logger("batch_processor")


def wait_for_topics(topics: list[str], max_retries: int = 30, initial_delay: int = 5):
    """Wait for Kafka topics to be available with exponential backoff"""
    admin_client = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
    missing_topics = set(topics)

    for attempt in range(max_retries):
        try:
            # Get cluster metadata
            metadata = admin_client.list_topics(timeout=10)
            available_topics = set(metadata.topics.keys())
            missing_topics = set(topics) - available_topics

            if not missing_topics:
                logger.info(
                    "all topics available", extra={"topics": topics, "attempt": attempt}
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
            time.sleep(delay)

        except Exception as e:
            logger.warning(
                "topic check error", extra={"attempt": attempt, "error": str(e)}
            )
            time.sleep(initial_delay)

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


def main():
    configure_logging()
    logger.info("Starting Clickhouse storage service")

    metrics_port = 8001
    start_http_server(metrics_port)
    logger.info("prometheus metrics exposed", extra={"port": metrics_port})

    # Wait for topics to be available before creating consumer
    logger.info(f"Waiting for topics: {settings.kafka_consumer_topics}")
    wait_for_topics(settings.kafka_consumer_topics)

    ch_client = ClickHouseClient()
    consumer = KafkaBatchConsumer(settings.kafka_consumer_topics)

    logger.info(f"Consuming from topics {', '.join(settings.kafka_consumer_topics)}")

    while True:
        try:
            batches = consumer.consume_batch()
            for topic, batch in batches.items():
                if not batch:
                    continue
                STORAGE_BATCHES.inc()
                STORAGE_RECORDS.inc(len(batch))

                ch_client.insert_batch(topic, batch)
                logger.info(
                    "batch_inserted", extra={"topic": topic, "batch_size": len(batch)}
                )

            consumer.commit()
            time.sleep(settings.storage_poll_interval_seconds)

        except Exception as e:
            STORAGE_ERRORS.inc()
            logger.error("processing error", extra={"error": str(e)})
            time.sleep(10)


if __name__ == "__main__":
    main()
