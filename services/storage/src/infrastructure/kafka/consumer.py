from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List

from confluent_kafka import Consumer, KafkaError, KafkaException
from src.core.config import settings

TimestampedRecord = Dict[str, object]
BatchMap = Dict[str, List[TimestampedRecord]]

_TS_FIELDS = {"window_start", "window_end", "start_time", "end_time"}


def _maybe_parse_timestamp(value: str):  # pragma: no cover - trivial
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return value


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
        self.buffers: BatchMap = {topic: [] for topic in topics}

    def consume_batch(self) -> BatchMap:
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
                for field in _TS_FIELDS:
                    if field in value and isinstance(value[field], str):
                        value[field] = _maybe_parse_timestamp(value[field])
                self.buffers[msg.topic()].append(value)
            except json.JSONDecodeError:
                continue
        result = {k: v.copy() for k, v in self.buffers.items()}
        for v in self.buffers.values():
            v.clear()
        return result

    def poll_batch(self) -> BatchMap:  # pragma: no cover - wrapper
        return self.consume_batch()

    def commit(self) -> None:
        self.consumer.commit()
