from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.kafka.admin import create_topics

try:
    from shared.logging.json import configure_logging as shared_configure_logging
except ImportError:
    shared_configure_logging = None

logger = get_logger("startup")


def initialize_application():
    """Initialize application resources.

    Order preserved for legacy unit tests: configure_logging -> create_topics.
    """
    logger.info("Starting application initialization")
    # Configure logging using shared implementation
    if shared_configure_logging:
        shared_configure_logging(
            service=settings.otel_service_name,
            level=settings.app_log_level,
            environment=settings.app_environment,
            redaction_patterns=settings.app_log_redaction_patterns,
        )
    create_topics()
    logger.info(
        "Application initialization complete",
        extra={
            "kafka_topics": settings.kafka_consumer_topics,
            "otel_service": settings.otel_service_name,
        },
    )
