from functools import lru_cache

from src.infrastructure.kafka.producer import EventProducer


@lru_cache
def get_kafka_producer() -> EventProducer:
    """
    Return a singleton EventProducer for the entire application.

    - The first time this function is called, it creates and returns an EventProducer().
    - Subsequent calls return the *same* instance from cache, avoiding re-instantiation.
    """
    return EventProducer()
