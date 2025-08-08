from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kafka - Raw Events
    kafka_bootstrap_servers: str = "kafka1:19092"
    kafka_topic_events: str = "analytics_events"
    kafka_consumer_group: str = "cache-metrics-group"
    kafka_consumer_auto_offset_reset: str = "latest"  # or earliest for warm fill

    # Kafka - Flink Processed Metrics
    kafka_topic_event_metrics: str = "event_metrics"
    kafka_topic_session_metrics: str = "session_metrics"
    kafka_topic_performance_metrics: str = "performance_metrics"
    kafka_flink_consumer_group: str = "cache-flink-metrics-group"
    kafka_flink_auto_offset_reset: str = "earliest"  # Get all processed metrics

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # ClickHouse - for cache warming and fallback
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123  # HTTP port, not native port
    clickhouse_db: str = "analytics"
    clickhouse_user: str = "admin"
    clickhouse_password: str = "admin"

    # Aggregation
    bucket_granularity_seconds: int = 1
    supported_windows_seconds: List[int] = [5, 60, 300, 900, 3600]  # Added 15m, 1h
    max_window_seconds: int = 3600  # Extended to 1 hour

    # Cache warming
    enable_cache_warming: bool = False  # Disabled by default for stability
    cache_warming_window_hours: int = 24  # Warm with last 24h of data
    cache_warming_batch_size: int = 1000

    # Cache TTL settings
    raw_metrics_ttl_seconds: int = 3900  # 65 minutes (max_window + buffer)
    flink_metrics_ttl_seconds: int = 86400  # 24 hours for processed metrics
    historical_cache_ttl_seconds: int = 7200  # 2 hours for ClickHouse data

    # Service
    otel_service_name: str = "cache"
    app_environment: str = "production"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
