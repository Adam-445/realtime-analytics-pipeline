from src.core.config import settings
from src.core.logger import get_logger
from src.core.logging_config import configure_logging
from src.core.tracing import configure_tracing
from src.infrastructure.kafka.admin import create_topics

logger = get_logger("startup")


def initialize_application():
    logger.info("Starting application initialization")
    configure_logging()

    create_topics()

    configure_tracing()

    logger.info(
        "Application initialization complete",
        extra={
            "kafka_topics": settings.kafka_consumer_topics,
            "otel_service": settings.otel_service_name,
        },
    )
