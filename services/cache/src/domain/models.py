from typing import Any, Dict

from pydantic import BaseModel


class MetricsWindow(BaseModel):
    """Represents a single metrics aggregation window."""

    window_start: int
    data: Dict[str, Any]


class OverviewSnapshot(BaseModel):
    """Aggregated view combining latest event & performance windows."""

    event_latest: Dict[str, Any]
    performance_latest: Dict[str, Any]
