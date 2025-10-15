# Processing Service Setup

Apache Flink streaming jobs that consume raw events and produce aggregated metrics.

- Source: `services/processing`
- Entrypoint: `services/processing/src/main.py`
- Jobs: `services/processing/src/jobs/*.py` (e.g., `EventAggregator`, `SessionTracker`, `PerformanceTracker`)
- Coordinator: `services/processing/src/core/job_coordinator.py`

## Runtime

- Flink JobManager: 8081 (UI)
- Prometheus metrics: 9249 (reporter enabled in JobManager/TaskManagers)

## Kafka Topics

- Input: `analytics_events`
- Output: `event_metrics`, `session_metrics`, `performance_metrics`

See `shared/constants/topics.py` for canonical names.

## Configuration

- Window sizes, allowed event types, and time attributes are configured via `services/processing/src/core/config.py`.
- Jobs typically decide between `event_time` and `proc_time` based on environment.

## Extending

Follow the guide: [Adding a New Job](../../adding_jobs.md).
- Implement a `BaseJob` subclass in `src/jobs/`.
- Register sink schemas and connectors.
- Register the job in `src/main.py` via `JobCoordinator().register_job(...)`.

## Compose Integration

- Flink cluster services: `jobmanager`, `taskmanager1`, `taskmanager2`.
- The `processing` container runs the Python driver with Flink dependencies and submits jobs or executes them.
