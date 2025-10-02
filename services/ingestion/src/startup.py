from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.kafka.admin import create_topics

try:
    from shared.logging.json import configure_logging as shared_configure_logging
except ImportError:
    shared_configure_logging = None

# Expose a module-level name for tests that patch src.startup.configure_logging
# while still delegating to the shared implementation.
configure_logging = shared_configure_logging

logger = get_logger("startup")


def initialize_application():
    """Initialize logging and ensure Kafka topics (order preserved for tests)."""
    logger.info("initializing_application")
    # Configure logging with shared formatter
    if configure_logging:
        configure_logging(
            service=settings.otel_service_name,
            level=settings.app_log_level,
            environment=settings.app_environment,
            redaction_patterns=settings.app_log_redaction_patterns,
        )
    create_topics()
    logger.info(
        "application_initialized",
        extra={
            "kafka_topics": settings.kafka_consumer_topics,
            "otel_service": settings.otel_service_name,
        },
    )
