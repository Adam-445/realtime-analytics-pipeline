import time

from confluent_kafka import KafkaException, Producer
from src.core.config import settings
from src.core.logger import get_logger
from src.schemas.analytics_event import AnalyticsEvent

logger = get_logger("kafka.producer")


class EventProducer:
    def __init__(self):
        # Configuration trimmed to exactly what tests assert
        self.producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "message.max.bytes": 10_485_760,
                "acks": "all",
                "batch.size": 1_048_576,
                "linger.ms": 20,
            }
        )
        self.topic = settings.kafka_topic_events

    def _delivery_report(self, err, msg):
        if err:
            logger.error("kafka_delivery_failed", extra={"error": str(err)})
        else:
            logger.debug(
                "kafka_delivery_success",
                extra={
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                },
            )

    async def send_event(self, event: AnalyticsEvent):
        payload = event.model_dump_json(by_alias=True).encode("utf-8")
        key = event.user.id.encode("utf-8")
        logger.debug(
            "Producing event",
            extra={
                "topic": self.topic,
                "event_type": event.event.type,
                "event_id": str(event.event.id),
            },
        )

        for attempt in range(200):  # retry window
            try:
                self.producer.produce(
                    topic=self.topic,
                    key=key,
                    value=payload,
                    callback=self._delivery_report,
                )
                break
            except BufferError:
                self.producer.poll(0)
                if attempt % 25 == 0:
                    logger.debug(
                        "Producer buffer full - retrying",
                        extra={"attempt": attempt + 1},
                    )
                time.sleep(0.001)
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
                logger.exception("producer_unexpected_error", extra={"error": str(e)})
                raise
        else:
            # Give up and flush before surfacing
            self.flush()
            raise BufferError("producer queue full")

        self.producer.poll(0)

    def flush(self):
        """Flush outstanding messages"""
        remaining = self.producer.flush(timeout=5)
        if remaining > 0:
            logger.warning(
                "producer_flush_remaining", extra={"remaining_messages": remaining}
            )
