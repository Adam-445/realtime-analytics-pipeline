# Storage Internals

Consumes Kafka metric topics and persists aggregates to ClickHouse with controlled batching and concurrency.

- Source: `services/storage`
- Entrypoint: `services/storage/src/main.py`
- Processor: `services/storage/src/services/processor.py`
- Kafka consumer: `services/storage/src/infrastructure/kafka/consumer.py`
- ClickHouse client + DDL: `services/storage/src/infrastructure/clickhouse/*`

## Topics and Tables

The service subscribes to metric topics defined in `shared/constants/topics.py` and ensures corresponding tables exist at startup.

ClickHouse table definitions (`.../clickhouse/ddl.py`):

- `event_metrics`
  - `window_start DateTime64(3)`, `window_end DateTime64(3)`
  - `event_type String`, `event_count UInt64`, `user_count UInt64`
  - ENGINE MergeTree, ORDER BY `(window_start, event_type)`
- `session_metrics`
  - `session_id String`, `user_id String`
  - `start_time DateTime64(3)`, `end_time DateTime64(3)`, `duration UInt64`, `page_count UInt64`, `device_category String`
  - ENGINE MergeTree, ORDER BY `(start_time, session_id)`
- `performance_metrics`
  - `window_start DateTime64(3)`, `window_end DateTime64(3)`, `device_category String`
  - `avg_load_time Float64`, `p95_load_time Float64`
  - ENGINE MergeTree, ORDER BY `(window_start, device_category)`

## Consumer and Batching

`KafkaBatchConsumer`:
- Subscribes to all metric topics with group `storage_kafka_consumer_group` (default `clickhouse-storage`).
- `auto.offset.reset = earliest`, manual commit only after successful inserts.
- Parses JSON, with light timestamp normalization for fields: `window_start`, `window_end`, `start_time`, `end_time`.
- `consume_batch()` returns a map of `topic -> list[dict]` up to `storage_batch_size`.

`process_batches()` loop:
- Polls batches, inserts per topic concurrently up to `storage_max_concurrent_inserts`.
- Bounded retries per insert with exponential backoff, observed via metrics.
- Commits offsets only if all inserts in the cycle succeed.
- Adaptive sleep: skip sleep if any batch reached `storage_batch_size` and `storage_skip_sleep_if_full` is true.

## ClickHouse Client

- Ensures tables on startup (`ALL_DDLS`).
- Serializes inserts with an `RLock` to avoid `PartiallyConsumedQueryError` from overlapping queries on a single connection.
- Builds `INSERT INTO <table>(cols...) VALUES` with positional tuples derived from keys of the first row.

## Configuration (selected)

From `services/storage/src/core/config.py`:

- Kafka: `kafka_bootstrap_servers`, `kafka_consumer_topics`, `storage_kafka_consumer_group`
- ClickHouse: `clickhouse_host`, `clickhouse_port`, `clickhouse_db`, `clickhouse_user`, `clickhouse_password`
- Batching: `storage_batch_size`, `storage_poll_interval_seconds`, `storage_max_concurrent_inserts`
- Adaptive batching: `storage_adaptive_batching_enabled`, `storage_min_batch_size`, `storage_max_batch_size`, `storage_target_cycle_seconds`, `storage_skip_sleep_if_full`
- Health/metrics: `metrics_port` (default 8001), `health_port` (8081)

Quick reference:

| Key | Default | Purpose |
| --- | --- | --- |
| kafka_bootstrap_servers | kafka1:19092 | Kafka brokers |
| kafka_consumer_topics | [event_metrics, session_metrics, performance_metrics] | Subscribed topics |
| storage_kafka_consumer_group | clickhouse-storage | Consumer group |
| clickhouse_host | clickhouse | ClickHouse host |
| clickhouse_port | 9000 | ClickHouse native port |
| clickhouse_db | analytics | Database name |
| clickhouse_user | admin | Username |
| clickhouse_password | admin | Password |
| storage_batch_size | 1000 | Max messages per poll |
| storage_poll_interval_seconds | 30 | Idle sleep when no messages |
| storage_max_concurrent_inserts | 4 | Concurrent topic inserts |
| storage_adaptive_batching_enabled | false | Enable adaptive batch sizing |
| storage_min_batch_size | 200 | Lower bound for adaptive |
| storage_max_batch_size | 5000 | Upper bound for adaptive |
| storage_target_cycle_seconds | 1.5 | Target consume+insert cycle |
| storage_skip_sleep_if_full | true | Skip sleep if any batch full |
| metrics_port | 8001 | Prometheus metrics port |
| health_port | 8081 | Healthz server port (internal) |

## Health and Metrics

- Health endpoint: HTTP server on `health_port` serving `/healthz` with `{ "status": "ok" }`.
- Prometheus metrics: started on `metrics_port` (default 8001).
- Key metrics (from `core/metrics.py`): batch size, insert latency, in-flight inserts, batches, commits, errors, retries, and consume cycle time.

## Observability and Operations

- Logs: JSON with redaction patterns from settings.
- Failure behavior: on insert failure, offsets are not committed; messages will reprocess.
- Tune `storage_poll_interval_seconds` and concurrency to balance throughput vs. DB pressure.

## Related

- Upstream producers and schemas: see [Processing Internals](../processing/README.md)
- End-to-end verification: `tests/e2e/test_full_pipeline.py`
