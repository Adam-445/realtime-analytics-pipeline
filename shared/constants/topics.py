class Topics:
    """Centralised Kafka topic definitions"""

    # Core topics
    EVENTS = "analytics_events"

    # Metric topics
    EVENT_METRICS = "event_metrics"
    SESSION_METRICS = "session_metrics"
    PERFORMANCE_METRICS = "performance_metrics"

    @classmethod
    def all_metrics_topics(cls) -> list[str]:
        """Get all metric topics"""
        return [cls.EVENT_METRICS, cls.SESSION_METRICS, cls.PERFORMANCE_METRICS]

    @classmethod
    def all_topics(cls) -> list[str]:
        return [cls.EVENTS] + cls.all_metrics_topics()
