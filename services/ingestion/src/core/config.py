from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "kafka1:19092"
    kafka_topic_events: str = "analytics_events"
    kafka_topic_event_metrics: str = "event_metrics"
    kafka_topic_session_metrics: str = "session_metrics"
    kafka_topic_performance_metrics: str = "performance_metrics"
    kafka_consumer_topics: list[str] = [
        "event_metrics",
        "session_metrics",
        "performance_metrics",
    ]
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
