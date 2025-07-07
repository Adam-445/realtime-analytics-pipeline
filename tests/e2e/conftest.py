import os

import pytest
from clickhouse_driver import Client

# @pytest.fixture(scope="module")
# def clickhouse_client():
#     """
#     Creates and provides a ClickHouse client fixture for tests.
#     It's 'module' scoped, so it's created once per test module.
#     """
#     try:
#         client = Client(
#             host=CLICKHOUSE_HOST,
#             port=CLICKHOUSE_PORT,
#             user="admin",
#             password="admin",
#             database="analytics",
#         )
#         # Verify connection
#         client.execute("SELECT 1")
#         print("ClickHouse client connected.")
#         yield client
#     finally:
#         if "client" in locals() and client.connection.connected:
#             client.disconnect()
#             print("\nClickHouse client disconnected.")


# Use the same host/port logic you already have
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
        # TRUNCATE is effectively a fast DELETE in ClickHouse
        clickhouse_client.execute(f"TRUNCATE TABLE IF EXISTS {table}")
    yield
    # No cleanup needed after test, since next invocation will truncate again
