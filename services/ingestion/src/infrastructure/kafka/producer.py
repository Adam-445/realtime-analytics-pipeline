import logging

from confluent_kafka import KafkaException, Producer
from opentelemetry.instrumentation.confluent_kafka import ConfluentKafkaInstrumentor
from opentelemetry.propagate import inject
from src.core.config import settings
from src.schemas.analytics_event import AnalyticsEvent

logger = logging.getLogger("kafka.producer")


class EventProducer:
    def __init__(self):
        ConfluentKafkaInstrumentor().instrument()
        self.producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "message.max.bytes": 10_485_760,  # 10 MB
                "acks": "all",
                "batch.size": 1_048_576,  # 1MB batches
                "linger.ms": 20,  # Wait up to 20ms for batching
            }
        )
        self.topic = settings.kafka_topic_events

    def _delivery_report(self, err, msg):
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(
                f"Delivered to {msg.topic()}[{msg.partition()}] @ offset {msg.offset()}"
            )

    async def send_event(self, event: AnalyticsEvent):
        try:
            # Inject tracing context into headers
            headers: dict[str, str] = {}
            inject(headers)

            self.producer.produce(
                topic=self.topic,
                key=event.user.id.encode("utf-8"),
                value=event.model_dump_json(by_alias=True).encode("utf-8"),
                headers=headers,
                callback=self._delivery_report,
            )
            # Non-bolcking poll to handle callbacks
            self.producer.poll(0)
        except BufferError:
            logger.warning("Producer queue full - triggering flush")
            self.flush()
            raise
        except KafkaException as e:
            logger.error(f"Kafka error: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected producer error: {e}")
            raise

    def flush(self):
        """Flush outstanding messages"""
        remaining = self.producer.flush(timeout=5)
        if remaining > 0:
            logger.warning(f"{remaining} messages not delivered")
