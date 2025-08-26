EVENT_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS event_metrics (
    window_start DateTime64(3),
    window_end DateTime64(3),
    event_type String,
    event_count UInt64,
    user_count UInt64
) ENGINE = MergeTree()
ORDER BY (window_start, event_type)
"""

SESSION_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS session_metrics (
    session_id String,
    user_id String,
    start_time DateTime64(3),
    end_time DateTime64(3),
    duration UInt64,
    page_count UInt64,
    device_category String
) ENGINE = MergeTree()
ORDER BY (start_time, session_id)
"""

PERFORMANCE_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS performance_metrics (
    window_start DateTime64(3),
    window_end DateTime64(3),
    device_category String,
    avg_load_time Float64,
    p95_load_time Float64
) ENGINE = MergeTree()
ORDER BY (window_start, device_category)
"""

ALL_DDLS = [
    EVENT_METRICS_DDL,
    SESSION_METRICS_DDL,
    PERFORMANCE_METRICS_DDL,
]
