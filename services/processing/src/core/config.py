from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap: str = "kafka1:19092"
    topic_events: str = "analytics_events"
    topic_metrics: str = "aggregated_metrics"


settings = Settings()
