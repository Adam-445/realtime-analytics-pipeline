import logging

from confluent_kafka.admin import AdminClient, NewTopic
from src.core.config import settings

logger = logging.getLogger("kafka.admin")


def create_topics():
    config = {"bootstrap.servers": settings.kafka_bootstrap_servers}
    admin = AdminClient(config)

    topics = [
        NewTopic(topic, num_partitions=3, replication_factor=1)
        for topic in settings.kafka_consumer_topics
    ]

    # Only create if doesn't exist
    result = admin.create_topics(topics, validate_only=False)

    for topic, future in result.items():
        try:
            future.result()
            logger.info(f"Topic {topic} created")
        except Exception as e:
            if e.args[0].code() != 36:  # TopicExistsError
                logger.error(f"Failed to create topic {topic}: {e}")
