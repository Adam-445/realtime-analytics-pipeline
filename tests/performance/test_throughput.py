import asyncio
import csv
import os
import time

import pytest
from performance.framework.loadgen import send_events_at_rate
from performance.framework.reporting import PerfReporter
from performance.framework.scenarios import get_scenario
from utils.clickhouse.metrics import (
    get_event_metrics_total,
    settle_after_windows,
    wait_for_processed_delta,
)


def _save_result(row: dict):
    out_dir = os.environ.get("PERF_RESULTS_DIR", "/app/perf-results")
    try:
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "throughput_results.csv")
        file_exists = os.path.exists(out_file)
        with open(out_file, "a", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "target_rate",
                    "actual_send_rate",
                    "sent",
                    "processed",
                    "success_rate",
                ],
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception:
        # Non-fatal if writing fails
        pass


@pytest.mark.perf
def test_ingestion_throughput(
    clickhouse_client,
    test_config,
    perf_config,
    perf_report: PerfReporter,
):
    """Send events at multiple rates and validate success rate in ClickHouse."""
    # Determine scenario and gating behavior
    mode = os.environ.get("PERF_MODE", os.environ.get("PERF_SCENARIO", "baseline"))
    scenario = get_scenario(mode, perf_config["event_rates"])
    # Allow override to force strict gating on all rates
    strict_override = os.environ.get("PERF_STRICT")
    if strict_override is not None:
        scenario.strict = str(strict_override).lower() in ("1", "true", "yes")

    for rate in scenario.rates:
        duration = perf_config["test_duration"]

        # Establish baseline before sending anything in this rate run
        baseline_total = get_event_metrics_total(clickhouse_client)

        # Concurrency from scenario with optional override
        conc_env = os.environ.get("PERF_CONCURRENCY")
        if conc_env and conc_env.isdigit():
            concurrency = int(conc_env)
        else:
            concurrency = scenario.concurrency.get(rate)

        start_time = time.time()
        sent_count = asyncio.run(
            send_events_at_rate(rate=rate, duration=duration, concurrency=concurrency)
        )
        end_time = time.time()

        # Wait for windows to complete and data to land in ClickHouse
        settle_after_windows(
            metrics_window_seconds=test_config[
                "processing_metrics_window_size_seconds"
            ],
            watermark_delay_seconds=test_config["flink_watermark_delay_seconds"],
            extra_seconds=2,
        )

        actual_rate = (
            sent_count / (end_time - start_time) if end_time > start_time else 0
        )
        # Gates (tunable)
        rate_factor_env = os.environ.get("PERF_RATE_FACTOR")
        try:
            rate_factor = float(rate_factor_env) if rate_factor_env else 0.8
        except ValueError:
            rate_factor = 0.8
        # Be more lenient for higher target rates where HTTP overhead is higher
        if rate >= 800:
            rate_factor = min(rate_factor, 0.65)
        elif rate >= 500:
            rate_factor = min(rate_factor, 0.60)
        elif rate >= 400:
            rate_factor = min(rate_factor, 0.70)

        success_min_env = os.environ.get("PERF_SUCCESS_MIN")
        try:
            success_min = float(success_min_env) if success_min_env else 0.90
        except ValueError:
            success_min = 0.90

        # Poll until delta reaches threshold of sent_count (based on success_min)
        processed_total = wait_for_processed_delta(
            clickhouse_client,
            baseline_total=baseline_total,
            target_delta=int(success_min * sent_count),
            timeout=test_config["max_wait_time"],
            poll_interval=test_config["poll_interval"],
        )

        success_rate = processed_total / sent_count if sent_count else 0.0

        print(
            {
                "target_rate": rate,
                "actual_send_rate": actual_rate,
                "sent": sent_count,
                "processed": processed_total,
                "success_rate": success_rate,
            }
        )

        _save_result(
            {
                "target_rate": rate,
                "actual_send_rate": actual_rate,
                "sent": sent_count,
                "processed": processed_total,
                "success_rate": success_rate,
            }
        )

        # Basic expectations (tunable)
        rate_ok = actual_rate >= rate_factor * rate
        success_ok = success_rate >= success_min

        # Report
        perf_report.add_throughput(
            target_rate=rate,
            actual_send_rate=actual_rate,
            sent=sent_count,
            processed=processed_total,
            success_rate=success_rate,
            thresholds={
                "rate_factor": rate_factor,
                "success_min": success_min,
            },
            passed=bool(rate_ok and success_ok),
            variant="single",
        )

        # Assertions: baseline/scenario.strict gates; step-up is exploratory by default
        if scenario.strict:
            assert rate_ok
            assert success_ok
    # No batched variant: real clients send single events; batch path removed
