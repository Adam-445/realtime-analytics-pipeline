from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap: str = "kafka1:19092"
    topic_events: str = "analytics_events"
    topic_event_metrics: str = "event_metrics"
    topic_session_metrics: str = "session_metrics"


settings = Settings()
