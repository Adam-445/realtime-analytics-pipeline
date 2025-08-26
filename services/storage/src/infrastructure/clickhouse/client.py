"""ClickHouse client wrapper."""

from __future__ import annotations

import threading

from clickhouse_driver import Client
from src.core.config import settings
from src.infrastructure.clickhouse.ddl import ALL_DDLS


class ClickHouseClient:
    def __init__(self):
        self.client = Client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_db,
        )
        # A simple re-entrant lock to serialize inserts executed from multiple
        # asyncio.to_thread contexts. clickhouse-driver raises
        # PartiallyConsumedQueryError when overlapping queries occur on the
        # same connection. The overhead is negligible for our small batch sizes
        # and removes intermittent race failures under concurrent inserts.
        self._lock = threading.RLock()
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        for ddl in ALL_DDLS:
            self.client.execute(ddl)

    def insert_rows(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        # Derive stable column order from first row; ClickHouse expects
        # positional tuples
        first = rows[0]
        columns = list(first.keys())
        # Build VALUES format with explicit columns to avoid mismatch / missing fields
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES"
        data = [tuple(r.get(col) for col in columns) for r in rows]
        # Serialize access to the underlying synchronous driver connection.
        with self._lock:
            self.client.execute(query, data)
