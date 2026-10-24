"""Thin client for the Elexon BMRS API (FUELHH actuals, WINDFOR forecasts)."""
import time
from datetime import date, datetime, timedelta

import pandas as pd
import requests

BASE = "https://data.elexon.co.uk/bmrs/api/v1"


def _get(path: str, params: dict, retries: int = 4) -> list[dict]:
    last = None
    for i in range(retries):
        try:
            r = requests.get(f"{BASE}{path}", params=params, timeout=60,
                             headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else data.get("data", [])
        except requests.RequestException as e:  # retry with backoff
            last = e
            time.sleep(2 ** i)
    raise RuntimeError(f"Elexon request failed: {path} {params}: {last}")


def _chunks(start: date, end: date, days: int):
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=days - 1), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def fetch_actuals(start: date, end: date) -> pd.DataFrame:
    """National WIND outturn, 30-min. Dates are settlement dates (inclusive)."""
    rows: list[dict] = []
    for a, b in _chunks(start, end, 7):
        rows += _get("/datasets/FUELHH/stream", {
            "settlementDateFrom": a.isoformat(),
            "settlementDateTo": b.isoformat(),
            "fuelType": "WIND",
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["startTime", "generation"])
    df = df[df["fuelType"] == "WIND"].copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return (df[["startTime", "generation"]]
            .drop_duplicates("startTime", keep="last")
            .sort_values("startTime").reset_index(drop=True))


def fetch_forecasts(pub_start: date, pub_end: date) -> pd.DataFrame:
    """All WINDFOR forecasts published in [pub_start, pub_end] (inclusive)."""
    rows: list[dict] = []
    for a, b in _chunks(pub_start, pub_end, 1):
        frm = datetime.combine(a, datetime.min.time()).strftime("%Y-%m-%dT%H:%MZ")
        to = datetime.combine(b + timedelta(days=1), datetime.min.time()).strftime("%Y-%m-%dT%H:%MZ")
        rows += _get("/datasets/WINDFOR/stream",
                     {"publishDateTimeFrom": frm, "publishDateTimeTo": to})
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["startTime", "publishTime", "generation"])
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    return (df[["startTime", "publishTime", "generation"]]
            .drop_duplicates(["startTime", "publishTime"], keep="last")
            .sort_values(["startTime", "publishTime"]).reset_index(drop=True))
