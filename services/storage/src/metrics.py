"""Prometheus metrics for storage service (relocated from observability/metrics)."""

from prometheus_client import Counter, Gauge, Histogram

STORAGE_BATCHES = Counter("storage_batches_total", "Total successful batches processed")
STORAGE_RECORDS = Counter("storage_records_total", "Total records stored")
STORAGE_ERRORS = Counter("storage_errors_total", "Total storage processing errors")
STORAGE_COMMITS = Counter("storage_commits_total", "Total successful commits")
STORAGE_RETRIES = Counter("storage_retries_total", "Total retry attempts for inserts")

BATCH_SIZE = Histogram("storage_batch_size", "Distribution of per-topic batch sizes")
CONSUME_CYCLE = Histogram(
    "storage_consume_cycle_seconds", "Total time of a consume + insert + commit cycle"
)
INSERT_LATENCY = Histogram(
    "storage_insert_latency_seconds", "Time spent inserting a batch into ClickHouse"
)

IN_FLIGHT_INSERTS = Gauge(
    "storage_in_flight_inserts", "Current in-flight insert operations"
)
ADAPTIVE_BATCH_TARGET = Gauge(
    "storage_adaptive_batch_target", "Current adaptive batch size target"
)
