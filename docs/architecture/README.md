# Architecture

This document provides a high-level overview of the real-time analytics pipeline, its core components, data flow, and key topics. It is the entry point for understanding how data moves through the system and which services are responsible for each stage.

- See also: [Setup](../setup/README.md), [Modules](../modules/README.md), [API](../api/README.md), [Adding Jobs](../modules/processing/adding-jobs.md)

## System Overview

Components deployed via `infrastructure/compose/docker-compose.yml`:

- Ingestion Service (FastAPI) — receives analytics events over HTTP and publishes to Kafka
- Kafka + Zookeeper — durable event transport and pub/sub backbone
- Processing (Flink) — streaming jobs that aggregate and transform events
- Storage Service — consumes processed metrics and persists to ClickHouse
- Cache Service (FastAPI) — consumes metrics and maintains windowed state in Redis for low-latency access
- ClickHouse — analytical database for persisted metrics
- Redis — in-memory store backing the cache service
- Monitoring — Prometheus (scrape), Grafana (dashboards), Flink UI

## Data Flow

```mermaid
flowchart LR
  subgraph Client Side
    U[Client]
  end

  subgraph Ingestion
    I[FastAPI /v1/analytics/track]
  end

  subgraph Kafka
    K1[(analytics_events)]
    K2[(event_metrics)]
    K3[(session_metrics)]
    K4[(performance_metrics)]
  end

  subgraph Processing
    P[Flink jobs\nEventAggregator | SessionTracker | PerformanceTracker]
  end

  subgraph Storage
    S[Consumer → ClickHouse\nTables: event_metrics, session_metrics, performance_metrics]
    CH[(ClickHouse)]
  end

  subgraph Cache
    C[Consumer → Redis\nWindows & overview]
    R[(Redis)]
  end

  U --> I
  I -->|publish| K1
  K1 --> P
  P -->|produce| K2
  P -->|produce| K3
  P -->|produce| K4
  K2 --> S
  K3 --> S
  K4 --> S
  S --> CH
  K2 --> C
  K4 --> C
  C --> R
```

Kafka topic names are centralized in `shared/constants/topics.py`:

- analytics_events
- event_metrics
- session_metrics
- performance_metrics

## Processing Model

- Event time vs processing time: Jobs can switch between event time and processing time based on environment (see `services/processing/src/jobs/*` and `services/processing/src/core/config.py`).
- Windowing: Tumble windows are used for aggregations (e.g., metrics and performance windows). Window sizes are configured via environment variables and surfaced in service configuration.
- Extensibility: New jobs follow a consistent pattern using a `BaseJob` and are registered in `services/processing/src/main.py` via the `JobCoordinator`.
  - Refer to [Adding Jobs](../modules/processing/adding-jobs.md) for a step-by-step guide.

## Observability and Health

- Metrics endpoints
  - Ingestion: `/metrics`
  - Cache: `/metrics`
  - Processing: Prometheus Reporter (Flink) on 9249 (scraped by Prometheus)
  - Storage: Prometheus client started on port 8001 by default
- Health endpoints
  - Ingestion: `/v1/healthz`
  - Cache: `/healthz` and `/readyz`
  - Storage: `/healthz` (internal port, exposed via compose)

## Ports and Dashboards

- Flink JobManager UI: 8081
- Prometheus: 9090
- Grafana: 3000
- Kafka JMX Exporter: 7071 (for Prometheus)
- Kafka external: 9092 (mapped to host)

Refer to the compose files for the authoritative list of ports and environment variables.

## Failure Domains and Recovery

- Kafka is the durable transport and primary recovery boundary.
- Processing jobs are idempotent over windows and can be restarted without data loss (subject to connector semantics and job configuration).
- Storage and Cache consumers resume from Kafka offsets; health checks guard readiness and liveness.

## Next

- Review [Modules](../modules/README.md) for service-level details.
- Use [Setup](../setup/README.md) to start the full stack locally.
