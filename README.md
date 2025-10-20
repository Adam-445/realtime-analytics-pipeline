## Real-Time Analytics Pipeline

A compact, production-grade pipeline for ingesting, processing, and serving analytics in real time. The stack uses FastAPI (ingestion, cache), Kafka, Flink, ClickHouse, Redis, and Prometheus/Grafana for observability.

Note: This project builds upon the foundational work in the [analytics-pipeline-lab](https://github.com/Adam-445/analytics-pipeline-lab) and evolves it into a more production-ready system.

## Quick start

Prerequisites:
- Docker and Docker Compose

Bring the full stack up:

```bash
docker compose -f infrastructure/compose/docker-compose.yml up -d --build
```

Verify core services are responding:

- Ingestion API health: `curl -s http://localhost:8000/v1/healthz`
- Cache service health: `curl -s http://localhost:8080/healthz`
- Flink UI: http://localhost:8081
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- ClickHouse HTTP ping: `curl -s http://localhost:8123/ping`

Send a sample analytics event to ingestion:

```bash
curl -sS -X POST http://localhost:8000/v1/analytics/track \
	-H 'Content-Type: application/json' \
	-d '{
		"event": {"type": "page_view"},
		"user": {"id": "user-1"},
		"device": {"user_agent": "Mozilla/5.0", "screen_width": 1920, "screen_height": 1080},
		"context": {"url": "https://example.com", "session_id": "sess-1"},
		"metrics": {"load_time": 120, "interaction_time": 400},
		"properties": {}
	}'
```

Once events flow, the Cache readiness endpoint will flip to ready:

```bash
curl -s http://localhost:8080/readyz
```

## Components & ports (local)

- Ingestion API: 8000
- Cache API: 8080
- Flink UI (JobManager): 8081
- ClickHouse HTTP: 8123 (native: 9000)
- Prometheus: 9090, Grafana: 3000
- Kafka: 9092 (external), 29092 (docker-internal), JMX/metrics: 7071/9999
- Storage metrics: 8001 (health served internally at 8081)

## Documentation

Start here: [docs/README.md](./docs/README.md)

Quick links:
- Architecture: [docs/architecture/README.md](./docs/architecture/README.md)
- Setup: [docs/setup/README.md](./docs/setup/README.md)
- API: [docs/api/README.md](./docs/api/README.md)
- Modules: [docs/modules/README.md](./docs/modules/README.md) (incl. Processing, Storage, Cache)
- Testing: [docs/testing/README.md](./docs/testing/README.md)
- Troubleshooting: [docs/troubleshooting/README.md](./docs/troubleshooting/README.md)

Adding new processing jobs: see [docs/modules/processing/adding-jobs.md](./docs/modules/processing/adding-jobs.md).

## Development

Run the test suites:

```bash
./run-tests.sh
```

Code for each service lives under `services/{ingestion,processing,storage,cache}` with shared utilities in `shared/`.

