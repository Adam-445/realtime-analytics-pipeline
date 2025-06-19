from confluent_kafka import Producer
from ingestion.track_service.schemas import AnalyticsEvent


class EventProducer:
    def __init__(self):
        self.producer = Producer(
            {
                "bootstrap.servers": "kafka1:19092",
                "acks": "all",
                "batch.size": 1_048_576,  # 1MB batches
                "linger.ms": 20,  # Wait up to 20ms for batching
            }
        )

    def delivery_report(self, err, msg):
        if err:
            # TODO: In prod, log to monitoring system
            print(f"Message delivery failed: {err}")

    def send_event(self, event: AnalyticsEvent):
        self.producer.produce(
            topic="analytics_events",
            key=event.user.id,
            value=event.model_dump_json().encode("utf-8"),
            callback=self.delivery_report,
        )
        self.producer.flush()
