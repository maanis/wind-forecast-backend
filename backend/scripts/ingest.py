"""Download Jan-2026 wind actuals + forecasts from Elexon and cache as compressed CSV.

  python -m scripts.ingest                 # real data (needs internet)
  python -m scripts.ingest --synthetic     # offline demo data (NOT real)
"""
import argparse
from datetime import date

import numpy as np
import pandas as pd

from app import config

TARGET_START, TARGET_END = date(2026, 1, 1), date(2026, 1, 31)
PUBLISH_START = date(2025, 12, 25)  # margin so Jan 1 has D-1 forecasts


def synthetic():
    """Offline demo data with error growing with lead time. Not real."""
    rng = np.random.default_rng(42)
    idx = pd.date_range("2026-01-01", "2026-02-01", freq="30min", tz="UTC", inclusive="left")
    full = pd.date_range("2025-12-25", "2026-02-02", freq="30min", tz="UTC", inclusive="left")

    def shape(ix):
        t = (ix - pd.Timestamp("2025-12-25", tz="UTC")).total_seconds().to_numpy() / 1800
        return np.clip(7000 + 4500 * np.sin(t / 90) + 1500 * np.sin(t / 17), 0, 14000)

    truth = np.clip(shape(idx) + rng.normal(0, 400, len(idx)), 0, 14000)
    actuals = pd.DataFrame({"startTime": idx, "generation": truth.round(0)})
    base = shape(full)
    rows = []
    for p in pd.date_range("2025-12-25", "2026-01-31", freq="1h", tz="UTC"):
        h = (full - p).total_seconds().to_numpy() / 3600
        m = (h >= 0) & (h <= config.MAX_HORIZON_HOURS)
        noise = rng.normal(0, 150 + 25 * h[m])
        rows.append(pd.DataFrame({"startTime": full[m], "publishTime": p,
                                  "generation": np.clip(base[m] + noise - 100, 0, 14000).round(0)}))
    return actuals, pd.concat(rows, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args()
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if args.synthetic:
        actuals, fc = synthetic()
    else:
        from app import elexon
        print("Fetching actuals (FUELHH)...")
        actuals = elexon.fetch_actuals(TARGET_START, TARGET_END)
        print("Fetching forecasts (WINDFOR)... can take a few minutes")
        fc = elexon.fetch_forecasts(PUBLISH_START, TARGET_END)
        h = (fc["startTime"] - fc["publishTime"]).dt.total_seconds() / 3600
        fc = fc[(h >= 0) & (h <= config.MAX_HORIZON_HOURS)]  # smaller file
    actuals.to_csv(config.ACTUALS_FILE, index=False, compression="gzip")
    fc.to_csv(config.FORECASTS_FILE, index=False, compression="gzip")
    print(f"actuals: {len(actuals)} rows -> {config.ACTUALS_FILE}")
    print(f"forecasts: {len(fc)} rows -> {config.FORECASTS_FILE}")


if __name__ == "__main__":
    main()
