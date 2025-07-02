from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kafka
    kafka_bootstrap: str = "kafka1:19092"
    topics: list[str] = ["event_metrics", "session_metrics", "performance_metrics"]
    consumer_group: str = "clickhouse-storage"

    # Clickhouse
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 9000
    clickhouse_db: str = "analytics"
    clickhouse_user: str = "admin"
    clickhouse_password: str = "admin"

    # Batching
    batch_size: int = 1000
    poll_interval_seconds: int = 30  # Seconds between consumptions

    # Logging
    log_level: str = "INFO"


settings = Settings()
