"""Deprecated: use utils.clickhouse.metrics instead.

This module re-exports the shared ClickHouse metrics helpers to avoid breaking
any lingering imports. Prefer importing from `utils.clickhouse.metrics`.
"""

from utils.clickhouse.metrics import (  # noqa: F401
    get_event_metrics_total,
    settle_after_windows,
    wait_for_processed_delta,
)
