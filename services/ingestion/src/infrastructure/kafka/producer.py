from confluent_kafka import KafkaException, Producer
from src.core.config import settings
from src.core.logger import get_logger
from src.schemas.analytics_event import AnalyticsEvent

logger = get_logger("kafka.producer")


class EventProducer:
    def __init__(self):
        self.producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "message.max.bytes": 10_485_760,  # 10 MB
                "acks": "1",  # Fastest while ensuring leader persistence
                "batch.size": 262_144,  # 256KB - optimal for high throughput
                "linger.ms": 0,  # No batching delay - maximum speed
                "compression.type": "lz4",  # Fastest compression
                "retry.backoff.ms": 50,  # Faster retries
                "request.timeout.ms": 10000,  # Reduced timeout
                "delivery.timeout.ms": 30000,
                "max.in.flight.requests.per.connection": 100,  # Increased parallelism
                "enable.idempotence": False,  # Disable for max performance
                "retries": 3,  # Reduce retry attempts
                "queue.buffering.max.messages": 1000000,  # Large buffer
                "queue.buffering.max.kbytes": 2097151,  # 2GB-1KB buffer
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

            self.producer.produce(
                topic=self.topic,
                key=event.user.id.encode("utf-8"),
                value=event.model_dump_json(by_alias=True).encode("utf-8"),
                callback=self._delivery_report,
            )
            # Non-bolcking poll to handle callbacks
            self.producer.poll(0)
        except BufferError:
            logger.warning("Producer queue full - triggering flush")
            self.flush()
            raise
        except KafkaException as e:
            logger.error(
                "Kafka produce error",
                extra={
                    "event_id": str(event.event.id),
                    "error_code": e.args[0].code(),
                    "retriable": e.retriable(),
                },
            )
            raise
        except Exception as e:
            logger.exception(f"Unexpected producer error: {e}")
            raise

    def flush(self):
        """Flush outstanding messages"""
        remaining = self.producer.flush(timeout=5)
        if remaining > 0:
            logger.warning(f"{remaining} messages not delivered")
