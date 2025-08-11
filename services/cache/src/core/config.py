from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kafka
    kafka_bootstrap_servers: str = "kafka1:19092"
    cache_kafka_topics: list[str] = [
        "event_metrics",
        # "session_metrics", # TODO: add when session caching implemented
        "performance_metrics",
    ]
    cache_kafka_consumer_group: str = "cache-service"
    cache_consume_from: str = "latest"  # earliest|latest

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # Windows / retention
    window_retention_count: int = 120  # keep last 120 windows (e.g., 2h @1m)
    window_hash_ttl_seconds: int = 21600  # 6h safety TTL

    # Sessions
    active_session_ttl_seconds: int = 1900  # slightly above processing_session_gap

    # Websocket / publishing
    websocket_broadcast_batch_ms: int = 250

    # Batching / performance
    kafka_commit_batch_size: int = 100
    kafka_commit_interval_ms: int = 1000
    redis_write_batch_size: int = 50
    redis_queue_max_size: int = 5000

    # Health / lag thresholds
    ready_lag_threshold: int = 5_000  # messages

    # Logging
    app_log_level: str = "INFO"
    app_log_redaction_patterns: list[str] = [
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "cookie",
    ]

    otel_service_name: str = "cache"
    app_environment: str = "production"


settings = Settings()
