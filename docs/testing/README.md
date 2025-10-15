# Testing

How to run and verify unit, integration, end-to-end, and performance tests.

- Test runner script: `run-tests.sh`
- Test suites: per-service unit tests under `services/*/tests/unit`, repository-level e2e and performance tests under `tests/`

## Running Tests

Common usages with the test runner:

- Unit tests (all services):
  - `./run-tests.sh unit`
- Unit tests (specific service):
  - `./run-tests.sh --service=processing unit`
- End-to-end tests:
  - `./run-tests.sh e2e`
- Performance tests:
  - `./run-tests.sh performance`

Coverage reports can be enabled with `--coverage` and are written to `./coverage-reports/[service]/`.

## Environments

The test composition overlays `infrastructure/compose/docker-compose.yml` with `docker-compose.test.yml` and `.env.test`. The script builds dedicated test images with the `test` stage when available.

## E2E Semantics

The e2e tests in `tests/e2e/test_full_pipeline.py` validate:
- A page_view event traverses ingestion → Kafka → processing → storage, and yields session metrics in ClickHouse.
- Aggregation counts per event type within a window.
- Performance metrics window calculations (avg, p95).

## Performance Tests

The suite under `tests/performance` drives load against ingestion and verifies metrics and error rates. See `tests/performance/README.md` for scenario details.
