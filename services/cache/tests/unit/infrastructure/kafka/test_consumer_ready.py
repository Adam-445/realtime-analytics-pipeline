import asyncio

import pytest


class DummyKafkaConsumer:
    async def start(self):
        return None

    def __aiter__(self):
        return self

    _yielded = False

    async def __anext__(self):
        # Yield a single message then stop
        if not self._yielded:
            self._yielded = True

            class M:
                topic = "event_metrics"
                value = {
                    "window_start": 1710000000000,
                    "event_type": "click",
                    "event_count": 1,
                    "user_count": 1,
                }

            return M()
        raise StopAsyncIteration

    async def stop(self):
        return None


@pytest.mark.asyncio
async def test_consumer_sets_ready_event(monkeypatch):
    from src.infrastructure.kafka import consumer as consumer_mod
    from src.infrastructure.kafka.consumer import (
        consume_loop,
        start_consumer_with_retries,
    )

    # Patch Kafka consumer factory to our dummy
    dummy_consumer = DummyKafkaConsumer()
    monkeypatch.setattr(
        consumer_mod, "AIOKafkaConsumer", lambda *a, **k: dummy_consumer
    )

    # No-op ensure topics and fast start
    async def no_wait(_):
        return None

    monkeypatch.setattr(consumer_mod.asyncio, "sleep", no_wait)
    monkeypatch.setitem(
        start_consumer_with_retries.__globals__,
        "asyncio",
        consumer_mod.asyncio,
    )

    # Minimal repo that just records calls
    class Repo:
        async def pipeline_apply(self, ops):
            return None

    class AppState:
        def __init__(self):
            self.ready_event = asyncio.Event()

    repo = Repo()  # type: ignore[assignment]
    app_state = AppState()

    await consume_loop(repo, app_state)  # type: ignore[arg-type]

    assert app_state.ready_event.is_set() is True
