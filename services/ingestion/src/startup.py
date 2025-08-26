from src.core.config import settings
from src.core.logger import get_logger
from src.core.logging_config import configure_logging  # local compatibility shim
from src.infrastructure.kafka.admin import create_topics

logger = get_logger("startup")


def initialize_application():
    """Initialize application resources.

    Order preserved for legacy unit tests: configure_logging -> create_topics.
    """
    logger.info("Starting application initialization")
    # Local configure_logging has no parameters (legacy signature expected by tests)
    configure_logging()
    create_topics()
    logger.info(
        "Application initialization complete",
        extra={
            "kafka_topics": settings.kafka_consumer_topics,
            "otel_service": settings.otel_service_name,
        },
    )
