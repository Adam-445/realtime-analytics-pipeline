from functools import lru_cache

from src.infrastructure.kafka.producer import EventProducer


@lru_cache
def get_kafka_producer() -> EventProducer:
    """Cached EventProducer singleton."""
    return EventProducer()
