from pydantic_settings import BaseSettings

# Shared topic constants (with fallback for legacy environments)
try:  # pragma: no cover
    from shared.constants.topics import (
        EVENT_METRICS_TOPIC,
        EVENTS_TOPIC,
        PERFORMANCE_METRICS_TOPIC,
        SESSION_METRICS_TOPIC,
    )
except Exception:  # noqa: pragma: no cover
    EVENTS_TOPIC = "analytics_events"  # type: ignore
    EVENT_METRICS_TOPIC = "event_metrics"  # type: ignore
    SESSION_METRICS_TOPIC = "session_metrics"  # type: ignore
    PERFORMANCE_METRICS_TOPIC = "performance_metrics"  # type: ignore


class Settings(BaseSettings):
    # Kafka settings
    kafka_bootstrap_servers: str = "kafka1:19092"
    kafka_topic_events: str = EVENTS_TOPIC
    kafka_topic_event_metrics: str = EVENT_METRICS_TOPIC
    kafka_topic_session_metrics: str = SESSION_METRICS_TOPIC
    kafka_topic_performance_metrics: str = PERFORMANCE_METRICS_TOPIC
    processing_kafka_consumer_group: str = "flink-analytics-group"
    processing_kafka_scan_startup_mode: str = "earliest-offset"

    # Flink settings
    flink_parallelism: int = 2
    # Checkpoint interval (override with FLINK_CHECKPOINT_INTERVAL_MS in env)
    flink_checkpoint_interval_ms: int = 30000
    flink_watermark_delay_seconds: int = 10
    flink_idle_timeout_seconds: int = 5
    processing_metrics_window_size_seconds: int = 60
    processing_performance_window_size_seconds: int = 300
    processing_session_gap_seconds: int = 1800

    # Table/Planner mini-batch tuning
    table_minibatch_enabled: bool = True
    table_minibatch_latency_seconds: int = 4
    table_minibatch_size: int = 999

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
