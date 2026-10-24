from functools import lru_cache

import pandas as pd

from . import config


@lru_cache(maxsize=1)
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    a_path, f_path = config.ACTUALS_FILE, config.FORECASTS_FILE
    if not a_path.exists() or not f_path.exists():
        raise FileNotFoundError(
            "Data files missing. Run `python -m scripts.ingest` (or add --synthetic).")
    actuals = pd.read_csv(a_path)
    fc = pd.read_csv(f_path)
    actuals["startTime"] = pd.to_datetime(actuals["startTime"], utc=True)
    fc["startTime"] = pd.to_datetime(fc["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    return actuals, fc
