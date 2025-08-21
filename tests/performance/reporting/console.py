from __future__ import annotations

from core.config import TestConfig
from core.metrics import Metrics


def print_summary(metrics: Metrics, config: TestConfig) -> None:
    print("\n" + "=" * 80)
    print("PERFORMANCE TEST RESULTS")
    print("=" * 80)

    print("\nCONFIG")
    print(f"  Target RPS: {config.target_rps}")
    print(f"  Duration: {config.duration_seconds}s")
    print(f"  Max Connections: {config.max_concurrent_connections}")

    print("\nTHROUGHPUT")
    print(f"  Actual RPS: {metrics.actual_rps:.1f}")
    print(f"  Peak RPS: {metrics.peak_rps:.1f}")
    print(f"  Total: {metrics.total_requests}")
    print(f"  Success: {metrics.successful_requests}")
    print(f"  Failed: {metrics.failed_requests}")
    success_rate = metrics.successful_requests / max(metrics.total_requests, 1) * 100
    print(f"  Success Rate: {success_rate:.2f}%")

    if metrics.response_times:
        print("\nLATENCY (ms)")
        print(f"  min={metrics.min_latency:.1f}")
        print(f"  avg={metrics.avg_latency:.1f}")
        print(f"  p50={metrics.p50_latency:.1f}")
        print(f"  p95={metrics.p95_latency:.1f}")
        print(f"  p99={metrics.p99_latency:.1f}")
        print(f"  max={metrics.max_latency:.1f}")
