from pydantic_settings import BaseSettings

from shared.constants import topics as topic_consts


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "kafka1:19092"
    kafka_topic_events: str = topic_consts.EVENTS_TOPIC
    kafka_topic_event_metrics: str = topic_consts.EVENT_METRICS_TOPIC
    kafka_topic_session_metrics: str = topic_consts.SESSION_METRICS_TOPIC
    kafka_topic_performance_metrics: str = topic_consts.PERFORMANCE_METRICS_TOPIC
    kafka_consumer_topics: list[str] = topic_consts.ALL_METRIC_TOPICS
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
