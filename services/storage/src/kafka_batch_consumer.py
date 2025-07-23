import json
from datetime import datetime

from confluent_kafka import Consumer, KafkaError, KafkaException
from src.core.config import settings


class KafkaBatchConsumer:
    def __init__(self, topics: list[str]):
        self.consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": settings.storage_kafka_consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self.consumer.subscribe(topics)
        self.buffers = {topic: [] for topic in topics}

    def consume_batch(self) -> dict[str, list]:
        """Poll Kafka and return batched messages by topic"""
        messages = self.consumer.consume(
            num_messages=settings.storage_batch_size, timeout=1.0
        )

        if not messages:
            return {}

        for msg in messages:
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())

            try:
                value = json.loads(msg.value().decode("utf-8"))

                # Format timestamp fields since they are currently strings
                for timestamp_field in [
                    "window_start",
                    "window_end",
                    "start_time",
                    "end_time",
                ]:
                    if timestamp_field in value:
                        value[timestamp_field] = datetime.fromisoformat(
                            value[timestamp_field].replace("Z", "+00:00")
                        )
                self.buffers[msg.topic()].append(value)
            except json.JSONDecodeError:
                continue

        # Return copy of buffers and reset
        results = {k: v.copy() for k, v in self.buffers.items()}
        for buffer in self.buffers.values():
            buffer.clear()

        return results

    def commit(self):
        self.consumer.commit()
