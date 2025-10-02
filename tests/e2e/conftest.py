import os
import time

import pytest
from clickhouse_driver import Client
from utils.clickhouse.poll import poll_for_data
from utils.ingestion.events import create_test_event, send_event

# ClickHouse connection defaults
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "analytics")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "admin")
CLICKHOUSE_PASS = os.getenv("CLICKHOUSE_PASS", "admin")

TABLES_TO_CLEAN = [
    "event_metrics",
    "session_metrics",
    "performance_metrics",
]


@pytest.fixture(scope="session")
def clickhouse_client():
    """Session-scoped ClickHouse client reused across tests for speed."""
    client = Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASS,
        database=CLICKHOUSE_DB,
    )
    try:
        client.execute("SELECT 1")
    except Exception as e:  # pragma: no cover - infrastructure failure
        pytest.exit(
            f"Cannot connect to ClickHouse at {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}: {e}"
        )
    yield client
    client.disconnect()


@pytest.fixture(scope="function", autouse=True)
def clean_test_environment(clickhouse_client: Client):
    """Truncate all metrics tables before each test for isolation."""
    for tbl in TABLES_TO_CLEAN:
        clickhouse_client.execute(f"TRUNCATE TABLE IF EXISTS {tbl}")
    # Small pause to allow any in-flight async inserts to settle before test starts
    time.sleep(0.25)


@pytest.fixture(scope="session")
def test_config() -> dict:
    """Session-wide default test configuration"""
    config = {
        "processing_session_gap_seconds": int(
            os.getenv("PROCESSING_SESSION_GAP_SECONDS", "1800")
        ),
        "processing_metrics_window_size_seconds": int(
            os.getenv("PROCESSING_METRICS_WINDOW_SIZE_SECONDS", "60")
        ),
        "processing_performance_window_size_seconds": int(
            os.getenv("PROCESSING_PERFORMANCE_WINDOW_SIZE_SECONDS", "300")
        ),
        "flink_watermark_delay_seconds": int(
            os.getenv("FLINK_WATERMARK_DELAY_SECONDS", "10")
        ),
        "max_wait_time": 30,
        "poll_interval": 2,
    }
    # print("Loaded test_config:", config)
    return config


# Warm-up: ensure pipeline components are ready before first test
@pytest.fixture(scope="session", autouse=True)
def pipeline_warmup(clickhouse_client: Client, test_config: dict):
    """Send one event and wait for its aggregation"""
    try:
        event = create_test_event(event_type="page_view")
        send_event(event)
        poll_for_data(
            clickhouse_client=clickhouse_client,
            query="""
            SELECT event_type, event_count, user_count
            FROM event_metrics
            WHERE event_type = 'page_view'
            """,
            max_wait_time=min(25, test_config.get("max_wait_time", 30)),
            poll_interval=1,
            expected_count=1,
        )
    except Exception:
        return
