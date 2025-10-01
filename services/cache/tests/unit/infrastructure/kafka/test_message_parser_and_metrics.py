import contextlib

import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
from src.infrastructure.kafka.message_parser import parse_message


@contextlib.contextmanager
def isolated_registry():
    reg = CollectorRegistry()
    yield reg


def test_isolated_registry_usage():
    with isolated_registry() as reg:
        c = Counter("demo_total", "demo", registry=reg)
        g = Gauge("demo_gauge", "demo", registry=reg)
        h = Histogram("demo_latency_seconds", "demo", registry=reg)

        c.inc()
        g.set(3)
        with h.time():
            pass

        samples = {s.name: s.value for m in reg.collect() for s in m.samples}
        assert samples.get("demo_total", 0) == 1
        assert any(n.startswith("demo_gauge") for n in samples.keys())
        assert samples.get("demo_latency_seconds_count", 0) == 1


def test_parse_event_metrics_basic():
    op = parse_message(
        "event_metrics",
        {
            "window_start": 1710000000000,
            "event_type": "click",
            "event_count": 5,
            "user_count": 3,
        },
    )
    assert op is not None
    assert op["type"] == "event"
    assert op["window_start"] == 1710000000000
    assert op["fields"] == {"click.count": 5, "click.users": 3}


def test_parse_performance_metrics_basic():
    op = parse_message(
        "performance_metrics",
        {
            "window_start": 1710000000000,
            "device_category": "mobile",
            "avg_load_time": 1.23,
            "p95_load_time": 2.34,
        },
    )
    assert op is not None
    assert op["type"] == "perf"
    assert op["fields"]["mobile.avg_load_time"] == pytest.approx(1.23)
    assert op["fields"]["mobile.p95_load_time"] == pytest.approx(2.34)


def test_parse_ignores_session_metrics():
    assert parse_message("session_metrics", {"window_start": 1}) is None


def test_parse_handles_missing_fields():
    assert (
        parse_message("event_metrics", {"window_start": 1000, "event_count": 1}) is None
    )
    assert (
        parse_message(
            "performance_metrics", {"window_start": 1000, "avg_load_time": 1.0}
        )
        is None
    )


def test_parse_unhandled_topic_warns(caplog):
    caplog.set_level("WARNING")
    assert parse_message("unknown_topic", {}) is None
    assert any("unhandled_topic" in r.message for r in caplog.records)


def test_parse_accepts_iso_timestamp():
    op = parse_message(
        "event_metrics",
        {
            "window_start": "2025-01-01T00:00:00Z",
            "event_type": "click",
            "event_count": 1,
            "user_count": 1,
        },
    )
    assert op is not None
    assert isinstance(op["window_start"], int)


def test_parse_bad_timestamp_warns_and_returns_none(caplog):
    caplog.set_level("WARNING")
    assert (
        parse_message("event_metrics", {"window_start": "not-a-ts", "event_type": "x"})
        is None
    )
    assert any("invalid_window_start" in r.message for r in caplog.records)
