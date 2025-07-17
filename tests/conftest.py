import os
import time

import pytest
from clickhouse_driver import Client

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


@pytest.fixture(scope="module")
def clickhouse_client():
    """ClickHouse client, connected once per test module."""
    client = Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASS,
        database=CLICKHOUSE_DB,
    )
    try:
        client.execute("SELECT 1")
    except Exception as e:
        pytest.exit(
            f"Cannot connect to ClickHouse at {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}: {e}"
        )
    yield client
    client.disconnect()


@pytest.fixture(scope="function", autouse=True)
def clean_test_environment(clickhouse_client: Client):
    """
    Truncate all test tables before each test function.
    Adds a brief pause to allow upstream sinks (e.g. Flink) to quiesce.
    """
    for tbl in TABLES_TO_CLEAN:
        clickhouse_client.execute(f"TRUNCATE TABLE IF EXISTS {tbl}")
    time.sleep(1)


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
