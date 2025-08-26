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

    # Batching / performance
    storage_batch_size: int = 1000
    storage_poll_interval_seconds: int = 30  # fallback sleep when idle
    storage_max_workers: int = 10  # reserved for future thread pool sizing
    storage_max_concurrent_inserts: int = 4
    storage_adaptive_batching_enabled: bool = False
    storage_min_batch_size: int = 200
    storage_max_batch_size: int = 5000
    storage_target_cycle_seconds: float = 1.5  # desired consume+insert cadence
    storage_skip_sleep_if_full: bool = True  # skip idle sleep when batch full

    # Health / metrics
    health_port: int = 8081

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
