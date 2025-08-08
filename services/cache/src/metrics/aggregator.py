import time
from typing import Any, Dict

from src.api.v1.routes.health import mark_first_event
from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.redis.client import RedisMetricsRepository
from src.metrics.bucketing import bucket_start
from src.metrics.key_hash import dimensions_hash

logger = get_logger("aggregator")


class EventAggregator:
    def __init__(self, repository: RedisMetricsRepository | None = None):
        self.repo = repository or RedisMetricsRepository()
        self.granularity = settings.bucket_granularity_seconds

    def process(self, event: Dict[str, Any]):
        """Process raw analytics event JSON.

        Expected shape (subset):
        {
          "event": {"type": str, ...},
          "user": {"id": str},
          "context": {"session_id": str, ...},
          "timestamp": epoch_ms
        }
        """
        try:
            event_type = event.get("event", {}).get("type")
            user_id = event.get("user", {}).get("id")
            session_id = event.get("context", {}).get("session_id")
            raw_ts = event.get("timestamp")
            # Accept int or string epoch ms
            if isinstance(raw_ts, str) and raw_ts.isdigit():
                ts_ms = int(raw_ts)
            elif isinstance(raw_ts, (int, float)):
                ts_ms = int(raw_ts)
            else:
                ts_ms = int(time.time() * 1000)
            # Optional app_id from properties
            app_id = (
                event.get("properties", {}).get("app_id")
                if isinstance(event.get("properties"), dict)
                else None
            )
            if not (event_type and user_id and session_id):
                logger.debug(
                    "Skipping event missing required fields",
                    extra={"have_event_type": bool(event_type)},
                )
                return
            ts_s = ts_ms // 1000
            b_start = bucket_start(ts_s, self.granularity)
            dims = {"event_type": event_type}
            if app_id:
                dims["app_id"] = str(app_id)
            dim_hash = dimensions_hash(dims)
            # Update counters
            self.repo.incr_event_count(dim_hash, b_start, 1)
            # Unique users & sessions
            self.repo.add_hll("unique_users", dim_hash, b_start, str(user_id))
            self.repo.add_hll("active_sessions", dim_hash, b_start, str(session_id))
            # Mark readiness on first successful event
            mark_first_event()
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to aggregate event", extra={"error": str(e)})
