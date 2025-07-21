import logging

from src.core.logging_config import configure_logging
from src.core.tracing import configure_tracing
from src.infrastructure.kafka.admin import create_topics

logger = logging.getLogger("startup")


def initialize_application():
    configure_logging()

    create_topics()
    logger.info("Ensured Kafka topics exist")

    configure_tracing()
    logger.info("Tracing setup complete")

    logger.info("Application initialization complete")
