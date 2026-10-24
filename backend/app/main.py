from datetime import date
import logging

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import metrics, pipeline, store
from .config import CORS_ORIGINS, DEFAULT_CUTOFF, TZ

logger = logging.getLogger(__name__)
app = FastAPI(title="UK Wind Forecast Accuracy API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["GET"], allow_headers=["*"])

DEFAULT_START, DEFAULT_END = "2026-01-01", "2026-01-31"


@app.on_event("startup")
def log_data_paths():
    logger.info(
        "Configured data directory: %s (actuals exists=%s, forecasts exists=%s)",
        store.config.DATA_DIR,
        store.config.ACTUALS_FILE.is_file(),
        store.config.FORECASTS_FILE.is_file(),
    )


def _clean(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(pd.notnull(df), None).to_dict("records")


def _iso(ts):
    return None if ts is None or pd.isna(ts) else ts.isoformat()


def _validate(start: str, end: str, cutoff: str):
    try:
        date.fromisoformat(start)
        date.fromisoformat(end)
        pipeline.parse_cutoff(cutoff)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if start > end:
        raise HTTPException(422, "start must be <= end")


def _load():
    try:
        return store.load()
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    actuals, fc = _load()
    return {
        "timezone": TZ,
        "default_cutoff": DEFAULT_CUTOFF,
        "default_range": {"start": DEFAULT_START, "end": DEFAULT_END},
        "actuals": {"rows": len(actuals), "from": _iso(actuals.startTime.min()),
                    "to": _iso(actuals.startTime.max())},
        "forecasts": {"rows": len(fc), "published_from": _iso(fc.publishTime.min()),
                      "published_to": _iso(fc.publishTime.max())},
        "units": "MW",
        "error_definition": "forecast - actual (positive = over-forecast)",
    }


@app.get("/api/forecast")
def forecast_for_day(
    day: str = Query(..., alias="date", description="Delivery date YYYY-MM-DD (Europe/London)"),
    cutoff: str = Query(DEFAULT_CUTOFF, description="D-1 decision cutoff HH:MM London"),
):
    """The forecast available at decision time for delivery day D, with actuals if known.
    Points are on the union of forecast (hourly) and actual (30-min) timestamps."""
    _validate(day, day, cutoff)
    actuals, fc = _load()
    sel, grid = pipeline.day_view(fc, actuals, cutoff, day)
    if sel.empty:
        raise HTTPException(404, f"No forecast available for {day} at cutoff {cutoff} on D-1")

    # Expected-actual band from the pilot-month error distribution (in-sample, indicative):
    # actual = forecast - error, so P10/P90 of actual = forecast - P90/P10 of error.
    ref = metrics.summarize(pipeline.decision_dataset(fc, actuals, cutoff, DEFAULT_START, DEFAULT_END))
    if ref["n"]:
        grid["band_low"] = (grid["forecast"] - ref["p90_error"]).clip(lower=0)
        grid["band_high"] = grid["forecast"] - ref["p10_error"]
    else:
        grid["band_low"] = grid["band_high"] = None

    h, mi = pipeline.parse_cutoff(cutoff)
    decision_utc = (pd.Timestamp(day) - pd.Timedelta(days=1)
                    + pd.Timedelta(hours=h, minutes=mi)).tz_localize(TZ).tz_convert("UTC")
    pts = grid[["startTime", "forecast", "actual", "error", "band_low", "band_high",
                "publishTime", "horizon_h"]].copy()
    pts["startTime"] = pts["startTime"].map(_iso)
    pts["publishTime"] = pts["publishTime"].map(_iso)
    return {
        "date": day, "cutoff": cutoff,
        "decision_time_utc": _iso(decision_utc),
        "forecast_published_from": _iso(sel.publishTime.min()),
        "forecast_published_to": _iso(sel.publishTime.max()),
        "forecast_resolution_note": "WINDFOR is hourly; actuals are 30-min. Forecast is null at :30.",
        "summary": {"mean_forecast": float(sel.forecast.mean()),
                    "min_forecast": float(sel.forecast.min()),
                    "max_forecast": float(sel.forecast.max())},
        "accuracy": metrics.summarize(grid),
        "points": _clean(pts),
    }


@app.get("/api/accuracy")
def accuracy(start: str = DEFAULT_START, end: str = DEFAULT_END, cutoff: str = DEFAULT_CUTOFF):
    _validate(start, end, cutoff)
    actuals, fc = _load()
    df = pipeline.decision_dataset(fc, actuals, cutoff, start, end)
    return {"start": start, "end": end, "cutoff": cutoff,
            "overall": metrics.summarize(df), "daily": metrics.daily(df)}


@app.get("/api/accuracy/horizon")
def accuracy_by_horizon(start: str = DEFAULT_START, end: str = DEFAULT_END,
                        bucket_hours: int = Query(6, ge=1, le=48)):
    """Error vs forecast lead time, across ALL published forecasts (not only the D-1 one)."""
    _validate(start, end, DEFAULT_CUTOFF)
    actuals, fc = _load()
    df = pipeline.filter_dates(pipeline.join_actuals(pipeline.add_local_date(fc), actuals),
                               start, end)
    return {"start": start, "end": end, "bucket_hours": bucket_hours,
            "buckets": metrics.by_horizon(df, bucket_hours)}