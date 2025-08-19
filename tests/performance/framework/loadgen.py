import asyncio
import os
import time
from typing import Any, Iterable, Optional

import requests
from utils.ingestion.events import create_test_event

# Allow overriding ingestion endpoint via env (useful for local runs)
TRACK_URL = os.environ.get("PERF_TRACK_URL", "http://ingestion:8000/v1/analytics/track")


async def _send_httpx(client, payload: Any) -> None:
    resp = await client.post(TRACK_URL, json=payload)
    if resp.status_code != 202:
        raise Exception(f"Event sending failed: {resp.status_code}")


def _send_with_session(session: requests.Session, payload: Any) -> None:
    resp = session.post(TRACK_URL, json=payload, timeout=3)
    if resp.status_code != 202:
        raise Exception(f"Event sending failed: {resp.status_code}")


async def send_events_at_rate(
    rate: int,
    duration: int,
    batch_size: Optional[int] = None,  # ignored (single-event only)
    concurrency: Optional[int] = None,
) -> int:
    """Send events at specified rate (events/sec) for duration seconds.

    Uses async HTTP client with connection pooling for higher throughput.
    Returns number of events attempted (successful POSTs assumed based on 202).
    """
    if rate <= 0 or duration <= 0:
        return 0

    total_events = rate * duration

    # Determine number of concurrent workers to achieve desired rate
    # Aim for each worker to send 20-30 req/s; scale with batch_size
    if concurrency is not None:
        workers = concurrency
    else:
        base = max(10, rate // max(20, 1))
        workers = min(400, base)
    # seconds between requests per worker to achieve target rate
    period = workers / float(rate)

    sent_counter = 0
    start = time.time()
    end_time = start + duration

    # Prefer httpx.AsyncClient if available for true async concurrency
    try:
        import httpx

        enable_h2 = bool(int(__import__("os").environ.get("LOADGEN_HTTP2", "0")))
        limits = httpx.Limits(
            max_connections=max(400, workers * 4),
            max_keepalive_connections=max(400, workers * 3),
        )
        timeout = httpx.Timeout(connect=2.0, read=3.0, write=3.0, pool=5.0)
        headers = {
            "Connection": "keep-alive",
            "User-Agent": "perf-loadgen/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=enable_h2,
            headers=headers,
        ) as client:
            # Worker coroutine: send with interval pacing and catch-up if behind
            async def worker(idx: int):
                nonlocal sent_counter
                # Stagger initial start to distribute evenly in first period
                next_ts = start + (idx % workers) * (period / workers)
                while True:
                    now = time.time()
                    if now >= end_time:
                        break
                    if now < next_ts:
                        await asyncio.sleep(min(next_ts - now, 0.005))
                        continue
                    # We're due (or behind) — send one or more events until caught up
                    # Recompute 'now' inside the inner loop to avoid spinning
                    while True:
                        now = time.time()
                        if now >= end_time or now < next_ts:
                            break
                        # Build single-event payload (batching removed for realism)
                        payload = create_test_event(
                            event_type=os.environ.get(
                                "PERF_EVENT_TYPE", "perf_test_event"
                            ),
                            user_id=(f"perf-user-{idx}-{int((now-start)*1000)}"),
                            session_id=(f"perf-session-{idx}-{int((now-start)*1000)}"),
                        )
                        inc = 1
                        try:
                            await _send_httpx(client, payload)
                            sent_counter += inc
                        except Exception:
                            # Best-effort; continue
                            pass
                        next_ts += period

            tasks = [asyncio.create_task(worker(i)) for i in range(workers)]
            await asyncio.gather(*tasks)
    except Exception:
        # Fallback to requests + thread pool via loop executor (single-event)
        batches = total_events
        batch_interval = 1 / rate
        with requests.Session() as session:
            session.headers.update({"Connection": "keep-alive"})
            try:
                from requests.adapters import HTTPAdapter

                adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
            except Exception:
                pass
            loop = asyncio.get_running_loop()
            for i in range(batches):
                payload = create_test_event(
                    event_type=os.environ.get("PERF_EVENT_TYPE", "perf_test_event"),
                    user_id=f"perf-user-{i}",
                    session_id=f"perf-session-{i}",
                )
                await loop.run_in_executor(None, _send_with_session, session, payload)
                sent_counter += 1
                # Rate pacing
                elapsed = time.time() - start
                expected_time = (i + 1) * batch_interval
                if expected_time > elapsed:
                    await asyncio.sleep(expected_time - elapsed)

    return sent_counter


def chunked(iterable: Iterable, size: int):
    it = iter(iterable)
    while True:
        chunk = []
        try:
            for _ in range(size):
                chunk.append(next(it))
        except StopIteration:
            if chunk:
                yield chunk
            break
        yield chunk
