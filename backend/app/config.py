import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_configured_data_dir = os.getenv("DATA_DIR")
DATA_DIR = Path(_configured_data_dir) if _configured_data_dir else BASE_DIR / "data"
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR / DATA_DIR
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "09:30")  # Europe/London, on D-1
MAX_HORIZON_HOURS = int(os.getenv("MAX_HORIZON_HOURS", "72"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
TZ = "Europe/London"

ACTUALS_FILE = DATA_DIR / "actuals.csv.gz"
FORECASTS_FILE = DATA_DIR / "forecasts.csv.gz"
