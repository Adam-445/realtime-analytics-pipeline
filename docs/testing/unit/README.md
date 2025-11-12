# Unit Testing

This document describes the unit test structure and patterns used across all services in the real-time analytics pipeline.

## Overview

Unit tests validate individual components in isolation using mocks and fakes. Each service has its own test suite organized by architectural layer.

## Test Organization

### Structure

```
services/
├── ingestion/
│   └── tests/
│       └── unit/
│           ├── api/
│           │   └── v1/
│           │       └── endpoints/
│           │           ├── test_track.py        # Track endpoint tests
│           │           ├── test_health.py       # Health endpoint tests
│           │           └── test_ready.py        # Readiness endpoint tests
│           ├── infrastructure/
│           │   ├── test_kafka_producer.py       # Kafka producer tests
│           │   └── test_dependencies.py         # Dependency injection tests
│           ├── domain/
│           │   └── test_schemas.py              # Pydantic schema validation tests
│           └── core/
│               ├── test_config.py               # Configuration tests
│               └── test_startup.py              # Application startup tests
│
├── cache/
│   └── tests/
│       └── unit/
│           ├── api/
│           │   └── test_api_endpoints.py        # FastAPI endpoints
│           ├── infrastructure/
│           │   ├── kafka/
│           │   │   ├── test_consumer.py         # Kafka consumer tests
│           │   │   ├── test_worker.py           # Consumer worker loop tests
│           │   │   ├── test_consumer_ready.py   # Ready check tests
│           │   │   └── test_message_parser_and_metrics.py
│           │   └── redis/
│           │       └── test_repository.py       # Redis operations tests
│           ├── domain/
│           │   └── test_domain_models.py        # Domain model tests
│           └── services/
│               └── test_cache_service.py        # Business logic tests
│
├── storage/
│   └── tests/
│       └── unit/
│           ├── infrastructure/
│           │   ├── test_clickhouse_client.py    # ClickHouse client tests
│           │   ├── test_kafka_consumer.py       # Kafka consumer tests
│           │   └── test_topic_waiter.py         # Kafka topic availability tests
│           └── core/
│               └── test_processor.py            # Message processing loop tests
│
└── processing/
    └── tests/
        └── unit/
            ├── jobs/
            │   ├── test_event_aggregator.py     # Event aggregation job tests
            │   ├── test_performance_tracker.py  # Performance tracking job tests
            │   ├── test_base_job.py             # Base job class tests
            │   └── test_job_coordinator.py      # Job orchestration tests
            ├── transformations/
            │   └── test_device_categorizer.py   # Device categorization tests
            └── core/
                ├── test_config.py               # Configuration tests
                └── test_logger.py               # Logging tests
```

### Architectural Layers

Tests are organized by architectural responsibility:

1. **API Layer** (`api/`): HTTP endpoints, request/response handling
2. **Infrastructure Layer** (`infrastructure/`): External system integrations (Kafka, Redis, ClickHouse)
3. **Domain Layer** (`domain/`): Business models, schemas, validation rules
4. **Services Layer** (`services/`): Business logic, orchestration
5. **Core Layer** (`core/`): Configuration, logging, utilities

---

## Running Unit Tests

### Run All Unit Tests

```bash
./run-tests.sh --unit
```

### Run Tests for Specific Service

```bash
./run-tests.sh --unit --service ingestion
./run-tests.sh --unit --service cache
./run-tests.sh --unit --service storage
./run-tests.sh --unit --service processing
```

### Run Specific Test File

```bash
./run-tests.sh --unit --test services/ingestion/tests/unit/api/v1/endpoints/test_track.py
```

### Run Specific Test

```bash
./run-tests.sh --unit --test services/ingestion/tests/unit/api/v1/endpoints/test_track.py::TestTrackEndpoint::test_track_event_success
```

### Run with Verbose Output

```bash
./run-tests.sh --unit -s
```

### Run with Coverage

```bash
./run-tests.sh --unit --cov
```

---

## Test Examples

### API Endpoint Testing (Ingestion Service)

**File**: `services/ingestion/tests/unit/api/v1/endpoints/test_track.py`

```python
class TestTrackEndpoint:
    """Test cases for the /track endpoint."""

    def test_track_event_success(
        self, test_client, mock_kafka_producer, sample_analytics_event
    ):
        """Test successful event tracking."""
        response = test_client.post("/v1/analytics/track", json=sample_analytics_event)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted"}
        mock_kafka_producer.send_event.assert_called_once()

    def test_track_event_missing_required_fields(
        self, test_client, mock_kafka_producer
    ):
        """Test tracking event with missing required fields."""
        incomplete_event = {
            "event": {"type": "page_view"},
            # Missing user, device, context, metrics
        }

        response = test_client.post("/v1/analytics/track", json=incomplete_event)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_kafka_producer.send_event.assert_not_called()
```

**Patterns**:
- Use FastAPI's `TestClient` for endpoint testing
- Mock external dependencies (Kafka producer)
- Provide test fixtures for sample data
- Test both success and error cases
- Verify status codes and response bodies
- Assert mock interactions

---

### Infrastructure Testing (Cache Service - Redis)

**File**: `services/cache/tests/unit/infrastructure/redis/test_repository.py`

```python
@pytest.mark.asyncio
async def test_pipeline_apply_stores_hashes_and_indices():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    repo = CacheRepository(r, window_retention_count=10, window_hash_ttl=60)
    
    ops: list[Operation] = [
        Operation(type="event", window_start=1000, fields={"click.count": 5}),
        Operation(type="perf", window_start=2000, fields={"mobile.avg_load_time": 1.2}),
    ]
    await repo.pipeline_apply(ops)

    event_key = RedisKeys.window_key("event", 1000)
    perf_key = RedisKeys.window_key("performance", 2000)

    ev = await r.hgetall(event_key)
    pf = await r.hgetall(perf_key)
    
    assert ev == {"click.count": "5"}
    assert pf == {"mobile.avg_load_time": "1.2"}
```

**Patterns**:
- Use `fakeredis` for in-memory Redis testing
- Mark async tests with `@pytest.mark.asyncio`
- Test repository operations (CRUD)
- Verify data structures (hashes, sorted sets)
- Test retention/TTL behavior
- Use shared constants from `shared/constants/`

---

### Processing Job Testing (Processing Service - Flink)

**File**: `services/processing/tests/unit/jobs/test_event_aggregator.py`

```python
class TestEventAggregator:
    """Test EventAggregator job functionality."""

    def test_event_aggregator_initialization(self):
        """Test EventAggregator initializes with correct name and sink name."""
        aggregator = EventAggregator()

        assert aggregator.name == "EventAggregator"
        assert aggregator.sink_name == "event_metrics"

    def test_build_pipeline_basic_flow(self):
        """Test build_pipeline basic execution flow."""
        aggregator = EventAggregator()
        mock_t_env = MagicMock()
        mock_events_table = MagicMock()
        mock_t_env.from_path.return_value = mock_events_table

        with patch("src.jobs.event_aggregator.device_categorizer.categorize_device") as mock_categorizer:
            mock_categorized_table = MagicMock()
            mock_categorizer.return_value = mock_categorized_table

            # Set up fluent chain
            mock_select = MagicMock()
            mock_categorized_table.select.return_value = mock_select
            mock_select.filter.return_value.window.return_value.group_by.return_value.select.return_value = MagicMock()

            result = aggregator.build_pipeline(mock_t_env)

            mock_t_env.from_path.assert_called_once_with("events")
            mock_categorizer.assert_called_once_with(mock_events_table)
```

**Patterns**:
- Mock Flink Table API components (`TableEnvironment`, `Table`)
- Test job configuration and initialization
- Verify fluent API call chains
- Patch imported functions/modules
- Test configuration-driven behavior (`settings`)
- Avoid running actual Flink jobs (too heavyweight for unit tests)

---

## Common Testing Patterns

### 1. Fixture-Based Setup

**Define reusable fixtures** in `conftest.py` at appropriate scope:

```python
# services/ingestion/tests/conftest.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def test_client(mock_kafka_producer):
    """FastAPI test client with mocked dependencies."""
    from src.main import app
    from src.dependencies import get_kafka_producer
    
    app.dependency_overrides[get_kafka_producer] = lambda: mock_kafka_producer
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_analytics_event():
    """Sample event payload for testing."""
    return {
        "event": {"type": "page_view"},
        "user": {"id": "test-user-123"},
        "device": {
            "user_agent": "Mozilla/5.0",
            "screen_width": 1920,
            "screen_height": 1080
        },
        "context": {
            "url": "https://example.com/test",
            "session_id": "test-session-456"
        },
        "metrics": {"load_time": 250}
    }
```

---

### 2. Mock External Dependencies

**Kafka Producer** (Ingestion):
```python
@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    producer = MagicMock()
    producer.send_event = MagicMock()
    return producer
```

**Redis Client** (Cache):
```python
@pytest.fixture
def fake_redis():
    """In-memory Redis using fakeredis."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)
```

**ClickHouse Client** (Storage):
```python
@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client."""
    client = MagicMock()
    client.execute = MagicMock(return_value=[])
    return client
```

---

### 3. Parametrized Tests

Test multiple scenarios with same logic:

```python
@pytest.mark.parametrize("event_type", ["page_view", "click", "conversion", "add_to_cart"])
def test_event_type_validation(test_client, mock_kafka_producer, event_type):
    """Test all event types are accepted."""
    event = create_test_event(event_type=event_type)
    response = test_client.post("/v1/analytics/track", json=event)
    assert response.status_code == 202

@pytest.mark.parametrize("user_agent,expected_category", [
    ("Mozilla/5.0 (Windows NT 10.0)", "desktop"),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_7)", "mobile"),
    ("Mozilla/5.0 (iPad; CPU OS 14_7)", "tablet"),
])
def test_device_categorization(user_agent, expected_category):
    """Test device categorization logic."""
    category = categorize_device(user_agent)
    assert category == expected_category
```

---

### 4. Testing Async Code

Use `pytest-asyncio` for async functions:

```python
@pytest.mark.asyncio
async def test_async_operation(fake_redis):
    """Test async Redis operation."""
    await fake_redis.set("key", "value")
    result = await fake_redis.get("key")
    assert result == "value"
```

---

### 5. Exception Testing

```python
def test_kafka_producer_error_handling(test_client, mock_kafka_producer):
    """Test handling of Kafka producer errors."""
    mock_kafka_producer.send_event.side_effect = Exception("Kafka connection failed")

    with pytest.raises(Exception, match="Kafka connection failed"):
        test_client.post("/v1/analytics/track", json=sample_event)
```

---

### 6. Mock Verification

Verify mock interactions:

```python
def test_prometheus_metrics_updated(test_client, mock_prometheus_metrics):
    """Test that Prometheus metrics are updated."""
    response = test_client.post("/v1/analytics/track", json=sample_event)

    # Verify specific mock calls
    mock_prometheus_metrics["requests"].inc.assert_called_once()
    mock_prometheus_metrics["latency"].observe.assert_called_once()
    mock_prometheus_metrics["errors"].inc.assert_not_called()
```

---

## Writing New Unit Tests

### 1. Create Test File

Follow the service's layer structure:

```bash
# For new API endpoint
services/ingestion/tests/unit/api/v1/endpoints/test_new_endpoint.py

# For new infrastructure component
services/cache/tests/unit/infrastructure/redis/test_new_repository.py

# For new business logic
services/processing/tests/unit/jobs/test_new_job.py
```

---

### 2. Basic Test Template

```python
import pytest
from unittest.mock import MagicMock, patch

class TestMyComponent:
    """Test cases for MyComponent."""

    def test_initialization(self):
        """Test component initializes correctly."""
        component = MyComponent(param1="value1")
        
        assert component.param1 == "value1"
        assert component.some_property is not None

    def test_basic_functionality(self, mock_dependency):
        """Test basic operation."""
        component = MyComponent()
        
        result = component.do_something()
        
        assert result == expected_value
        mock_dependency.method.assert_called_once()

    def test_error_handling(self):
        """Test error scenarios."""
        component = MyComponent()
        
        with pytest.raises(ValueError, match="Expected error message"):
            component.do_invalid_operation()

    @pytest.mark.asyncio
    async def test_async_operation(self, async_mock):
        """Test async operation."""
        component = MyComponent()
        
        result = await component.async_method()
        
        assert result is not None
```

---

### 3. Testing FastAPI Endpoints

```python
def test_endpoint_success_case(test_client, mock_dependencies):
    """Test successful request."""
    payload = {"key": "value"}
    
    response = test_client.post("/api/endpoint", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_endpoint_validation_error(test_client):
    """Test request validation."""
    invalid_payload = {"missing": "required_field"}
    
    response = test_client.post("/api/endpoint", json=invalid_payload)
    
    assert response.status_code == 422
    assert "detail" in response.json()
```

---

### 4. Testing Repository/Database Operations

```python
@pytest.mark.asyncio
async def test_repository_create(fake_database):
    """Test creating a record."""
    repo = MyRepository(fake_database)
    
    entity = {"id": "123", "name": "test"}
    result = await repo.create(entity)
    
    assert result["id"] == "123"
    
    # Verify data was stored
    stored = await fake_database.get("123")
    assert stored["name"] == "test"

@pytest.mark.asyncio
async def test_repository_not_found(fake_database):
    """Test handling of missing records."""
    repo = MyRepository(fake_database)
    
    with pytest.raises(NotFoundError):
        await repo.get("nonexistent-id")
```

---

## Test Coverage

### Generate Coverage Reports

```bash
# Run tests with coverage
./run-tests.sh --unit --cov

# View HTML coverage report
coverage-reports/{service}/htmlcov/index.html
```

### Coverage Targets

- **Overall**: Aim for >80% coverage
- **Critical paths**: API endpoints, business logic should have >90%
- **Infrastructure**: Kafka/Redis/ClickHouse clients >70%
- **Configuration**: Config loading and validation >80%

### Exclude from Coverage

Some code is intentionally excluded:
- Main entry points (`if __name__ == "__main__"`)
- Abstract base classes
- Type checking blocks (`if TYPE_CHECKING`)
- Debug-only code

---

## Common Fixtures

### Service-Level Fixtures

Defined in each service's `tests/conftest.py`:

#### Ingestion Service
- `test_client`: FastAPI TestClient
- `mock_kafka_producer`: Mocked Kafka producer
- `mock_prometheus_metrics`: Mocked Prometheus metrics
- `mock_logger`: Mocked logger
- `sample_analytics_event`: Sample event payload

#### Cache Service
- `fake_redis`: In-memory Redis (fakeredis)
- `mock_kafka_consumer`: Mocked Kafka consumer
- `sample_operation`: Sample cache operation

#### Storage Service
- `mock_clickhouse_client`: Mocked ClickHouse client
- `mock_kafka_consumer`: Mocked Kafka consumer
- `sample_metric_message`: Sample metric message

#### Processing Service
- `mock_table_env`: Mocked Flink TableEnvironment
- `mock_settings`: Mocked configuration settings

---

## Debugging Unit Tests

### 1. Run Single Test with Output

```bash
./run-tests.sh --unit --test path/to/test_file.py::test_function -s
```

### 2. Use pytest Debugging

```python
def test_with_breakpoint():
    import pdb; pdb.set_trace()
    # Test code here
```

Run with:
```bash
pytest -s path/to/test_file.py::test_with_breakpoint
```

### 3. Print Mock Call History

```python
def test_mock_debugging(mock_kafka_producer):
    # ... test code ...
    
    # Print all calls to mock
    print(mock_kafka_producer.send_event.call_args_list)
    
    # Print call count
    print(f"Called {mock_kafka_producer.send_event.call_count} times")
```

### 4. Check Test Discovery

```bash
# List all tests pytest will run
pytest --collect-only services/ingestion/tests/unit/
```

---

## Best Practices

### Do

- **Test one thing per test**: Each test should verify a single behavior
- **Use descriptive names**: `test_track_endpoint_rejects_invalid_url` not `test_error`
- **Arrange-Act-Assert**: Clear structure (setup, execute, verify)
- **Mock external dependencies**: Don't hit real Kafka/Redis/ClickHouse in unit tests
- **Use fixtures**: Reuse setup code with pytest fixtures
- **Test error cases**: Test both success and failure paths
- **Keep tests fast**: Unit tests should run in milliseconds

### Don't

- **Test implementation details**: Test behavior, not internal structure
- **Create brittle tests**: Don't assert on irrelevant details
- **Use real external services**: Use mocks/fakes for unit tests
- **Write flaky tests**: Tests should be deterministic
- **Ignore test failures**: Fix or skip failing tests, don't leave broken
- **Copy-paste test code**: Extract to fixtures/helpers

---

## Integration with E2E Tests

Unit tests focus on **isolated components**, E2E tests validate **complete flows**:

| Aspect | Unit Tests | E2E Tests |
|--------|-----------|-----------|
| Scope | Single component | Full pipeline |
| Dependencies | Mocked | Real services |
| Speed | Fast (milliseconds) | Slow (minutes) |
| Coverage | Individual functions | User workflows |
| Feedback | Immediate | Delayed |
| Debugging | Easy | Complex |

**Strategy**: Write many unit tests, fewer E2E tests. Use unit tests for fast feedback during development, E2E tests to validate integration.

---

## CI/CD Integration

Unit tests run on every commit:

```bash
# In CI pipeline
./run-tests.sh --unit --cov

# Check coverage threshold
if [ $COVERAGE -lt 80 ]; then
    echo "Coverage below 80%"
    exit 1
fi
```

See `docs/testing/README.md` for complete CI/CD documentation.

---

## Shared Test Utilities

Some utilities are shared across services in `shared/`:

### Shared Constants

```python
from shared.constants import RedisKeys, Topics

# Use in tests
event_key = RedisKeys.window_key("event", window_start)
topic_name = Topics.ANALYTICS_EVENTS
```

### Shared Config

```python
from shared.config import get_config

# Test config loading
config = get_config("test")
assert config.kafka_bootstrap_servers == "kafka:9092"
```

---

## Resources

- **pytest documentation**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **fakeredis**: https://github.com/cunla/fakeredis-py
- **unittest.mock**: https://docs.python.org/3/library/unittest.mock.html
- **FastAPI testing**: https://fastapi.tiangolo.com/tutorial/testing/

---

For complete testing documentation, see:
- [Testing Overview](./README.md)
- [E2E Testing](./e2e.md)
- [Performance Testing](./performance/README.md)
