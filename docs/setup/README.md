# Setup

This section documents how to build, run, and verify the full stack locally using Docker Compose, as well as how to run tests and performance checks.

- See also: [Architecture](../architecture/README.md), [Testing](../testing/README.md), [Troubleshooting](../troubleshooting/README.md)

## Prerequisites

- Docker and Docker Compose
- Bash-compatible shell

## Quick Start (Local)

The full environment is defined in `infrastructure/compose/docker-compose.yml` (and `docker-compose.test.yml` for testing overlays).

1. Build images and start the stack.
2. Verify health endpoints and UIs.

Example invocation is automated via `run-tests.sh` for tests; to run services manually see the compose files. If you need exact commands, consult the compose files and service `bin/entrypoint.sh` scripts.

## Services and Infrastructure

- [Ingestion](./services/ingestion.md)
- [Processing](./services/processing.md)
- [Storage](./services/storage.md)
- [Cache](./services/cache.md)
- [Kafka & Zookeeper](./infrastructure/kafka.md)
- [ClickHouse](./infrastructure/clickhouse.md)
- [Redis](./infrastructure/redis.md)
- [Monitoring (Prometheus/Grafana)](./infrastructure/monitoring.md)

## Health and Metrics

- Ingestion: `GET /v1/healthz`, `GET /metrics`
- Cache: `GET /healthz`, `GET /readyz`, `GET /metrics`
- Storage: `GET /healthz` (internal)
- Flink metrics: Prometheus port 9249; JobManager UI on 8081

## Environments

Runtime configuration is primarily via environment variables surfaced by service settings (see each service's `src/core/config.py`). For Kafka topic names and shared constants, see `shared/constants/*`.

## Tests

Use the provided test runner:

- Unit, integration, e2e, performance: see [Testing](../testing/README.md)

## Next

- Explore [Modules](../modules/README.md) for detailed service internals.
