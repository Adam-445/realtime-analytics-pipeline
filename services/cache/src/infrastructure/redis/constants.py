# Metrics windows (event & performance)
WINDOW_EVENT_HASH = "metrics:event:{window_start}"
WINDOW_EVENT_INDEX = "metrics:event:windows"
WINDOW_PERF_HASH = "metrics:perf:{window_start}"
WINDOW_PERF_INDEX = "metrics:perf:windows"

# Sessions
SESSION_COMPLETED_LIST = "metrics:session:completed"  # candidate for stream later
ACTIVE_SESSION_HASH = "session:active:{session_id}"
ACTIVE_SESSION_INDEX = "session:active:index"

# Rollups / aggregations
ROLLUP_EVENT_CURRENT = "rollup:events:current_window:{event_type}"
ROLLUP_ACTIVE_USERS_HLL = "rollup:active_users:hyperloglog"

# Pub/Sub channels
PUBSUB_CHANNEL_UPDATES = "channel:metrics:updates"
