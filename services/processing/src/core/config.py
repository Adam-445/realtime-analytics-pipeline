from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kafka settings
    kafka_bootstrap_servers: str = "kafka1:19092"
    kafka_topic_events: str = "analytics_events"
    kafka_topic_event_metrics: str = "event_metrics"
    kafka_topic_session_metrics: str = "session_metrics"
    kafka_topic_performance_metrics: str = "performance_metrics"
    processing_kafka_consumer_group: str = "flink-analytics-group"
    processing_kafka_scan_startup_mode: str = "earliest-offset"

    # Flink settings
    flink_parallelism: int = 2
    flink_checkpoint_interval_ms: int = 30000
    flink_watermark_delay_seconds: int = 10
    flink_idle_timeout_seconds: int = 5
    processing_metrics_window_size_seconds: int = 60
    processing_performance_window_size_seconds: int = 300
    processing_session_gap_seconds: int = 1800

    # Event filtering
    processing_allowed_event_types: list[str] = [
        "page_view",
        "click",
        "conversion",
        "add_to_cart",
    ]

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

    app_environment: str = "production"
    otel_service_name: str = "processing"


settings = Settings()
