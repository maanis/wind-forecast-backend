"""Core logic: choose the forecast a buyer actually had at decision time, join to actuals."""
import pandas as pd

from .config import TZ


def parse_cutoff(cutoff: str) -> tuple[int, int]:
    try:
        h, m = cutoff.split(":")
        h, m = int(h), int(m)
        assert 0 <= h < 24 and 0 <= m < 60
        return h, m
    except Exception:
        raise ValueError(f"cutoff must be HH:MM, got {cutoff!r}")


def add_local_date(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["target_date"] = df["startTime"].dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    return df


def latest_before_cutoff(fc: pd.DataFrame, cutoff: str) -> pd.DataFrame:
    """For each target half-hour on day D (Europe/London), keep the most recent forecast
    published at or before (D-1) at `cutoff` London time -- i.e. what the day-ahead
    buyer could see. Rows with no such forecast are dropped."""
    h, m = parse_cutoff(cutoff)
    fc = add_local_date(fc)
    if fc.empty:
        return fc
    cutoff_local = fc["target_date"] - pd.Timedelta(days=1) + pd.Timedelta(hours=h, minutes=m)
    cutoff_utc = cutoff_local.dt.tz_localize(TZ, ambiguous=False,
                                             nonexistent="shift_forward").dt.tz_convert("UTC")
    ok = fc[fc["publishTime"] <= cutoff_utc]
    return (ok.sort_values(["startTime", "publishTime"])
              .drop_duplicates("startTime", keep="last")
              .reset_index(drop=True))


def join_actuals(fc: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    out = fc.merge(actuals.rename(columns={"generation": "actual"}), on="startTime", how="left")
    out = out.rename(columns={"generation": "forecast"})
    out["error"] = out["forecast"] - out["actual"]  # +ve = over-forecast
    out["horizon_h"] = (out["startTime"] - out["publishTime"]).dt.total_seconds() / 3600
    return out


def filter_dates(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    return df[(df["target_date"] >= s) & (df["target_date"] <= e)]


def decision_dataset(fc, actuals, cutoff: str, start: str, end: str) -> pd.DataFrame:
    sel = latest_before_cutoff(fc, cutoff)
    return filter_dates(join_actuals(sel, actuals), start, end)


def day_view(fc, actuals, cutoff: str, day: str):
    """Decision-time forecast for one delivery day on the union of forecast and actual
    timestamps. WINDFOR is hourly while FUELHH is 30-min, so forecast is null at :30."""
    sel = decision_dataset(fc, actuals, cutoff, day, day)
    a = filter_dates(add_local_date(actuals), day, day)[["startTime", "generation"]]
    a = a.rename(columns={"generation": "actual_a"})
    grid = sel.merge(a, on="startTime", how="outer").sort_values("startTime")
    grid["actual"] = grid["actual"].fillna(grid["actual_a"])
    grid["error"] = grid["forecast"] - grid["actual"]
    return sel, grid.drop(columns=["actual_a"]).reset_index(drop=True)