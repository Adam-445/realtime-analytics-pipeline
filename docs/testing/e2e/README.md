# End-to-End Testing

This document describes the E2E test suite that validates the complete real-time analytics pipeline from event ingestion through storage.

## Overview

E2E tests validate the full data flow through all services:

```
Ingestion API → Kafka → Processing (Flink) → Storage → ClickHouse
                   ↓
                 Cache
```

Each test sends events via the ingestion API, waits for processing through windowed aggregations, then queries ClickHouse to verify correct storage and calculation of metrics.

## Test Location

- **Main test file**: `tests/e2e/test_full_pipeline.py`
- **Test utilities**: `tests/utils/`
  - `ingestion/events.py` - Event creation and sending
  - `clickhouse/poll.py` - ClickHouse data polling
  - `clickhouse/debug.py` - Debug helpers

## Running E2E Tests

```bash
# Run all E2E tests
./run-tests.sh --e2e

# Run specific E2E test
./run-tests.sh --e2e --test tests/e2e/test_full_pipeline.py::test_happy_path_page_view_event_is_processed

# Run with verbose output
./run-tests.sh --e2e -s
```

## Test Scenarios

### 1. Happy Path - Basic Pipeline Validation

**Test**: `test_happy_path_page_view_event_is_processed`

Validates a single `page_view` event traverses the entire pipeline correctly.

**Flow**:
1. Send a `page_view` event via ingestion API
2. Wait for processing window to complete (60s + buffer)
3. Query `session_metrics` table in ClickHouse
4. Verify event was processed and metrics calculated correctly

**Validates**:
- Event ingestion accepts payload
- Kafka message routing works
- Flink processing window aggregation
- ClickHouse storage of metrics
- Session tracking and event counting

---

### 2. Event Aggregation

**Test**: `test_event_aggregator_counts_multiple_events`

Validates that multiple events of different types are correctly counted and categorized.

**Parametrized**: Tests both `desktop` and `mobile` device categories

**Flow**:
1. Send 3 events with same session but different types (`page_view`, `click`, `conversion`)
2. Wait for processing window
3. Query `event_metrics` table
4. Verify all event types are counted correctly by device category

**Validates**:
- Multi-event aggregation in same window
- Event type differentiation (`page_view`, `click`, `conversion`, `add_to_cart`)
- Device categorization (desktop vs mobile)
- Count accuracy across event types

---

### 3. Performance Metrics Calculation

**Test**: `test_performance_tracker_calculates_metrics`

Validates performance metric calculations (averages and percentiles).

**Flow**:
1. Send 5 events with controlled `load_time` values: `[100, 200, 300, 400, 500]`
2. Wait for processing window
3. Query `performance_metrics` table
4. Verify calculated metrics match expected values:
   - `avg_load_time = 300ms`
   - `p95_load_time = 480ms` (5th event at 95th percentile)
   - `event_count = 5`

**Validates**:
- Average calculation across events
- 95th percentile (p95) calculation
- Performance metric aggregation
- Numerical precision in ClickHouse

---

### 4. Multiple Event Types

**Test**: `test_different_event_types_are_processed`

Validates that all supported event types are processed correctly.

**Parametrized**: Tests all 4 event types
- `page_view`
- `click`
- `conversion`
- `add_to_cart`

**Flow**:
1. Send single event of specified type
2. Wait for processing window
3. Query appropriate ClickHouse table
4. Verify event was stored with correct type

**Validates**:
- Event type filtering in Flink jobs
- Proper routing per event type
- Schema validation for each type
- Storage consistency

---

## Test Utilities

### Event Creation and Sending

Located in `tests/utils/ingestion/events.py`:

#### `create_test_event()`
Creates a test event payload matching the ingestion API schema.

```python
from tests.utils.ingestion.events import create_test_event

event = create_test_event(
    event_type="page_view",
    user_id="test-user-123",
    session_id="test-session-456",
    load_time=250,  # ms
    url="https://example.com/products",
    referrer="https://google.com/search"
)
```

**Parameters**:
- `event_type`: `page_view`, `click`, `conversion`, `add_to_cart`
- `user_id`: User identifier (generates UUID if not provided)
- `session_id`: Session identifier (generates UUID if not provided)
- `load_time`: Page load time in milliseconds
- `user_agent`: Browser user agent string
- `url`: Page URL
- `referrer`: Referrer URL
- `timestamp_override`: Override event timestamp (milliseconds since epoch)

**Returns**: Dictionary with complete event payload

---

#### `send_event()`
Sends an event to the ingestion API.

```python
from tests.utils.ingestion.events import send_event, create_test_event

# Send custom event
event = create_test_event(event_type="click")
timestamp = send_event(event, ingestion_url="http://ingestion:8000")

# Send default event
timestamp = send_event()
```

**Parameters**:
- `event_payload`: Event payload (creates default if None)
- `timestamp_override`: Override event timestamp
- `ingestion_url`: Ingestion service URL (default: `http://ingestion:8000`)

**Returns**: Timestamp when event was sent

**Raises**: `requests.RequestException` if API call fails

---

#### `send_multiple_events()`
Sends multiple events with controlled timing.

```python
from tests.utils.ingestion.events import send_multiple_events

# Send 10 page views, 1 second apart
events = send_multiple_events(
    count=10,
    event_type="page_view",
    base_user_id="bulk-test-user",
    base_session_id="bulk-test-session",
    interval_ms=1000
)
```

**Returns**: List of event metadata including user_id, session_id, timestamps

---

### ClickHouse Data Polling

Located in `tests/utils/clickhouse/poll.py`:

#### `poll_for_data()`
Polls ClickHouse until expected data appears or timeout.

```python
from tests.utils.clickhouse.poll import poll_for_data

result = poll_for_data(
    clickhouse_client=client,
    query="SELECT * FROM session_metrics WHERE session_id = %(session_id)s",
    params={"session_id": "test-session-123"},
    max_wait_time=30.0,   # seconds
    poll_interval=2.0,    # seconds
    expected_count=1,     # minimum rows expected
    verbose=False         # set True for debugging
)
```

**Why polling?**  
Processing involves windowed aggregations (60-second windows) with additional buffer time. Data appears asynchronously, so polling handles the eventual consistency.

**Parameters**:
- `clickhouse_client`: ClickHouse client instance
- `query`: SQL query to execute
- `params`: Query parameters (dict)
- `max_wait_time`: Maximum wait time in seconds (default: 20.0)
- `poll_interval`: Time between polls in seconds (default: 2.0)
- `expected_count`: Minimum rows expected (default: 1)
- `verbose`: Enable debug output (default: False)

**Returns**: Query result (list of tuples)

**Raises**: `TimeoutError` if data doesn't appear within `max_wait_time`

---

## Writing New E2E Tests

### 1. Basic Test Structure

```python
import pytest
from tests.utils.ingestion.events import send_event, create_test_event
from tests.utils.clickhouse.poll import poll_for_data

@pytest.mark.asyncio
async def test_my_new_scenario(clickhouse_client):
    # 1. Create and send event(s)
    event = create_test_event(
        event_type="click",
        user_id="test-user-new",
        session_id="test-session-new"
    )
    send_event(event)
    
    # 2. Wait for processing (60s window + buffer)
    await asyncio.sleep(75)
    
    # 3. Poll ClickHouse for results
    result = poll_for_data(
        clickhouse_client,
        query="SELECT * FROM event_metrics WHERE session_id = %(session_id)s",
        params={"session_id": "test-session-new"},
        max_wait_time=30.0
    )
    
    # 4. Assert expected results
    assert len(result) > 0
    assert result[0][1] == "click"  # event_type column
```

---

### 2. Testing Aggregations

```python
@pytest.mark.asyncio
async def test_aggregation_scenario(clickhouse_client):
    session_id = f"test-agg-{uuid.uuid4()}"
    
    # Send multiple events for same session
    for i in range(5):
        event = create_test_event(
            event_type="page_view",
            session_id=session_id,
            load_time=100 * (i + 1)  # 100, 200, 300, 400, 500
        )
        send_event(event)
    
    await asyncio.sleep(75)
    
    # Query aggregated metrics
    result = poll_for_data(
        clickhouse_client,
        query="""
            SELECT event_count, avg_load_time
            FROM performance_metrics
            WHERE session_id = %(session_id)s
        """,
        params={"session_id": session_id}
    )
    
    event_count, avg_load_time = result[0]
    assert event_count == 5
    assert avg_load_time == 300  # Average of 100, 200, 300, 400, 500
```

---

### 3. Parametrized Tests

```python
@pytest.mark.parametrize("event_type", ["page_view", "click", "conversion", "add_to_cart"])
@pytest.mark.asyncio
async def test_event_type_processing(clickhouse_client, event_type):
    event = create_test_event(event_type=event_type)
    send_event(event)
    
    await asyncio.sleep(75)
    
    result = poll_for_data(
        clickhouse_client,
        query="SELECT event_type FROM event_metrics WHERE session_id = %(session_id)s",
        params={"session_id": event["context"]["session_id"]}
    )
    
    assert result[0][0] == event_type
```

---

## Common Patterns

### Wait Times

E2E tests require waiting for windowed processing:

- **Processing window**: 60 seconds (tumbling window)
- **Buffer time**: ~15 seconds (for window completion + write latency)
- **Total wait**: ~75 seconds after sending events

```python
await asyncio.sleep(75)  # Standard wait after sending events
```

### ClickHouse Queries

Always use parameterized queries to avoid SQL injection:

```python
# Parameterized
result = poll_for_data(
    client,
    "SELECT * FROM metrics WHERE session_id = %(session_id)s",
    params={"session_id": session_id}
)

# String interpolation
result = poll_for_data(
    client,
    f"SELECT * FROM metrics WHERE session_id = '{session_id}'"
)
```

### Error Handling

```python
try:
    result = poll_for_data(client, query, params, max_wait_time=30.0)
except TimeoutError as e:
    # Data didn't appear - check logs, verify services are running
    pytest.fail(f"Data not found: {e}")
```

---

## ClickHouse Tables

E2E tests query these tables:

### `session_metrics`
- `window_start` (DateTime)
- `window_end` (DateTime)
- `session_id` (String)
- `user_id` (String)
- `event_count` (UInt64)
- Device info, session duration, etc.

### `event_metrics`
- `window_start` (DateTime)
- `window_end` (DateTime)
- `event_type` (String)
- `device_category` (String)
- `event_count` (UInt64)

### `performance_metrics`
- `window_start` (DateTime)
- `window_end` (DateTime)
- `device_category` (String)
- `avg_load_time` (Float64)
- `p95_load_time` (Float64)
- `event_count` (UInt64)

---

## Fixtures

E2E tests use these pytest fixtures (defined in `tests/e2e/conftest.py`):

- `clickhouse_client`: ClickHouse database client
- `ingestion_url`: Ingestion API base URL
- Other service-specific fixtures

---

## Debugging Failed E2E Tests

### 1. Check Services Are Running

```bash
docker compose -f infrastructure/compose/docker-compose.yml ps
```

All services should be "Up" (ingestion, cache, processing, storage, kafka, clickhouse, redis).

### 2. Enable Verbose Output

```bash
./run-tests.sh --e2e -s
```

Shows test output including print statements and logs.

### 3. Use Polling Verbose Mode

```python
result = poll_for_data(
    client, query, params,
    verbose=True  # Shows polling attempts
)
```

### 4. Check Kafka Topics

```bash
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic analytics-events \
  --from-beginning
```

### 5. Query ClickHouse Directly

```bash
docker compose exec clickhouse clickhouse-client

# Query tables
SELECT * FROM session_metrics ORDER BY window_start DESC LIMIT 10;
SELECT * FROM event_metrics ORDER BY window_start DESC LIMIT 10;
```

### 6. Check Service Logs

```bash
docker compose logs -f ingestion
docker compose logs -f processing
docker compose logs -f storage
```

---

## Test Data Cleanup

E2E tests use unique UUIDs for session_id and user_id to avoid conflicts. No manual cleanup needed between test runs.

The test environment uses Docker Compose which can be fully reset:

```bash
docker compose down -v  # Removes volumes (full data reset)
```

---

## CI/CD Integration

E2E tests are included in the test pipeline but can be skipped for faster feedback:

```bash
# Run everything except E2E
./run-tests.sh --unit --integration

# Run E2E only (for nightly builds)
./run-tests.sh --e2e
```

See `docs/testing/README.md` for complete test runner documentation.
