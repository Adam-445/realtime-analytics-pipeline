# ClickHouse

Analytical storage for persisted metrics.

- Image: `clickhouse/clickhouse-server:25.6`
- Ports: 8123 (HTTP), 9000 (native)
- Default DB: `analytics`

## Health

Compose healthcheck uses `/ping` endpoint.

## Access

- From host: `http://localhost:8123`
- From containers: `http://clickhouse:8123`

## Schema

Tables for `event_metrics`, `session_metrics`, and `performance_metrics` are created by the storage service at startup (see `services/storage/src/infrastructure/clickhouse/ddl.py`).
