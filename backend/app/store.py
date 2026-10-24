from functools import lru_cache
import logging

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    a_path, f_path = config.ACTUALS_FILE, config.FORECASTS_FILE
    logger.info(
        "Loading forecast data from %s (actuals exists=%s, forecasts exists=%s)",
        config.DATA_DIR,
        a_path.is_file(),
        f_path.is_file(),
    )
    if not a_path.exists() or not f_path.exists():
        logger.error(
            "Forecast data files missing: actuals=%s, forecasts=%s",
            a_path,
            f_path,
        )
        raise FileNotFoundError(
            "Data files missing. Run `python -m scripts.ingest` (or add --synthetic).")
    actuals = pd.read_csv(a_path)
    fc = pd.read_csv(f_path)
    actuals["startTime"] = pd.to_datetime(actuals["startTime"], utc=True)
    fc["startTime"] = pd.to_datetime(fc["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    return actuals, fc
