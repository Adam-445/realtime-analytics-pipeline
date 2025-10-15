# Ingestion Service Setup

FastAPI application that accepts analytics events and publishes them to Kafka.

- Source: `services/ingestion`
- Entrypoint: `services/ingestion/src/main.py`
- API router: `services/ingestion/src/api/v1/router.py`
- Event schema: `services/ingestion/src/schemas/analytics_event.py`

## Runtime

- Ports: 8000 (HTTP)
- Health: `GET /v1/healthz`
- Metrics: `GET /metrics` (Prometheus multiprocess)
- Kafka: produces to `shared/constants/topics.py::Topics.EVENTS`

## Configuration

Defined in `services/ingestion/src/core/config.py` (pydantic-settings):

- `kafka_bootstrap_servers` (default: `kafka1:19092`)
- `kafka_topic_events` and metric topics
- `kafka_topic_partitions`
- `otel_service_name`, `app_environment`
- Logging: `app_log_level`, `app_log_redaction_patterns`

## Compose Integration

Service defined in `infrastructure/compose/docker-compose.yml` as `ingestion`.

- Depends on Kafka
- Shares `../../shared` as read-only volume
- Healthcheck probes `/v1/healthz`

## Notes

- Metrics directory is controlled via `PROMETHEUS_MULTIPROC_DIR`.
- Use [API docs](../../api/README.md) for request/response details.
