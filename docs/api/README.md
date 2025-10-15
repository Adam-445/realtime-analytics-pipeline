# API

Public HTTP APIs exposed by services. This section summarizes endpoints and links to per-service details.

- Ingestion API (FastAPI): accepts analytics events
  - Base path: `/v1`
  - Endpoints: `/v1/analytics/track`, `/v1/healthz`
- Cache API (FastAPI): health and readiness, internal metrics
  - Endpoints: `/healthz`, `/readyz`

For request schema of analytics events, see `services/ingestion/src/schemas/analytics_event.py`.

## Ingestion: Track Event

- Method: POST `/v1/analytics/track`
- Body: `AnalyticsEvent` (see schema)
- Response: `202 Accepted` with `{ "status": "accepted" }` on success

## Health Endpoints

- Ingestion: GET `/v1/healthz`
- Cache: GET `/healthz`, GET `/readyz`

Note: Detailed error semantics and additional endpoints can be documented as they evolve.
