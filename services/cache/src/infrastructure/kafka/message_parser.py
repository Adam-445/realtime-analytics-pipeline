from __future__ import annotations

from typing import Any, Optional

from src.core.logger import get_logger
from src.domain.operations import Operation

logger = get_logger("cache.message_parser")


def parse_message(topic: str, payload: dict) -> Optional[Operation]:
    """Translate a raw Kafka topic/payload into an Operation or None.

    Returns None for topics we intentionally ignore.
    """
    if topic == "event_metrics":
        window_start = _coerce_ts(payload.get("window_start"))
        if window_start is None:
            return None
        event_type = payload.get("event_type")
        if not event_type:
            return None
        fields = {
            f"{event_type}.count": int(payload.get("event_count", 0)),
            f"{event_type}.users": int(payload.get("user_count", 0)),
        }
        return Operation(type="event", window_start=window_start, fields=fields)
    if topic == "performance_metrics":
        window_start = _coerce_ts(payload.get("window_start"))
        if window_start is None:
            return None
        device_category = payload.get("device_category")
        if not device_category:
            return None
        fields = {
            f"{device_category}.avg_load_time": float(
                payload.get("avg_load_time", 0.0)
            ),
            f"{device_category}.p95_load_time": float(
                payload.get("p95_load_time", 0.0)
            ),
        }
        return Operation(type="perf", window_start=window_start, fields=fields)
    if topic == "session_metrics":
        return None
    logger.warning("unhandled_topic", extra={"topic": topic})
    return None


def _coerce_ts(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except Exception:  # noqa
            logger.warning("invalid_window_start", extra={"value": value})
    return None
