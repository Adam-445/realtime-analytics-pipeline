from pydantic_settings import BaseSettings

from shared.constants import Topics


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "kafka1:19092"
    kafka_topic_events: str = Topics.EVENTS
    kafka_topic_event_metrics: str = Topics.EVENT_METRICS
    kafka_topic_session_metrics: str = Topics.SESSION_METRICS
    kafka_topic_performance_metrics: str = Topics.PERFORMANCE_METRICS
    kafka_consumer_topics: list[str] = Topics.all_metrics_topics()
    kafka_topic_partitions: int = 6
    otel_service_name: str = "ingestion"
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


settings = Settings()
