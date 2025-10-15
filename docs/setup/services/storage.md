# Storage Service Setup

Consumes Kafka metric topics and persists records to ClickHouse.

- Source: `services/storage`
- Entrypoint: `services/storage/src/main.py`
- Consumer: `services/storage/src/infrastructure/kafka/consumer.py`
- ClickHouse client/DDL: `services/storage/src/infrastructure/clickhouse/`

## Runtime

- Metrics: Prometheus client exposed on `settings.metrics_port` (default 8001)
- Health: `GET /healthz` served by a lightweight HTTP server inside the process

## Configuration

- See `services/storage/src/core/config.py` for Kafka, ClickHouse, and logging settings.
- Topic list is verified on startup by `ensure_topics_available`.

## Compose Integration

- Depends on `clickhouse` and `kafka1`.
- Healthcheck probes `/healthz`.
- Shares `../../shared` as read-only volume.

## ClickHouse

- Default DB: `analytics` (see compose env vars)
- Tables: created by the service (see DDL helpers) aligned with metric topics.
