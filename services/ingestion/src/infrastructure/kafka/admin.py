from confluent_kafka.admin import AdminClient, NewTopic
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("kafka.admin")


def create_topics():
    topics = [settings.kafka_topic_events] + settings.kafka_consumer_topics
    logger.info("Creating Kafka topics", extra={"topics": topics})
    config = {"bootstrap.servers": settings.kafka_bootstrap_servers}
    admin = AdminClient(config)

    topics = [
        NewTopic(topic, num_partitions=6, replication_factor=1) for topic in topics
    ]

    # Only create if doesn't exist
    result = admin.create_topics(topics, validate_only=False)

    for topic, future in result.items():
        try:
            future.result()
            logger.info("Topic created", extra={"topic": topic})
        except Exception as e:
            if e.args[0].code() != 36:  # TopicExistsError
                logger.error(
                    "Failed to create topic", extra={"topic": topic, "error": e}
                )
