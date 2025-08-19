from __future__ import annotations

import os
import time
from typing import Any

from clickhouse_driver import Client


def _event_type() -> str:
    return os.environ.get("PERF_EVENT_TYPE", "perf_test_event")


def _total_query_for_event_type(event_type: str) -> str:
    safe = event_type.replace("'", "'")
    return (
        "SELECT sum(event_count) as total FROM event_metrics "
        f"WHERE event_type = '{safe}'"
    )


def get_event_metrics_total(client: Client) -> int:
    """Return the current total event_count for this run's event_type."""
    try:
        res: Any = client.execute(_total_query_for_event_type(_event_type()))
        if isinstance(res, list) and res:
            row0 = res[0]
            if isinstance(row0, (list, tuple)) and row0:
                val = row0[0]
            else:
                val = row0
            if isinstance(val, (int, float)):
                return int(val)
            try:
                return int(str(val)) if val is not None else 0
            except Exception:
                return 0
        return 0
    except Exception:
        return 0


def wait_for_processed_delta(
    client: Client,
    *,
    baseline_total: int,
    target_delta: int,
    timeout: float,
    poll_interval: float,
) -> int:
    deadline = time.time() + max(0.0, float(timeout))
    processed_total = 0
    while time.time() < deadline:
        current_total = get_event_metrics_total(client)
        processed_total = max(0, current_total - baseline_total)
        if processed_total >= target_delta:
            break
        time.sleep(max(0.01, float(poll_interval)))
    return processed_total


def settle_after_windows(
    *,
    metrics_window_seconds: int,
    watermark_delay_seconds: int,
    extra_seconds: int = 2,
) -> None:
    wait_s = (
        int(metrics_window_seconds) + int(watermark_delay_seconds) + int(extra_seconds)
    )
    time.sleep(max(0, wait_s))
