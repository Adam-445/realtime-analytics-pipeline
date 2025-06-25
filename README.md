# Real-Time Analytics Pipeline [![Project Status: Active](https://img.shields.io/badge/status-active-success.svg)]()

A scalable, real-time analytics pipeline for processing and visualizing event streams. Built with an event-driven architecture using modern tools like Kafka, Flink, Redis, and FastAPI, this system demonstrates low-latency stream processing and end-to-end data flow suitable for high-throughput environments.

> **Note**: This project builds upon the foundational work done in the [lab repository](https://github.com/Adam-445/analytics-pipeline-lab) and extends it into a production-grade system.

## Adding New Jobs to the Pipeline
To add a new processing job to the pipeline:

1. Create a new job class in `src/jobs/`
2. Define output schema in `src/core/schemas/`
3. Register Kafka sink in `src/connectors/kafka_sink.py`
4. Update configuration in `src/core/config.py`
5. Register job in `src/main.py`
6. Create Kafka topic in ingestion service

See [Job Implementation Guide](docs/adding_jobs.md) for details