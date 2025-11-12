# Testing

Comprehensive testing documentation for the real-time analytics pipeline, covering unit tests, end-to-end tests, and performance tests.

## Quick Links

- **[Unit Testing Guide](./unit.md)** - Service-level component testing with mocks and fakes
- **[E2E Testing Guide](./e2e.md)** - Full pipeline validation and integration testing
- **[Performance Testing Guide](./performance/README.md)** - Load testing and performance benchmarking
- **[Endpoint Testing](./endpoints.md)** - Manual endpoint verification

## Test Structure

- **Test runner script**: `run-tests.sh` (repository root)
- **Unit tests**: `services/*/tests/unit/` (per-service, organized by architectural layer)
- **E2E tests**: `tests/e2e/` (full pipeline validation)
- **Performance tests**: `tests/performance/` (load testing scenarios)
- **Test utilities**: `tests/utils/` (shared helpers for ClickHouse polling, event creation)

## Running Tests

The `run-tests.sh` script provides a unified interface for running all test types. All tests run in Docker containers with appropriate service dependencies.

### Unit Tests

Run unit tests for service components in isolation:

```bash
# All unit tests across all services
./run-tests.sh --unit

# Specific service only
./run-tests.sh --unit --service ingestion
./run-tests.sh --unit --service cache
./run-tests.sh --unit --service storage
./run-tests.sh --unit --service processing

# Specific test file or function
./run-tests.sh --unit --test services/ingestion/tests/unit/api/v1/endpoints/test_track.py
./run-tests.sh --unit --test services/cache/tests/unit/infrastructure/redis/test_repository.py::test_pipeline_apply_stores_hashes_and_indices

# With verbose output (-s flag passes through to pytest)
./run-tests.sh --unit -s

# With coverage report
./run-tests.sh --unit --cov
```

**Coverage reports**: Generated in `coverage-reports/{service}/htmlcov/index.html`

See **[Unit Testing Guide](./unit.md)** for detailed patterns and examples.

---

### End-to-End Tests

Run E2E tests that validate the full pipeline:

```bash
# All E2E tests
./run-tests.sh --e2e

# Specific E2E test
./run-tests.sh --e2e --test tests/e2e/test_full_pipeline.py::test_happy_path_page_view_event_is_processed

# With verbose output
./run-tests.sh --e2e -s
```

**Note**: E2E tests take ~2-5 minutes per test due to windowed aggregation processing (60-second windows).

See **[E2E Testing Guide](./e2e.md)** for test scenarios and utilities.

---

### Performance Tests

Run load testing scenarios:

```bash
# All performance tests with default rates
./run-tests.sh --performance

# Custom load rates (comma-separated)
./run-tests.sh --performance --perf-rates "100,250,500"

# With strict failure on degradation
./run-tests.sh --performance --perf-strict

# Save detailed performance metrics
./run-tests.sh --performance --env PERF_SAVE_DETAILS=true
```

See **[Performance Testing Guide](./performance/README.md)** for scenario details and baseline results.

---

### Run All Tests

```bash
# Everything (unit + e2e + performance)
./run-tests.sh --unit --e2e --performance

# Everything except performance (faster)
./run-tests.sh --unit --e2e
```

---

### Test Runner Options

Common flags for `run-tests.sh`:

- `--unit` - Run unit tests
- `--e2e` - Run end-to-end tests  
- `--performance` - Run performance tests
- `--service SERVICE` - Target specific service (unit tests only)
- `--test PATH` - Run specific test file or function
- `-s` / `--show-output` - Show test output (pytest `-s` flag)
- `--cov` - Generate coverage report
- `--env KEY=VALUE` - Pass environment variables to tests
- `--perf-rates "200,500"` - Custom performance test rates (comma-separated)
- `--perf-strict` - Fail on performance degradation
- `-h` / `--help` - Show complete usage




## Test Environment

### Docker Compose Setup

Tests run in Docker containers with full service dependencies:

- **Base**: `infrastructure/compose/docker-compose.yml`
- **Test overlay**: `infrastructure/compose/docker-compose.test.yml`
- **Environment**: `.env.test`

The test runner automatically:
1. Builds test images using multi-stage `test` stage when available
2. Starts required services (Kafka, Redis, ClickHouse, etc.)
3. Waits for services to be ready
4. Runs tests in containers
5. Collects results and coverage reports

### Service Dependencies

Different test types require different services:

- **Unit tests**: No external dependencies (uses mocks/fakes)
- **E2E tests**: All services (ingestion, cache, processing, storage, Kafka, ClickHouse, Redis)
- **Performance tests**: Ingestion + Kafka (+ optional monitoring)

### Environment Variables

Tests use environment-specific configuration:

- `.env.test` - Test environment variables
- `--env KEY=VALUE` - Override specific variables for test runs

Common test environment variables:
- `APP_ENVIRONMENT=test`
- `LOG_LEVEL=WARNING` (reduces noise in test output)
- `KAFKA_BOOTSTRAP_SERVERS=kafka:9092`
- `REDIS_HOST=redis`
- `CLICKHOUSE_HOST=clickhouse`

---

## Test Coverage

### Current Coverage Status

Per-service coverage reports are generated in `coverage-reports/{service}/`:

- **Ingestion**: `coverage-reports/ingestion/htmlcov/index.html`
- **Cache**: `coverage-reports/cache/htmlcov/index.html`
- **Storage**: `coverage-reports/storage/htmlcov/index.html`
- **Processing**: `coverage-reports/processing/htmlcov/index.html`

### Coverage Targets

- **Overall**: >80% coverage
- **Critical paths**: API endpoints, business logic >90%
- **Infrastructure**: Kafka/Redis/ClickHouse clients >70%

### Generate Coverage Reports

```bash
# Unit test coverage
./run-tests.sh --unit --cov

# Service-specific coverage
./run-tests.sh --unit --service ingestion --cov

# View HTML report
open coverage-reports/ingestion/htmlcov/index.html
```

---

## Writing Tests

### Unit Tests

See **[Unit Testing Guide](./unit.md)** for:
- Test organization by architectural layer
- Common testing patterns (fixtures, mocks, parametrization)
- FastAPI endpoint testing
- Infrastructure testing (Redis, Kafka, ClickHouse)
- Flink job testing
- Best practices and examples

### E2E Tests

See **[E2E Testing Guide](./e2e.md)** for:
- Full pipeline validation patterns
- Test utilities (event creation, ClickHouse polling)
- Writing new E2E scenarios
- Debugging E2E test failures
- ClickHouse table schemas

### Performance Tests

See **[Performance Testing Guide](./performance/README.md)** for:
- Load testing scenarios
- Custom throughput tests
- Performance baseline results
- Interpreting performance metrics

---

## Manual Testing

For quick manual verification of service endpoints without the full test suite:

See **[Endpoint Testing Guide](./endpoints.md)** for curl commands to test each service manually.

---

## Continuous Integration

### CI Pipeline

Tests run on every commit:

```yaml
# Example CI workflow
- run: ./run-tests.sh --unit --cov
- run: ./run-tests.sh --e2e
- run: ./run-tests.sh --performance  # Optional: nightly builds only
```

### Fast Feedback Loop

For rapid development iteration:

```bash
# Quick unit tests (fastest)
./run-tests.sh --unit --service ingestion

# Unit + E2E (comprehensive, ~5-10 min)
./run-tests.sh --unit --e2e

# Skip performance tests in PR checks (saves time)
```

### Test Failure Debugging

1. **Check test output**: Run with `-s` flag for verbose output
2. **Check service logs**: `docker compose logs -f SERVICE_NAME`
3. **Inspect test containers**: `docker compose ps`, `docker compose exec SERVICE bash`
4. **Verify environment**: Check `.env.test` and environment variables
5. **Run specific failing test**: Use `--test` flag to isolate issue

---

