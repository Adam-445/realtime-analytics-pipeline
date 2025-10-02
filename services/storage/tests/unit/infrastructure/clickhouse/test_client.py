from unittest.mock import MagicMock, patch

from src.infrastructure.clickhouse import ddl as ddl_module
from src.infrastructure.clickhouse.client import ClickHouseClient


def test_clickhouse_client_ensures_tables():
    with patch("src.infrastructure.clickhouse.client.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Ensure there is at least one DDL
        assert len(ddl_module.ALL_DDLS) > 0

        ClickHouseClient()

        # Called once per DDL
        assert mock_client.execute.call_count == len(ddl_module.ALL_DDLS)


def test_insert_rows_builds_query_and_executes():
    with patch("src.infrastructure.clickhouse.client.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        ch = ClickHouseClient()

        rows = [
            {"window_start": 1, "event_type": "click", "event_count": 2},
            {"window_start": 1, "event_type": "view", "event_count": 3},
        ]

        ch.insert_rows("event_metrics", rows)

        # Verify query and parameterization
        assert mock_client.execute.call_count == len(ddl_module.ALL_DDLS) + 1
        query = mock_client.execute.call_args[0][0]
        params = mock_client.execute.call_args[0][1]
        assert query.startswith("INSERT INTO event_metrics (")
        assert isinstance(params, list)
        assert params[0] == (1, "click", 2)
        assert params[1] == (1, "view", 3)
