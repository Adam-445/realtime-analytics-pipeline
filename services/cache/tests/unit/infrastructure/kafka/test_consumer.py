import asyncio

import pytest


class DummyKafkaConsumer:
    def __init__(self, start_failures: int = 2):
        self._failures_left = start_failures
        self.start_calls = 0
        self.stopped = False

    async def start(self):
        self.start_calls += 1
        if self._failures_left > 0:
            self._failures_left -= 1
            raise RuntimeError("start failure")

    # Support `async for msg in consumer:` by being an async iterator
    def __aiter__(self):
        return self

    async def __anext__(self):
        # Block until cancelled; we don't yield any messages in this test
        try:
            while True:
                await asyncio.sleep(0.05)
        except asyncio.CancelledError as e:
            raise e

    async def stop(self):
        self.stopped = True


class DummyAdminClient:
    async def start(self):
        return None

    async def create_topics(self, new_topics, validate_only=False):
        return None

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_start_consumer_with_retries(monkeypatch):
    # Import helper and module for patching
    from src.infrastructure.kafka import consumer as consumer_mod
    from src.infrastructure.kafka.consumer import start_consumer_with_retries

    dummy_consumer = DummyKafkaConsumer(start_failures=2)

    # Speed up retry backoff within the helper
    async def no_wait(_delay: float):
        return None

    monkeypatch.setattr(consumer_mod.asyncio, "sleep", no_wait)
    # Ensure the helper uses the patched asyncio
    monkeypatch.setitem(
        start_consumer_with_retries.__globals__, "asyncio", consumer_mod.asyncio
    )

    # Provide a no-op ensure topics callback
    async def noop():
        return None

    await start_consumer_with_retries(dummy_consumer, ensure_topics_cb=noop)

    # Two failures + one success => three start attempts
    assert dummy_consumer.start_calls == 3
