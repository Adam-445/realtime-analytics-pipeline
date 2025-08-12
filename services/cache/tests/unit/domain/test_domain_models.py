from src.domain.models import MetricsWindow, OverviewSnapshot


def test_metrics_window_and_overview_models():
    mw = MetricsWindow(window_start=1234567890, data={"a": 1, "b": 2})
    assert mw.window_start == 1234567890
    assert mw.data["a"] == 1

    ov = OverviewSnapshot(event_latest=mw.model_dump(), performance_latest={"p": 3})
    assert "event_latest" in ov.model_dump()
    assert ov.performance_latest["p"] == 3
