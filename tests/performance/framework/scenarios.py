from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Scenario:
    name: str
    rates: List[int]
    concurrency: Dict[int, int]
    strict: bool = True  # whether failures should fail the test by default


def _default_concurrency_for(rate: int) -> int:
    # Aim ~10 req/s per worker; cap to keep httpx pool reasonable
    return max(10, min(200, rate // 10 or 10))


def get_scenario(mode: str, fallback_rates: List[int]) -> Scenario:
    mode = (mode or "baseline").lower()
    if mode in ("baseline", "base"):
        rates = fallback_rates or [50, 100]
        conc = {r: _default_concurrency_for(r) for r in rates}
        return Scenario(name="baseline", rates=rates, concurrency=conc, strict=True)

    if mode in ("step-up", "stepup", "ramp", "ramp-up"):
        # Ambitious but reasonable defaults; can be overridden via PERF_RATES
        rates_env = os.getenv("PERF_RATES")
        if rates_env:
            rates = [int(x.strip()) for x in rates_env.split(",") if x.strip()]
        else:
            rates = [100, 200, 400, 800]
        conc = {r: _default_concurrency_for(r) for r in rates}
        # Step-up is exploratory by default; can be made strict via PERF_STRICT
        return Scenario(name="step-up", rates=rates, concurrency=conc, strict=False)

    # Fallback: treat unknown as baseline with provided rates
    conc = {r: _default_concurrency_for(r) for r in fallback_rates}
    return Scenario(
        name="baseline", rates=fallback_rates, concurrency=conc, strict=True
    )
