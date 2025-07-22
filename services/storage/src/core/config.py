from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kafka
    kafka_bootstrap_servers: str = "kafka1:19092"
    kafka_consumer_topics: list[str] = [
        "event_metrics",
        "session_metrics",
        "performance_metrics",
    ]
    storage_kafka_consumer_group: str = "clickhouse-storage"

    # Clickhouse
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 9000
    clickhouse_db: str = "analytics"
    clickhouse_user: str = "admin"
    clickhouse_password: str = "admin"

    # Batching
    storage_batch_size: int = 1000
    storage_poll_interval_seconds: int = 30  # Seconds between consumptions

    # Logging
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

    otel_service_name: str = "storage"
    app_environment: str = "production"


settings = Settings()
