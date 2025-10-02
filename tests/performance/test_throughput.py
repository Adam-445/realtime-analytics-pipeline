import os
from typing import List

import pytest
from performance.load_test import run_single_test


def _parse_rates(value: str | None) -> List[int]:
    if not value:
        return [50]  # safe default for local smoke
    rates: List[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            rates.append(int(part))
        except ValueError:
            raise AssertionError(f"Invalid PERF_RATES item: {part}")
    assert rates, "No valid rates provided"
    return rates


@pytest.mark.performance
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target_rps",
    _parse_rates(os.getenv("PERF_RATES")),
)
async def test_throughput(target_rps: int):
    duration = int(os.getenv("PERF_DURATION", "20"))
    strict = os.getenv("PERF_STRICT", "false").lower() in {"1", "true", "yes"}
    max_error_rate = float(os.getenv("PERF_MAX_ERROR_RATE", "5.0"))

    metrics = await run_single_test(target_rps, duration)

    # Always print summary to stdout; assertions gated by strict mode or env threshold
    # Basic sanity: some requests should succeed unless target is unreachable
    assert metrics.total_requests > 0

    # Optional strict checks suitable for CI/regressions
    if strict:
        assert (
            metrics.error_rate <= max_error_rate
        ), f"Error rate too high: {metrics.error_rate:.2f}% > {max_error_rate:.2f}%"
        assert (
            metrics.actual_rps >= target_rps * 0.7
        ), f"Actual RPS too low: {metrics.actual_rps:.1f} < 70% of target {target_rps}"
