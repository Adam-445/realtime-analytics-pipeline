# Troubleshooting

Common issues and diagnostic steps when running the pipeline locally.

## Kafka Not Ready

- Symptom: ingestion or processing fails on startup.
- Check: `docker compose logs kafka1` and health of Zookeeper.
- Ensure advertised listeners in compose match your host IP if accessing from host.

## Flink Jobs Not Visible

- Check JobManager UI at http://localhost:8081.
- Verify that the `processing` container can reach JobManager (`jobmanager:8081`).

## ClickHouse Empty Results

- The e2e tests poll for data; ensure sufficient wait for window end (see test configs).
- Inspect storage logs for consumer lag or DDL errors.

## Cache Not Ready

- `/readyz` returns 503 until the Kafka consumer starts and signals readiness.
- Confirm Redis connectivity via `/healthz`.

## Metrics Not Scraped

- Verify Prometheus targets at http://localhost:9090/targets.
- Check that `/metrics` endpoints respond and Flink reporter is enabled.

## General Diagnostics

- Use `docker compose ps` and `docker compose logs -f [service]`.
- Confirm network `analytics_net` exists and containers share it.
- Inspect environment variables and volumes in the compose files.
