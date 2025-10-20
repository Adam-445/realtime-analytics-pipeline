# API

Public HTTP APIs exposed by services. This section summarizes endpoints, request/response formats, and links to setup pages.

- Ingestion API (FastAPI): accepts analytics events and exposes health/metrics
  - Base path: `/v1`
  - Endpoints: `/v1/analytics/track`, `/v1/healthz`, `/metrics`
- Cache API (FastAPI): exposes health/readiness and metrics views from Redis
  - Endpoints: `/healthz`, `/readyz`, `/metrics/*`, Prometheus metrics at `/metrics`

See also: [Setup → Ingestion](../setup/services/ingestion.md), [Setup → Cache](../setup/services/cache.md), [Testing Endpoints](../testing/endpoints.md)

For the event request model, see `services/ingestion/src/schemas/analytics_event.py`.

## Ingestion

### POST /v1/analytics/track

Accepts `AnalyticsEvent` and publishes to Kafka.

- Request body: `AnalyticsEvent`
- Success: 202 Accepted `{ "status": "accepted" }`
- Errors: 500 if Kafka publish fails (see service logs for error type)

Minimal example body (fields truncated for brevity; see schema for full spec):

```json
{
  "event": { "type": "page_view" },
  "user": { "id": "user-123" },
  "device": { "user_agent": "Mozilla/5.0", "screen_width": 1920, "screen_height": 1080 },
  "context": { "url": "https://example.com", "session_id": "sess-abc" },
  "metrics": { "load_time": 250 }
}
```

### GET /v1/healthz

Returns `{ "status": "ok" }` when the ingestion service is healthy.

### GET /metrics

Prometheus metrics endpoint (multiprocess collector).

## Cache

### GET /healthz

Checks Redis connectivity; returns `{ "status": "ok", "redis": true }` when healthy.

### GET /readyz

Readiness probe; returns 200 when the Kafka consumer has started and signaled readiness, otherwise 503.

### GET /metrics/overview

Returns a summarized view computed by the cache service.

### GET /metrics/event/latest

Returns the latest event metrics snapshot.

### GET /metrics/event/windows?limit=20

Returns a list of recent event metric windows (default `limit=20`).

### GET /metrics/performance/windows?limit=20

### GET /metrics

Prometheus metrics endpoint for the cache service.

Returns a list of recent performance windows (default `limit=20`).

## Notes

- All endpoints are served inside Docker per the compose configuration; host ports are mapped via `infrastructure/compose/docker-compose.yml`.
- Status and error semantics are intentionally minimal; rely on service logs for detailed error diagnostics.