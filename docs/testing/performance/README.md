# Performance Testing

This section documents performance scenarios and how to execute them via the provided test runner and test suite.

- Suite location (drivers and helpers): `tests/performance`
- Primary scenario: `tests/performance/test_throughput.py`
- Supporting modules under `tests/performance/core/` and `tests/performance/scenarios/`

## Running Performance Tests

Use the orchestrated runner from the project root:

- Default throughput scenario:
  - `./run-tests.sh performance`
- Override rates and duration:
  - `./run-tests.sh --perf-rates=200,500 --perf-duration=45 performance`
- Additional options: `--perf-warmup`, `--perf-strict`, `--env=KEY=VALUE`

## Metrics and Validation

- Endpoints under test: Ingestion (default http://ingestion:8000) and Cache (http://cache:8080)
- Prometheus scraping validates service-level metrics when configured via `PROMETHEUS_URL`
- Error rate constraints controlled via `--perf-strict` and `--perf-max-error-rate`

## Reporting

- Console reporters under `tests/performance/reporting/`
- Git metadata (commit/branch) is passed through for provenance in logs

## Notes

- The test runner composes and builds all required containers for a consistent environment.
- Tune rates and duration to match your workstation capabilities.
