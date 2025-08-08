import json
import os
import threading
import time

from confluent_kafka import Consumer, KafkaError, Message
from prometheus_client import Counter, Gauge
from src.core.config import settings
from src.core.logger import get_logger
from src.metrics.aggregator import EventAggregator

logger = get_logger("consumer")


class MetricsConsumer:
    def __init__(self, aggregator: EventAggregator | None = None):
        bootstrap = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", settings.kafka_bootstrap_servers
        )
        conf = {
            "bootstrap.servers": bootstrap,
            "group.id": settings.kafka_consumer_group,
            "auto.offset.reset": settings.kafka_consumer_auto_offset_reset,
            "enable.partition.eof": False,
        }
        debug_flags = os.getenv("KAFKA_CONSUMER_DEBUG")
        if debug_flags:
            conf["debug"] = debug_flags
        self._consumer = Consumer(conf)
        self._topic = settings.kafka_topic_events
        self._running = False
        self._thread: threading.Thread | None = None
        self._aggregator = aggregator or EventAggregator()
        self._messages_processed = 0
        self._last_event_ts_ms: int | None = None
        # Prom metrics
        self._processed_counter = Counter(
            "cache_events_processed_total", "Total events processed by cache consumer"
        )
        self._last_event_gauge = Gauge(
            "cache_last_event_timestamp_ms",
            "Timestamp (ms) of last processed event",
        )

    def start(self):
        # Subscribe with assignment callbacks for visibility
        self._consumer.subscribe(
            [self._topic], on_assign=self._on_assign, on_revoke=self._on_revoke
        )
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("MetricsConsumer started", extra={"topic": self._topic})

    def _run_loop(self):
        idle_loops = 0
        while self._running:
            msg: Message | None = self._consumer.poll(timeout=0.5)
            if msg is None:
                idle_loops += 1
                if idle_loops % 40 == 0:  # every ~20s
                    logger.debug(
                        "Consumer idle",
                        extra={
                            "processed": self._messages_processed,
                            "bootstrap": self._consumer.list_topics().orig_broker_name,
                        },
                    )
                continue
            idle_loops = 0
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Kafka error", extra={"error": str(msg.error())})
                continue
            try:
                payload = json.loads(msg.value())
                self._aggregator.process(payload)
                self._messages_processed += 1
                self._processed_counter.inc()
                now_ms = int(time.time() * 1000)
                self._last_event_ts_ms = now_ms
                self._last_event_gauge.set(now_ms)
                if self._messages_processed % 1000 == 0:
                    logger.info(
                        "Processed messages",
                        extra={"count": self._messages_processed},
                    )
            except Exception as e:  # noqa: BLE001
                logger.exception("Failed to process message", extra={"error": str(e)})

    def stop(self):
        self._running = False
        try:
            self._consumer.close()
        finally:
            logger.info(
                "MetricsConsumer stopped",
                extra={"processed": self._messages_processed},
            )

    # --- internal callbacks ---
    def _on_assign(self, consumer: Consumer, partitions):  # noqa: ANN001
        info = [f"{p.topic}[{p.partition}]@{p.offset}" for p in partitions]
        logger.info(
            "Partitions assigned",
            extra={"partitions": info, "topic": self._topic},
        )

    # Optionally seek to beginning if needed for replay
    # (currently default behavior respected)

    def _on_revoke(self, consumer: Consumer, partitions):  # noqa: ANN001
        info = [f"{p.topic}[{p.partition}]" for p in partitions]
        logger.warning(
            "Partitions revoked",
            extra={"partitions": info, "topic": self._topic},
        )
