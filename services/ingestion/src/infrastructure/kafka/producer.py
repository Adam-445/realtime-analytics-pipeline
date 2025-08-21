import time

from confluent_kafka import Producer
from src.core.config import settings
from src.core.logger import get_logger
from src.schemas.analytics_event import AnalyticsEvent

logger = get_logger("kafka.producer")


class EventProducer:
    def __init__(self):
        self.producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                # Throughut & batching
                "compression.type": "lz4",
                "linger.ms": 10,
                "batch.size": 524288,
                "message.max.bytes": 10_485_760,
                # Queue capacity (avoid BufferError under bursts)
                "queue.buffering.max.kbytes": 1_048_576,
                "queue.buffering.max.messages": 200000,
                # Durability/ordering
                "enable.idempotence": True,
                # Timeouts
                "request.timeout.ms": 10000,
                "delivery.timeout.ms": 30000,
                # Reduce callback overhead
                "delivery.report.only.error": True,
            }
        )
        self.topic = settings.kafka_topic_events

    def _delivery_report(self, err, msg):
        if err:
            logger.error(f"Message delivery failed: {err}")

    async def send_event(self, event: AnalyticsEvent):
        payload = event.model_dump_json(by_alias=True).encode("utf-8")
        key = event.user.id.encode("utf-8")

        for _ in range(200):  # ~ a few ms worst case under burst
            try:
                self.producer.produce(
                    topic=self.topic,
                    key=key,
                    value=payload,
                    callback=self._delivery_report,
                )
                break
            except BufferError:
                # queue full: give librdkafka a chance to drain
                self.producer.poll(0)
                # tiny sleep avoids tight spin under extreme bursts
                time.sleep(0.001)
        else:
            # After brief backpressure, surface the condition
            raise BufferError("producer queue full")

        # service internal timers / error callbacks occasionally
        if getattr(self, "_poll_counter", 0) % 16 == 0:
            self.producer.poll(0)
        self._poll_counter = getattr(self, "_poll_counter", 0) + 1

    def flush(self):
        """Flush outstanding messages"""
        remaining = self.producer.flush(timeout=5)
        if remaining > 0:
            logger.warning(f"{remaining} messages not delivered")
