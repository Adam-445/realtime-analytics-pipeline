"""
Prometheus metrics for the cache service Kafka -> Redis ingestion path.

All metric names share the cache_ prefix. Naming conventions:
  cache_kafka_* for Kafka consumption / commit related metrics
  cache_redis_* for Redis write pipeline metrics
  cache_queue_* for internal buffering / backpressure indicators
"""

from prometheus_client import Counter, Gauge, Histogram

# Kafka consumption
KAFKA_RECORDS_TOTAL = Counter(
    "cache_kafka_records_total", "Total Kafka records consumed (pre-filter)."
)
KAFKA_COMMIT_BATCHES_TOTAL = Counter(
    "cache_kafka_commit_batches_total", "Number of Kafka offset commit batches."
)

# Internal queue / buffering
QUEUE_CURRENT_SIZE = Gauge(
    "cache_queue_current_size", "Current size of the in-memory operation queue."
)
KAFKA_PENDING_MESSAGES = Gauge(
    "cache_kafka_pending_messages", "Messages parsed but not yet committed."
)

# Redis pipeline
REDIS_BATCH_ERRORS_TOTAL = Counter(
    "cache_redis_batch_errors_total", "Count of Redis batch write failures."
)
REDIS_BATCH_LATENCY_SECONDS = Histogram(
    "cache_redis_batch_latency_seconds", "Latency of Redis batch apply operations."
)
