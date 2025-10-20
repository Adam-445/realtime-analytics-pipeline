# Cache Internals

Consumes metric topics and maintains windowed aggregates in Redis for low-latency access. Exposes health/readiness endpoints and metrics views.

- Source: `services/cache`
- Entrypoint: `services/cache/src/main.py`
- Kafka consumer: `services/cache/src/infrastructure/kafka/consumer.py`
- Redis repository: `services/cache/src/infrastructure/redis/repository.py`
- API: `services/cache/src/api/*`

## Responsibilities

- Consume metric topics (event and performance) and translate them into Redis write operations
- Maintain recency-ordered indices of window starts per metric type
- Enforce retention and TTL to bound memory usage
- Provide HTTP endpoints to read recent windows and overviews

## Kafka Consumption and Batching

- Topics subscribed (defaults): `event_metrics`, `performance_metrics`
- Group: `cache_kafka_consumer_group` (default `cache-service`), `auto_offset_reset = cache_consume_from` (default `latest`)
- Startup with retries and optional topic availability checks (`start_consumer_with_retries`)
- The main `consume_loop`:
  - Parses each Kafka message by topic to an `Operation` via `message_parser.parse_message`
  - Enqueues operations into an asyncio Queue (bounded by `redis_queue_max_size`)
  - A background `redis_batch_worker` drains the queue, applies batched Redis writes, and commits Kafka offsets upon success

## Redis Data Model

Key primitives defined by `shared.constants.RedisKeys` and used in `CacheRepository`:

- Window hashes per type:
  - `WINDOW_EVENT_HASH.format(window_start=ts_ms)`
  - `WINDOW_PERF_HASH.format(window_start=ts_ms)`
- Sorted-set indices for recency ordering:
  - `WINDOW_EVENT_INDEX`
  - `WINDOW_PERF_INDEX`
- PubSub channel for updates:
  - `PUBSUB_CHANNEL_UPDATES`

Stored fields are flattened metrics, e.g.:
- Event: `{ "page_view.count": 2, "page_view.users": 2 }`
- Performance: `{ "Desktop.avg_load_time": 300.0, "Desktop.p95_load_time": 450.0 }`

Retention:
- `window_retention_count` bounds the number of window entries per type kept in the sorted set
- `window_hash_ttl_seconds` applies TTL on hashes as a safety

## Repository Operations

- `store_event_window(window_start_ms, fields)` / `store_performance_window(...)`
- `pipeline_apply(ops)` applies a mixed batch of event/perf operations using a Redis pipeline and trims touched indices
- `get_latest_event_window()` returns the most recent event window
- `get_last_event_windows(limit)` / `get_last_performance_windows(limit)` return recent windows ordered by recency

## Readiness and Health

- `/healthz`: pings Redis; returns 200 `{ "status": "ok", "redis": true }` when healthy
- `/readyz`: returns 200 when the consumer has started and signaled readiness; otherwise 503

## Configuration (selected)

From `services/cache/src/core/config.py`:
- Kafka: `kafka_bootstrap_servers`, `cache_kafka_topics`, `cache_kafka_consumer_group`, `cache_consume_from`
- Redis: `redis_host`, `redis_port`, `redis_db`
- Windows/retention: `window_retention_count`, `window_hash_ttl_seconds`, `active_session_ttl_seconds`
- Batching/perf: `kafka_commit_batch_size`, `kafka_commit_interval_ms`, `redis_write_batch_size`, `redis_queue_max_size`
- Health/lag: `ready_lag_threshold`

Quick reference:

| Key | Default | Purpose |
| --- | --- | --- |
| kafka_bootstrap_servers | kafka1:19092 | Kafka brokers |
| cache_kafka_topics | [event_metrics, performance_metrics] | Subscribed topics |
| cache_kafka_consumer_group | cache-service | Consumer group |
| cache_consume_from | latest | Startup offset behavior |
| redis_host | redis | Redis hostname |
| redis_port | 6379 | Redis port |
| redis_db | 0 | Redis database index |
| window_retention_count | 120 | Number of recent windows to retain |
| window_hash_ttl_seconds | 21600 | TTL for window hashes (safety) |
| active_session_ttl_seconds | 1900 | TTL for session tracking |
| kafka_commit_batch_size | 100 | Target messages per commit batch |
| kafka_commit_interval_ms | 1000 | Max time between commits |
| redis_write_batch_size | 50 | Batch size for Redis pipeline |
| redis_queue_max_size | 5000 | Back-pressure on enqueued ops |
| ready_lag_threshold | 5000 | Lag threshold for readiness |

## Operational Notes

- Kafka offsets are committed only after successful Redis writes (at batch flush boundaries)
- On Redis failure, the same batch is retried after a short delay without committing offsets
- Flattened field naming allows simple composition of multiple event types or device categories

## Related

- Endpoints: see [API](../../api/README.md) and [Testing Endpoints](../../testing/endpoints.md)
- Upstream: [Processing Internals](../processing/README.md)
