# Cache Service Setup

Consumes metric topics and maintains windowed aggregates in Redis for low-latency access. Exposes FastAPI endpoints.

- Source: `services/cache`
- Entrypoint: `services/cache/src/main.py`
- Kafka consumer: `services/cache/src/infrastructure/kafka/consumer.py`
- Redis repository: `services/cache/src/infrastructure/redis/repository.py`

## Runtime

- Ports: 8080 (HTTP)
- Health: `GET /healthz` (pings Redis), `GET /readyz` (consumer ready)
- Metrics: `GET /metrics`

## Configuration

- Redis host/port/db via `services/cache/src/core/config.py`.
- Window retention and TTL via settings.

## Compose Integration

- Depends on `kafka1` and `redis`.
- Healthcheck probes `/healthz`.
- Shares `../../shared` as read-only volume.
