import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def resolve_data_dir(configured_data_dir: str | None) -> Path:
    if not configured_data_dir:
        return BASE_DIR / "data"
    data_dir = Path(configured_data_dir)
    if data_dir.is_absolute():
        return data_dir
    if data_dir.parts[:1] in ((BASE_DIR.name,), ("backend",)):
        data_dir = Path(*data_dir.parts[1:])
    return BASE_DIR / data_dir


DATA_DIR = resolve_data_dir(os.getenv("DATA_DIR"))
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "09:30")  # Europe/London, on D-1
MAX_HORIZON_HOURS = int(os.getenv("MAX_HORIZON_HOURS", "72"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
TZ = "Europe/London"

ACTUALS_FILE = DATA_DIR / "actuals.csv.gz"
FORECASTS_FILE = DATA_DIR / "forecasts.csv.gz"
