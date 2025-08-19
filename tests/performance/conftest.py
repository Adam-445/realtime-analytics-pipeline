import os
import time

import pytest
from clickhouse_driver import Client
from performance.framework.reporting import PerfReporter

# ClickHouse connection defaults (match e2e config)
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "analytics")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "admin")
CLICKHOUSE_PASS = os.getenv("CLICKHOUSE_PASS", "admin")


@pytest.fixture(scope="session")
def clickhouse_client():
    """ClickHouse client for performance tests."""
    client = Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASS,
        database=CLICKHOUSE_DB,
    )
    try:
        client.execute("SELECT 1")
    except Exception as e:
        pytest.exit(
            f"Cannot connect to ClickHouse at {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}: {e}"
        )
    yield client
    client.disconnect()


@pytest.fixture(scope="function", autouse=True)
def clean_tables(clickhouse_client: Client):
    """Ensure target tables are empty before each performance test."""
    for tbl in ("event_metrics", "session_metrics", "performance_metrics"):
        clickhouse_client.execute(f"TRUNCATE TABLE IF EXISTS {tbl}")
    # small pause to let downstream stabilize
    time.sleep(1)


@pytest.fixture(scope="session")
def test_config() -> dict:
    """Shared test configuration sourced from env with sensible defaults."""
    return {
        "processing_session_gap_seconds": int(
            os.getenv("PROCESSING_SESSION_GAP_SECONDS", "1800")
        ),
        "processing_metrics_window_size_seconds": int(
            os.getenv("PROCESSING_METRICS_WINDOW_SIZE_SECONDS", "60")
        ),
        "processing_performance_window_size_seconds": int(
            os.getenv("PROCESSING_PERFORMANCE_WINDOW_SIZE_SECONDS", "300")
        ),
        "flink_watermark_delay_seconds": int(
            os.getenv("FLINK_WATERMARK_DELAY_SECONDS", "10")
        ),
        "max_wait_time": int(os.getenv("TEST_MAX_WAIT_TIME", "60")),
        "poll_interval": float(os.getenv("TEST_POLL_INTERVAL", "2")),
    }


@pytest.fixture(scope="session")
def perf_config() -> dict:
    """Performance-specific configuration (rates/durations), override via env."""
    # Allow comma-separated rates via env PERF_RATES, e.g., "100,500,1000"
    rates_env = os.getenv("PERF_RATES")
    if rates_env:
        event_rates = [int(x.strip()) for x in rates_env.split(",") if x.strip()]
    else:
        # Default to a moderate, reliable rate; higher rates can
        # be passed via PERF_RATES
        event_rates = [100]

    return {
        "event_rates": event_rates,
        "test_duration": int(os.getenv("PERF_DURATION", "30")),
        "warmup_period": int(os.getenv("PERF_WARMUP", "5")),
        "prometheus_url": os.getenv("PROMETHEUS_URL", "http://prometheus:9090"),
    }


def pytest_configure(config):
    config.addinivalue_line("markers", "perf: mark test as performance test")


@pytest.fixture(scope="session")
def perf_report():
    out_dir = os.environ.get("PERF_RESULTS_DIR", "/app/perf-results")
    # Use a default event type that is allowed by processing filters unless overridden
    # This avoids dropping perf traffic due to disallowed event types.
    os.environ.setdefault("PERF_EVENT_TYPE", "page_view")
    reporter = PerfReporter(out_dir)
    # Optionally start system metrics sampling for richer reports
    try:
        if os.environ.get("PERF_SYS_METRICS", "1") not in ("0", "false", "False"):
            reporter.start_system_metrics()
    except Exception:
        pass
    # Optionally load a baseline file for comparison in summary
    baseline_file = os.environ.get("PERF_BASELINE_FILE")
    if baseline_file and os.path.exists(baseline_file):
        reporter.load_baseline(baseline_file)
    yield reporter
    try:
        reporter.stop_system_metrics()
    except Exception:
        pass
    reporter.flush()
