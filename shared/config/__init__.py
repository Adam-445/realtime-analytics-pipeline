"""Shared configuration base classes.

Provides common configuration patterns used across all services to reduce
duplication and ensure consistency.
"""

from pydantic_settings import BaseSettings


class BaseLoggingConfig(BaseSettings):
    """Common logging configuration for all services."""

    app_log_level: str = "INFO"
    app_log_redaction_patterns: list[str] = [
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "cookie",
        "session",
    ]
    app_environment: str = "production"


class BaseKafkaConfig(BaseSettings):
    """Common Kafka configuration for all services."""

    kafka_bootstrap_servers: str = "kafka1:19092"


class BaseServiceConfig(BaseLoggingConfig, BaseKafkaConfig):
    """Base configuration combining logging and Kafka settings.

    Services should inherit from this and add their own specific settings.
    The otel_service_name should be overridden by each service.
    """

    otel_service_name: str = "unknown"  # Should be overridden by service


__all__ = ["BaseLoggingConfig", "BaseKafkaConfig", "BaseServiceConfig"]
