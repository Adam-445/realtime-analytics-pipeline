import asyncio

import fakeredis.aioredis
import pytest
from src.domain.operations import Operation
from src.infrastructure.redis.repository import CacheRepository

from shared.constants import RedisKeys


@pytest.mark.asyncio
async def test_pipeline_apply_stores_hashes_and_indices():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    repo = CacheRepository(r, window_retention_count=10, window_hash_ttl=60)
    ops: list[Operation] = [
        Operation(type="event", window_start=1000, fields={"click.count": 5}),
        Operation(type="perf", window_start=2000, fields={"mobile.avg_load_time": 1.2}),
    ]
    await repo.pipeline_apply(ops)

    event_key = RedisKeys.window_key("event", 1000)
    perf_key = RedisKeys.window_key("performance", 2000)

    ev = r.hgetall(event_key)
    if hasattr(ev, "__await__"):
        ev = await ev  # type: ignore[assignment]
    pf = r.hgetall(perf_key)
    if hasattr(pf, "__await__"):
        pf = await pf  # type: ignore[assignment]
    assert ev == {"click.count": "5"}
    assert pf == {"mobile.avg_load_time": "1.2"}

    event_index = await r.zrevrange(RedisKeys.WINDOW_EVENT_INDEX, 0, -1)
    perf_index = await r.zrevrange(RedisKeys.WINDOW_PERF_INDEX, 0, -1)
    assert str(1000) in event_index
    assert str(2000) in perf_index


@pytest.mark.asyncio
async def test_get_latest_and_conversion():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    repo = CacheRepository(r, window_retention_count=10, window_hash_ttl=60)

    await repo.store_event_window(1000, {"foo": 1, "bar": 2.5, "baz": "x"})
    latest = await repo.get_latest_event_window()
    assert latest is not None
    assert latest["window_start"] == 1000
    # type conversion
    assert isinstance(latest["foo"], int)
    assert isinstance(latest["bar"], float)


@pytest.mark.asyncio
async def test_retention_trimming():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    repo = CacheRepository(r, window_retention_count=3, window_hash_ttl=60)
    # create 5 windows
    for i in range(5):
        await repo.store_event_window(1000 + i, {"v": i})
    # only last 3 should remain in index (sorted zset ascending score,
    # we keep newest by trimming lowest rank)
    ids = await r.zrange(RedisKeys.WINDOW_EVENT_INDEX, 0, -1)
    # expect newest 3: 1002,1003,1004 (older removed)
    assert ids == ["1002", "1003", "1004"]


@pytest.mark.asyncio
async def test_publish_update():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    repo = CacheRepository(r, window_retention_count=3, window_hash_ttl=60)
    # fakeredis pubsub capture
    psub = r.pubsub()
    # Use direct channel subscribe (psubscribe expects pattern semantics)
    await psub.subscribe(RedisKeys.PUBSUB_CHANNEL_UPDATES)
    await repo.publish_update({"a": 1})
    # Allow event loop turn
    await asyncio.sleep(0)
    message = None
    # poll a few times to allow fakeredis pubsub loop to process
    for _ in range(5):
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=0.2)
        if message:
            break
        await asyncio.sleep(0)
    assert message is not None, "Expected pubsub message but none received"
    assert message["data"] == '{"a": 1}'
