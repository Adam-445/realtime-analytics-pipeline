# Monitoring

Prometheus and Grafana support metrics scraping and dashboards. Flink exposes Prometheus metrics as well.

- Prometheus: `prom/prometheus:v3.5.0` configured by `infrastructure/monitoring/prometheus/prometheus.yml`
- Grafana: `grafana/grafana:12.0.2`
- Flink metrics: reporter at port 9249; JobManager UI at 8081

## Access

- Prometheus UI: http://localhost:9090
- Grafana UI: http://localhost:3000 (default credentials per image docs)

## Scrape Targets

- Kafka JMX exporter (7071)
- Flink JobManager/TaskManagers (9249)
- Ingestion and Cache `/metrics` endpoints
- Storage Prometheus client (port from settings)
