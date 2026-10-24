import pandas as pd
import pytest

from app import metrics, pipeline


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make_fc():
    # target 2026-01-10 12:00 UTC; three forecasts; default cutoff 09:30 on Jan 9
    return pd.DataFrame({
        "startTime": [ts("2026-01-10 12:00")] * 3,
        "publishTime": [ts("2026-01-09 08:00"), ts("2026-01-09 09:00"), ts("2026-01-09 10:00")],
        "generation": [100.0, 200.0, 999.0],
    })


def test_picks_latest_before_cutoff_and_ignores_later():
    sel = pipeline.latest_before_cutoff(make_fc(), "09:30")
    assert len(sel) == 1 and sel.generation.iloc[0] == 200.0


def test_cutoff_is_configurable():
    assert pipeline.latest_before_cutoff(make_fc(), "10:30").generation.iloc[0] == 999.0


def test_no_forecast_before_cutoff_drops_row():
    assert pipeline.latest_before_cutoff(make_fc(), "07:00").empty


def test_bad_cutoff():
    with pytest.raises(ValueError):
        pipeline.parse_cutoff("25:99")


def test_error_sign_and_metrics():
    sel = pipeline.latest_before_cutoff(make_fc(), "09:30")
    act = pd.DataFrame({"startTime": [ts("2026-01-10 12:00")], "generation": [150.0]})
    df = pipeline.join_actuals(sel, act)
    assert df.error.iloc[0] == 50.0  # over-forecast
    m = metrics.summarize(df)
    assert m["mae"] == 50 and m["bias"] == 50 and m["n"] == 1


def test_missing_actual_excluded_from_metrics():
    sel = pipeline.latest_before_cutoff(make_fc(), "09:30")
    act = pd.DataFrame({"startTime": pd.to_datetime([], utc=True), "generation": []})
    df = pipeline.join_actuals(sel, act)
    assert metrics.summarize(df)["n"] == 0


def test_day_view_hourly_forecast_halfhourly_actuals():
    fc = pd.DataFrame({
        "startTime": [ts("2026-01-10 12:00"), ts("2026-01-10 13:00")],
        "publishTime": [ts("2026-01-09 08:00")] * 2,
        "generation": [100.0, 110.0],
    })
    act = pd.DataFrame({
        "startTime": [ts("2026-01-10 12:00"), ts("2026-01-10 12:30"), ts("2026-01-10 13:00")],
        "generation": [90.0, 95.0, 120.0],
    })
    sel, grid = pipeline.day_view(fc, act, "09:30", "2026-01-10")
    assert len(sel) == 2 and len(grid) == 3
    assert grid.forecast.isna().tolist() == [False, True, False]
    assert grid.actual.tolist() == [90.0, 95.0, 120.0]
    assert metrics.summarize(grid)["n"] == 2  # only matched points scored