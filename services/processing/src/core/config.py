from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kafka settings
    kafka_bootstrap: str = "kafka1:19092"
    topic_events: str = "analytics_events"
    topic_event_metrics: str = "event_metrics"
    topic_session_metrics: str = "session_metrics"
    kafka_group_id: str = "flink-analytics-group"
    scan_startup_mode: str = "earliest-offset"

    # Flink settings
    flink_parallelism: int = 2
    checkpoint_interval_ms: int = 30000
    watermark_delay_seconds: int = 10
    window_size_minutes: int = 1
    session_gap_minutes: int = 30

    # Event filtering
    allowed_event_types: list[str] = ["page_view", "click", "conversion", "add_to_cart"]

    # Logging
    log_level: str = "INFO"


settings = Settings()
