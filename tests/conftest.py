import os

import pytest
from clickhouse_driver import Client

CLICKHOUSE_HOST = os.environ.get("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = os.environ.get("CLICKHOUSE_PORT", 9000)
CLICKHOUSE_DB = os.environ.get("CLICKHOUSE_DB", "analytics")

TABLES_TO_CLEAN = [
    "event_metrics",
    "session_metrics",
    "performance_metrics",
]


@pytest.fixture(scope="module")
def clickhouse_client():
    """
    Creates a ClickHouse client fixture for tests once per module.
    """
    client = Client(
        host=CLICKHOUSE_HOST,
        port=int(CLICKHOUSE_PORT),
        user="admin",
        password="admin",
        database=CLICKHOUSE_DB,
    )
    # Verify connection
    client.execute("SELECT 1")
    yield client
    client.disconnect()


@pytest.fixture(autouse=True)
def clean_clickhouse_tables(clickhouse_client):
    """
    Truncates analytics tables before each test function.
    """
    for table in TABLES_TO_CLEAN:
        clickhouse_client.execute(f"TRUNCATE TABLE IF EXISTS {table}")
    yield
