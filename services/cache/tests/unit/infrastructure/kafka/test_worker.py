import asyncio
from typing import Any, cast

import pytest
from src.infrastructure.kafka.worker import redis_batch_worker


class DummyRepo:
    def __init__(self):
        self.applied = []
        self.fail_once = False

    async def pipeline_apply(self, ops):
        # simulate a small delay to exercise timing
        await asyncio.sleep(0.01)
        if self.fail_once:
            # fail exactly once to exercise retry, then succeed subsequently
            self.fail_once = False
            raise RuntimeError("transient redis failure")
        self.applied.append(list(ops))


class DummyConsumer:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


class RepoRecords:
    def __init__(self):
        self.applied = []

    async def pipeline_apply(self, ops):
        self.applied.append(list(ops))


class ConsumerCommitFailOnce:
    def __init__(self):
        self.calls = 0
        self.fail_once = True

    async def commit(self):
        self.calls += 1
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("commit failed once")


@pytest.mark.asyncio
async def test_worker_batches_and_commits(monkeypatch):
    # settings for fast flush
    from src.core import config as cfg

    monkeypatch.setattr(cfg.settings, "kafka_commit_interval_ms", 10)
    monkeypatch.setattr(cfg.settings, "redis_write_batch_size", 3)

    q: asyncio.Queue = asyncio.Queue()
    repo = DummyRepo()
    stop = asyncio.Event()
    consumer = DummyConsumer()

    async def produce():
        # enqueue 5 ops; expect 2 batches (3 + 2)
        for i in range(5):
            await q.put({"type": "event", "window_start": i, "fields": {"v": i}})
        # signal stop after a moment
        await asyncio.sleep(0.05)
        stop.set()

    prod_task = asyncio.create_task(produce())
    worker = asyncio.create_task(  # type: ignore[arg-type]
        redis_batch_worker(
            queue=q,
            repo=cast(Any, repo),
            stop_event=stop,
            kafka_consumer=cast(Any, consumer),
        )
    )

    await asyncio.gather(prod_task, worker)

    # Two batches applied (3 then 2)
    assert len(repo.applied) >= 2
    total_items = sum(len(b) for b in repo.applied)
    assert total_items == 5
    # Commits happened at least once
    assert consumer.commits >= 1


@pytest.mark.asyncio
async def test_worker_retries_on_redis_failure(monkeypatch):
    from src.core import config as cfg

    # Make time-based flush quick, and batch size small
    monkeypatch.setattr(cfg.settings, "kafka_commit_interval_ms", 10)
    monkeypatch.setattr(cfg.settings, "redis_write_batch_size", 2)

    q: asyncio.Queue = asyncio.Queue()
    repo = DummyRepo()
    repo.fail_once = True
    stop = asyncio.Event()
    consumer = DummyConsumer()

    async def produce():
        for i in range(3):
            await q.put({"type": "event", "window_start": i, "fields": {"v": i}})
        await asyncio.sleep(0.05)
        stop.set()

    prod_task = asyncio.create_task(produce())
    worker = asyncio.create_task(  # type: ignore[arg-type]
        redis_batch_worker(
            queue=q,
            repo=cast(Any, repo),
            stop_event=stop,
            kafka_consumer=cast(Any, consumer),
        )
    )

    await asyncio.gather(prod_task, worker)

    # Despite an initial failure, we should have eventually applied batches
    assert sum(len(b) for b in repo.applied) == 3
    # Commits should still occur
    assert consumer.commits >= 1


@pytest.mark.asyncio
async def test_worker_final_flush_on_shutdown(monkeypatch):
    from src.core import config as cfg

    # Force large batch size and long interval so only final flush writes
    monkeypatch.setattr(cfg.settings, "kafka_commit_interval_ms", 1000)
    monkeypatch.setattr(cfg.settings, "redis_write_batch_size", 1000)

    q: asyncio.Queue = asyncio.Queue()
    repo = RepoRecords()
    stop = asyncio.Event()
    consumer = ConsumerCommitFailOnce()

    # Put fewer than batch size so only final flush writes
    for i in range(2):
        await q.put({"type": "event", "window_start": i, "fields": {"v": i}})

    # Start worker then trigger shutdown quickly
    worker = asyncio.create_task(  # type: ignore[arg-type]
        redis_batch_worker(
            queue=q,
            repo=cast(Any, repo),
            stop_event=stop,
            kafka_consumer=cast(Any, consumer),
        )
    )
    await asyncio.sleep(0.02)
    stop.set()
    await worker

    # Final flush should have applied the 2 ops
    assert sum(len(b) for b in repo.applied) == 2
    # Commit attempted (may fail once but worker continues)
    assert consumer.calls >= 1


@pytest.mark.asyncio
async def test_worker_commit_failure_path(monkeypatch):
    from src.core import config as cfg

    monkeypatch.setattr(cfg.settings, "kafka_commit_interval_ms", 10)
    monkeypatch.setattr(cfg.settings, "redis_write_batch_size", 1)

    q: asyncio.Queue = asyncio.Queue()
    repo = RepoRecords()
    stop = asyncio.Event()
    consumer = ConsumerCommitFailOnce()

    # One item to force a flush and trigger a commit failure once
    await q.put({"type": "event", "window_start": 1, "fields": {"v": 1}})

    async def stop_soon():
        await asyncio.sleep(0.05)
        stop.set()

    stopper = asyncio.create_task(stop_soon())
    worker = asyncio.create_task(  # type: ignore[arg-type]
        redis_batch_worker(
            queue=q,
            repo=cast(Any, repo),
            stop_event=stop,
            kafka_consumer=cast(Any, consumer),
        )
    )
    await asyncio.gather(worker, stopper)

    # Applied at least one batch
    assert len(repo.applied) >= 1
    # Commit was attempted at least once
    assert consumer.calls >= 1
