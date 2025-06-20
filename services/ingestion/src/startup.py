import logging

from src.infrastructure.kafka.admin import create_topics

logger = logging.getLogger("startup")


def initialize_application():
    # Infrastructure setup
    logger.info("Ensuring Kafka topics exist")
    create_topics()

    logger.info("Application initialization complete")
