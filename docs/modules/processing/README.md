# Processing Internals

This document explains how the processing service (Apache Flink) consumes raw events, executes streaming jobs, and emits aggregated metrics.

- Source: `services/processing`
- Entrypoint: `services/processing/src/main.py`
- Coordinator: `services/processing/src/core/job_coordinator.py`
- Jobs: `services/processing/src/jobs/*.py`
- Connectors: `services/processing/src/connectors/*.py`
- Schemas: `services/processing/src/core/schemas/*.py`

## Architecture Overview

The service uses a `JobCoordinator` to:
- Configure the Flink runtime and Table API settings
- Register Kafka source and sinks
- Register and execute all jobs within a single `StatementSet`

See `services/processing/src/main.py` where `EventAggregator`, `SessionTracker`, and `PerformanceTracker` are registered.

## Source and Sinks

- Source table `events` is created from Kafka in `connectors/kafka_source.py` using schema `core/schemas/event_source.py`.
- Sinks for `event_metrics`, `session_metrics`, and `performance_metrics` are created in `connectors/kafka_sink.py` using their respective schemas in `core/schemas`.
- Topic names are centralized in `shared/constants/topics.py` and surfaced in processing settings.

### Kafka connector options of note

- Source (`kafka_source.py`):
	- `properties.group.id = settings.processing_kafka_consumer_group`
	- `scan.startup.mode = settings.processing_kafka_scan_startup_mode` (default: `earliest-offset`)
	- `format = json`, `json.ignore-parse-errors = true`, `json.fail-on-missing-field = false`
- Sinks (`kafka_sink.py`):
	- `sink.transactional-id-prefix` is set per sink to support transactional writes

## Time Attributes and Watermarks

The event source schema defines time attributes and watermarks:
- In production, `event_time` is used with a watermark delay: `event_time - INTERVAL '<flink_watermark_delay_seconds>' SECOND`.
- In non-production, a `proc_time` field is added for processing-time execution.

Jobs can select `event_time` vs `proc_time` based on environment to ensure predictable behavior locally and correct semantics in production.

Environment-specific behavior:
- `app_environment = production`: uses `event_time` with watermarks and `flink_watermark_delay_seconds`
- non-production: injects `proc_time = PROCTIME()` to avoid watermark configuration when developing locally

## Windows and Aggregations

Window sizes and session gaps are defined in `core/config.py`:
- `processing_metrics_window_size_seconds`
- `processing_performance_window_size_seconds`
- `processing_session_gap_seconds`

Example: `EventAggregator` uses tumble windows sized by `processing_metrics_window_size_seconds` and filters allowed event types from `processing_allowed_event_types`.

## Configuration

Key settings in `core/config.py` (pydantic-settings):
- Kafka: bootstrap servers, topics, consumer group, startup mode
- Flink: parallelism, checkpoint interval, watermark delay, idle timeout
- Table planner: mini-batch enablement, latency, size, default parallelism
- Filtering: `processing_allowed_event_types`
- Environment and logging: `app_environment`, `otel_service_name`, `app_log_level`

Quick reference (selected keys and defaults from `core/config.py`):

| Key | Default | Purpose |
| --- | --- | --- |
| kafka_bootstrap_servers | kafka1:19092 | Kafka broker list |
| kafka_topic_events | analytics_events | Source topic |
| kafka_topic_event_metrics | event_metrics | Sink topic |
| kafka_topic_session_metrics | session_metrics | Sink topic |
| kafka_topic_performance_metrics | performance_metrics | Sink topic |
| processing_kafka_consumer_group | flink-analytics-group | Consumer group for source |
| processing_kafka_scan_startup_mode | earliest-offset | Startup mode (earliest/latest) |
| flink_parallelism | 2 | Default operator/statement parallelism |
| flink_checkpoint_interval_ms | 30000 | Checkpoint interval |
| flink_watermark_delay_seconds | 10 | Event-time watermark delay |
| flink_idle_timeout_seconds | 5 | Source idle timeout |
| table_minibatch_enabled | true | Table API mini-batch toggle |
| table_minibatch_latency_seconds | 4 | Max mini-batch latency |
| table_minibatch_size | 999 | Mini-batch size |
| processing_metrics_window_size_seconds | 60 | Event metrics window size |
| processing_performance_window_size_seconds | 300 | Performance window size |
| processing_session_gap_seconds | 1800 | Session gap |
| processing_allowed_event_types | [page_view, click, conversion, add_to_cart] | Filter set |

## Job Lifecycle

- Implement a job as a subclass of `BaseJob` defining `build_pipeline(self, t_env)` and a `sink_name`.
- Register the job with `JobCoordinator.register_job(job)`.
- During `execute()`, the coordinator adds each job’s pipeline to a single `StatementSet` with inserts into the configured sink tables and executes them.

Execution flow (simplified):
1. `JobCoordinator` configures Flink and Table settings
2. Registers source and sink tables
3. Each job builds a `Table` pipeline and is added to a `StatementSet`
4. `StatementSet.execute()` submits all inserts atomically from the driver

## Observability

- Flink JobManager UI: port 8081 (see compose)
- Prometheus metrics reporter: port 9249 on JobManager and TaskManagers
- Service logs use JSON formatting with redaction patterns from settings

Operational notes:
- The Flink JobManager and TaskManagers expose Prometheus metrics on 9249 (see compose)
- JSON source parsing is fault-tolerant by default; malformed records are ignored (`json.ignore-parse-errors = true`)
- Tune mini-batch options and parallelism to balance throughput and latency

## Extending

- Follow [Adding a New Processing Job](./adding-jobs.md) for end-to-end steps.
- When introducing a new sink, add a schema in `core/schemas`, register a sink in `connectors/kafka_sink.py`, and register it in `JobCoordinator._register_connectors()`.
- If the storage pipeline consumes the new topic, update ClickHouse DDL in `services/storage/src/infrastructure/clickhouse/ddl.py` and consumer routing.

## Failure Modes and Recovery

- Kafka acts as the durable boundary; ensure idempotent aggregations where practical.
- Checkpoint interval is configured via `flink_checkpoint_interval_ms`. Align with sink semantics for delivery guarantees.
- Tune `flink_idle_timeout_seconds` and mini-batch settings to balance latency and throughput.
