import json

from confluent_kafka import Consumer, KafkaException
from src.core.config import settings


class KafkaBatchConsumer:
    def __init__(self, topics: list[str]):
        self.consumer = Consumer(
            {
                "bootsrap.servers": settings.kafka_bootstrap,
                "group.id": settings.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self.consumer.subscribe(topics)
        self.buffers = {topic: [] for topic in topics}

    def consume_batch(self) -> dict[str, list]:
        """Poll Kafka and return batched messages by topic"""
        messages = self.consumer.consume(num_messages=settings.batch_size, timeout=1.0)

        if not messages:
            return {}

        for msg in messages:
            if msg.error():
                if msg.error().code() == KafkaException._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())

            try:
                value = json.loads(msg.value().decode("utf-8"))
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
