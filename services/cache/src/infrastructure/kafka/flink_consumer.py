import json
import threading
import time
from typing import List

from confluent_kafka import Consumer, KafkaError, Message
from prometheus_client import Counter, Gauge
from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.redis.client import RedisMetricsRepository

logger = get_logger("flink_consumer")


class FlinkMetricsConsumer:
    """Consumer for Flink-processed metrics from event_metrics, session_metrics,
    and performance_metrics topics"""

    def __init__(self, repository: RedisMetricsRepository | None = None):
        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": settings.kafka_flink_consumer_group,
                "auto.offset.reset": settings.kafka_flink_auto_offset_reset,
                "enable.partition.eof": False,
            }
        )

        self._topics = [
            settings.kafka_topic_event_metrics,
            settings.kafka_topic_session_metrics,
            settings.kafka_topic_performance_metrics,
        ]

        self._running = False
        self._thread: threading.Thread | None = None
        self._repository = repository or RedisMetricsRepository()
        self._messages_processed = 0

        # Prometheus metrics
        self._processed_counter = Counter(
            "cache_flink_metrics_processed_total",
            "Total Flink metrics processed by cache consumer",
            ["topic", "metric_type"],
        )
        self._last_processed_gauge = Gauge(
            "cache_flink_last_processed_timestamp_ms",
            "Timestamp (ms) of last processed Flink metric",
            ["topic"],
        )
        self._processing_errors = Counter(
            "cache_flink_processing_errors_total",
            "Total processing errors in Flink consumer",
            ["topic", "error_type"],
        )

    def start(self):
        """Start the Flink metrics consumer"""
        self._consumer.subscribe(
            self._topics, on_assign=self._on_assign, on_revoke=self._on_revoke
        )
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("FlinkMetricsConsumer started", extra={"topics": self._topics})

    def _run_loop(self):
        """Main consumer loop"""
        idle_loops = 0
        batch_size = 100
        batch_timeout = 5.0

        while self._running:
            try:
                # Consume messages in batches for better performance
                messages = self._consumer.consume(
                    num_messages=batch_size, timeout=batch_timeout
                )

                if not messages:
                    idle_loops += 1
                    if idle_loops % 20 == 0:  # Log every ~100s
                        logger.debug(
                            "Flink consumer idle",
                            extra={"processed": self._messages_processed},
                        )
                    continue

                idle_loops = 0
                self._process_message_batch(messages)

            except Exception as e:
                logger.error("Error in Flink consumer loop", extra={"error": str(e)})
                time.sleep(5)  # Back off on errors

    def _process_message_batch(self, messages: List[Message]):
        """Process a batch of Kafka messages"""
        event_metrics = []
        session_metrics = []
        performance_metrics = []

        for msg in messages:
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(
                    "Kafka message error",
                    extra={"error": str(msg.error()), "topic": msg.topic()},
                )
                self._processing_errors.labels(
                    topic=msg.topic(), error_type="kafka_error"
                ).inc()
                continue

            try:
                payload = json.loads(msg.value())
                topic = msg.topic()

                # Route to appropriate collection based on topic
                if topic == settings.kafka_topic_event_metrics:
                    event_metrics.append(payload)
                elif topic == settings.kafka_topic_session_metrics:
                    session_metrics.append(payload)
                elif topic == settings.kafka_topic_performance_metrics:
                    performance_metrics.append(payload)

                self._processed_counter.labels(
                    topic=topic, metric_type=topic.replace("_", "")
                ).inc()
                self._last_processed_gauge.labels(topic=topic).set(
                    int(time.time() * 1000)
                )
                self._messages_processed += 1

            except json.JSONDecodeError as e:
                logger.warning(
                    "Invalid JSON in Flink message",
                    extra={"error": str(e), "topic": msg.topic()},
                )
                self._processing_errors.labels(
                    topic=msg.topic(), error_type="json_decode_error"
                ).inc()
            except Exception as e:
                logger.error(
                    "Error processing Flink message",
                    extra={"error": str(e), "topic": msg.topic()},
                )
                self._processing_errors.labels(
                    topic=msg.topic(), error_type="processing_error"
                ).inc()

        # Cache metrics in batches for better performance
        if event_metrics:
            self._repository.cache_flink_event_metrics(event_metrics)
            logger.debug(
                "Cached event metrics batch", extra={"count": len(event_metrics)}
            )

        if session_metrics:
            self._repository.cache_flink_session_metrics(session_metrics)
            logger.debug(
                "Cached session metrics batch", extra={"count": len(session_metrics)}
            )

        if performance_metrics:
            self._repository.cache_flink_performance_metrics(performance_metrics)
            logger.debug(
                "Cached performance metrics batch",
                extra={"count": len(performance_metrics)},
            )

    def stop(self):
        """Stop the Flink metrics consumer"""
        self._running = False
        try:
            self._consumer.close()
        finally:
            logger.info(
                "FlinkMetricsConsumer stopped",
                extra={"processed": self._messages_processed},
            )

    def _on_assign(self, consumer: Consumer, partitions):
        """Callback when partitions are assigned"""
        info = [f"{p.topic}[{p.partition}]@{p.offset}" for p in partitions]
        logger.info("Flink consumer partitions assigned", extra={"partitions": info})

    def _on_revoke(self, consumer: Consumer, partitions):
        """Callback when partitions are revoked"""
        info = [f"{p.topic}[{p.partition}]" for p in partitions]
        logger.warning("Flink consumer partitions revoked", extra={"partitions": info})
