# Testing Endpoints

This guide shows how to verify the running services locally using simple HTTP requests. Host port mappings are defined in `infrastructure/compose/docker-compose.yml`.

- Ingestion (FastAPI): http://localhost:8000
- Cache (FastAPI): http://localhost:8080
- Storage health: internal on 8081 (not mapped to host; see below for container exec)
- Metrics:
  - Ingestion `/metrics`
  - Cache `/metrics`
  - Storage Prometheus on `metrics_port` (default 8001)

## Prerequisites

- The stack is running via Docker Compose (see `docs/setup/README.md`).

## Ingestion

- Health

```bash
curl -s http://localhost:8000/v1/healthz
```

- Metrics (Prometheus format)

```bash
curl -s http://localhost:8000/metrics | head -n 10
```

- Track Event (minimal body)

```bash
curl -s -X POST http://localhost:8000/v1/analytics/track \
  -H 'Content-Type: application/json' \
  -d '{
    "event": { "type": "page_view" },
    "user": { "id": "user-123" },
    "device": { "user_agent": "Mozilla/5.0", "screen_width": 1920, "screen_height": 1080 },
    "context": { "url": "https://example.com", "session_id": "sess-abc" },
    "metrics": { "load_time": 250 }
  }'
```

Expected: HTTP 202 and `{ "status": "accepted" }`.

## Cache

- Health

```bash
curl -s http://localhost:8080/healthz
```

- Readiness

```bash
curl -s -i http://localhost:8080/readyz
```

- Metrics: overview

```bash
curl -s http://localhost:8080/metrics/overview
```

- Metrics: latest event snapshot

```bash
curl -s http://localhost:8080/metrics/event/latest
```

- Metrics: event windows (limit 5)

```bash
curl -s "http://localhost:8080/metrics/event/windows?limit=5"
```

- Metrics: performance windows (limit 5)

```bash
curl -s "http://localhost:8080/metrics/performance/windows?limit=5"
```

## Storage

- Health (internal port 8081, not mapped to host). Exec into the container or run curl inside it:

```bash
# Exec into the running storage container
docker compose -f infrastructure/compose/docker-compose.yml exec storage \
  curl -s http://localhost:8081/healthz
```

- Metrics: Prometheus client on port 8001 (mapped to host)

```bash
curl -s http://localhost:8001 | head -n 10
```

## Optional: Monitoring UIs

- Prometheus: http://localhost:9090/targets
- Grafana: http://localhost:3000
- Flink JobManager UI: http://localhost:8081

## Troubleshooting

- If a request fails, inspect container logs:

```bash
docker compose -f infrastructure/compose/docker-compose.yml logs -f ingestion
```

Replace `ingestion` with `cache` or `storage` as needed. See also `docs/troubleshooting/README.md`.
