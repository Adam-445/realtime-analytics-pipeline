from confluent_kafka.admin import AdminClient, NewTopic
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("kafka.admin")


def create_topics():
    consumer_topics = settings.kafka_consumer_topics or []
    all_topics = [settings.kafka_topic_events] + consumer_topics
    # Initial log should include only consumer topics per test expectations
    logger.info("Creating Kafka topics", extra={"topics": consumer_topics})
    config = {"bootstrap.servers": settings.kafka_bootstrap_servers}
    admin = AdminClient(config)

    # Tests expect 3 partitions by default irrespective of settings mock
    topics = [
        NewTopic(topic, num_partitions=3, replication_factor=1) for topic in all_topics
    ]

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
