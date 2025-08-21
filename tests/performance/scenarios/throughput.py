from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from core.config import TestConfig
from core.generator import EventGenerator
from core.metrics import Metrics


class ThroughputScenario:
    def __init__(self, config: TestConfig):
        self.config = config
        self.gen = EventGenerator(config)
        self.metrics = Metrics()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(config.max_concurrent_connections)

    async def setup(self):
        connector = aiohttp.TCPConnector(
            limit=self.config.connection_pool_size,
            limit_per_host=self.config.connection_pool_size,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
            ttl_dns_cache=300,
        )
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
        # quick verify
        async with self.session.get(f"{self.config.ingestion_url}/docs") as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ingestion not ready: {resp.status}")

    async def send_single(self) -> Dict:
        event = self.gen.generate_event()
        start = time.time()
        async with self.semaphore:
            try:
                assert self.session is not None
                async with self.session.post(
                    f"{self.config.ingestion_url}/v1/analytics/track", json=event
                ) as resp:
                    rt = (time.time() - start) * 1000
                    if resp.status in (200, 202):
                        self.metrics.successful_requests += 1
                        self.metrics.response_times.append(rt)
                        return {"ok": True, "rt": rt}
                    self.metrics.failed_requests += 1
                    self.metrics.http_errors[resp.status] = (
                        self.metrics.http_errors.get(resp.status, 0) + 1
                    )
                    return {"ok": False, "rt": rt, "status": resp.status}
            except asyncio.TimeoutError:
                rt = (time.time() - start) * 1000
                self.metrics.failed_requests += 1
                self.metrics.timeout_errors += 1
                return {"ok": False, "rt": rt, "error": "timeout"}
            except Exception as e:
                rt = (time.time() - start) * 1000
                self.metrics.failed_requests += 1
                self.metrics.connection_errors += 1
                return {"ok": False, "rt": rt, "error": str(e)}
            finally:
                self.metrics.total_requests += 1

    async def _scheduled(self, delay: float):
        await asyncio.sleep(delay)
        return await self.send_single()

    async def _monitor(self, started_at: float):
        try:
            while True:
                await asyncio.sleep(5)
                elapsed = time.time() - started_at
                rps = self.metrics.total_requests / elapsed if elapsed > 0 else 0
                if rps > self.metrics.peak_rps:
                    self.metrics.peak_rps = rps
                ok_pct = (
                    self.metrics.successful_requests
                    / max(self.metrics.total_requests, 1)
                ) * 100
                print(
                    f"[PROGRESS] {elapsed:.1f}s RPS={rps:.1f} "
                    f"total={self.metrics.total_requests} ok%={ok_pct:.1f}"
                )
        except asyncio.CancelledError:
            pass

    async def run(self) -> Metrics:
        self.metrics.start_time = datetime.now()  # type: ignore[name-defined]
        started_at = time.time()
        total = self.config.target_rps * self.config.duration_seconds
        interval = 1.0 / self.config.target_rps
        print(f"Planned requests: {total} interval={interval*1000:.2f}ms")
        tasks: List[asyncio.Task] = []
        for i in range(total):
            tasks.append(asyncio.create_task(self._scheduled(i * interval)))
        monitor = asyncio.create_task(self._monitor(started_at))
        await asyncio.gather(*tasks, return_exceptions=True)
        monitor.cancel()
        try:
            await monitor
        except asyncio.CancelledError:
            pass
        self.metrics.end_time = datetime.now()  # type: ignore[name-defined]
        self.metrics.finalize()
        return self.metrics

    async def cleanup(self):
        if self.session:
            await self.session.close()
