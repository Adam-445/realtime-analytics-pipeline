from clickhouse_driver import Client
from src.core.config import settings
from src.infrastructure.clickhouse.ddl import ALL_DDLS


class ClickHouseClient:
    """Light wrapper around clickhouse-driver Client handling DDL and inserts."""

    def __init__(self):
        self.client = Client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_db,
        )
        self._ensure_tables()

    def _ensure_tables(self):
        for ddl in ALL_DDLS:
            self.client.execute(ddl)

    def insert_rows(self, table: str, rows: list[dict]):
        """Insert a collection of row dicts into table.

        Uses simple VALUES insertion; future optimization could provide a
        columnar layout or JSONEachRow format depending on benchmark results.
        """
        if not rows:
            return
        query = f"INSERT INTO {table} VALUES"
        self.client.execute(query, rows)
