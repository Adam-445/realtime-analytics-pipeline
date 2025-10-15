# Modules

This section maps the repository structure to functional modules and describes core responsibilities and extension points.

## Services

- Ingestion (`services/ingestion`): HTTP ingestion and Kafka producer
- Processing (`services/processing`): Flink jobs and transformations — see [Processing Internals](./processing/README.md)
- Storage (`services/storage`): Kafka consumers and ClickHouse persistence — see [Storage Internals](./storage/README.md)
- Cache (`services/cache`): Kafka consumer, Redis repository, and FastAPI endpoints — see [Cache Internals](./cache/README.md)

## Shared

- `shared/constants`: Kafka topics, environment enums, Redis keys
- `shared/logging`: JSON logging configuration
- `shared/utils`: utility helpers (e.g., retry)

## Key Extension Points

- Processing Jobs: add new jobs under `services/processing/src/jobs/` and register them in `src/main.py`. See [Adding Jobs](./processing/adding-jobs.md).
- Connectors/Sinks: schemas and connectors under `services/processing/src/connectors`.
- Storage DDL: update ClickHouse tables in `services/storage/src/infrastructure/clickhouse/ddl.py` when adding new outputs.

## Cross-References

- [Architecture](../architecture/README.md)
- [Setup](../setup/README.md)
- [API](../api/README.md)
