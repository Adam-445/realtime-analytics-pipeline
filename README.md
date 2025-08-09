# Real-Time Analytics Pipeline [![Project Status: Active](https://img.shields.io/badge/status-active-success.svg)]()

A scalable, real-time analytics pipeline for processing and visualizing event streams. Built with an event-driven architecture using modern tools like Kafka, Flink, Clickhouse, and FastAPI, this system demonstrates low-latency stream processing and end-to-end data flow suitable for high-throughput environments.

> **Note**: This project builds upon the foundational work done in the [lab repository](https://github.com/Adam-445/analytics-pipeline-lab) and extends it into a production-grade system.

## Adding New Jobs to the Pipeline
To add a new processing job to the pipeline:

1. Create a new job class in `src/jobs/`
2. Define output schema in `src/core/schemas/`
3. Register Kafka sink in `src/connectors/kafka_sink.py`
4. Update configuration in `src/core/config.py`
5. Register job in `src/main.py`
6. Create Kafka topic in ingestion service

See [Job Implementation Guide](docs/adding_jobs.md) for details

## Cache Service (Speed Layer)

The `cache` service provides sub-second access to the most recent aggregated metrics emitted by Flink.

Flow: Kafka (event_metrics/session_metrics/performance_metrics) -> Cache Service (Redis) -> REST (and future WebSocket) APIs.

Current endpoints:

- `GET /healthz` – liveness
- `GET /readyz` – readiness (after first Kafka record processed)
- `GET /metrics/event/latest` – latest event metrics window (flattened per event type)
- `GET /metrics/event/windows?limit=N` – last N event windows
- `GET /metrics/performance/windows?limit=N` – last N performance windows
- `GET /metrics/overview` – combined latest event + performance snapshots
- `GET /metrics` – Prometheus metrics

Redis key patterns (abbreviated):

- `metrics:event:{window_start_ms}` (Hash) – flattened counts & user counts
- `metrics:event:windows` (ZSET) – index of window_start values
- `metrics:perf:{window_start_ms}` / `metrics:perf:windows`

Planned (future PRs): WebSocket streaming (`/ws/stream`), active session state, completed session lists, client subscription fanout, raw event tail for mid-window freshness.

Prometheus metrics (selected):

- `cache_records_total` – total Kafka records processed
- `cache_kafka_commits_total` – Kafka offset batch commits
- `cache_queue_size` – current in-memory processing queue length
- `cache_pending_commit_messages` – messages consumed but not yet committed (gauge)
- `cache_redis_batch_seconds` – histogram of Redis pipeline batch execution time

Run (in Docker Compose): the cache service listens on `:8080` and depends on `redis` + `kafka1`.
