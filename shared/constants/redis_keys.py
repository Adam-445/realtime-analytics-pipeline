class RedisKeys:
    """Centralised Redis key pattern definitions"""

    # Window data patterns
    WINDOW_EVENT_HASH = "metrics:event:{window_start}"
    WINDOW_PERF_HASH = "metrics:perf:{window_start}"
    WINDOW_SESSION_HASH = "metrics:session:{window_start}"

    # Index patterns
    WINDOW_EVENT_INDEX = "metrics:event:windows"
    WINDOW_PERF_INDEX = "metrics:perf:windows"
    WINDOW_SESSION_INDEX = "metrics:session:windows"

    # PubSub patterns
    PUBSUB_CHANNEL_UPDATES = "cache:updates"

    # Session patterns
    ACTIVE_SESSION_SET = "sessions:active"
    SESSION_DATA_HASH = "session:{session_id}"

    @classmethod
    def window_key(cls, metric_type: str, window_start: int) -> str:
        """Generate window key for given metric type."""
        patterns = {
            "event": cls.WINDOW_EVENT_HASH,
            "performance": cls.WINDOW_PERF_HASH,
            "session": cls.WINDOW_SESSION_HASH,
        }
        pattern = patterns.get(metric_type)
        if not pattern:
            raise ValueError(f"Unknown metric type: {metric_type}")
        return pattern.format(window_start=window_start)

    @classmethod
    def session_key(cls, session_id: str) -> str:
        """Generate session key for given session ID."""
        return cls.SESSION_DATA_HASH.format(session_id=session_id)
