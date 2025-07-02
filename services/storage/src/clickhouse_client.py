from clickhouse_driver import Client
from src.core.config import settings


class ClickHouseClient:
    def __init__(self):
        self.client = Client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_db,
        )
        self.create_tables()

    def create_tables(self):
        self.client.execute(
            """
        CREATE TABLE IF NOT EXISTS event_metrics (
            window_start DateTime64(3),
            window_end DateTime64(3),
            event_type String,
            event_count UInt64,
            user_count UInt64
        ) ENGINE = MergeTree()
        ORDER BY (window_start, event_type)
        """
        )

        self.client.execute(
            """
        CREATE TABLE IF NOT EXISTS session_metrics (
            session_id String,
            user_id String,
            start_time DateTime64(3),
            end_time DateTime64(3),
            duration UInt64,
            page_count UInt64,
            device_category String
        ) ENGINE = MergeTree()
        ORDER BY (start_time, session_id)
        """
        )

        self.client.execute(
            """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            window_start DateTime64(3),
            window_end DateTime64(3),
            device_category String,
            avg_load_time Float64,
            p95_load_time Float64
        ) ENGINE = MergeTree()
        ORDER BY (window_start, device_category)
        """
        )

    def insert_batch(self, table: str, batch: list[dict]):
        if not batch:
            return

        query = f"INSERT INTO {table} VALUES"
        self.client.execute(query, batch)
