import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "09:30")  # Europe/London, on D-1
MAX_HORIZON_HOURS = int(os.getenv("MAX_HORIZON_HOURS", "72"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
TZ = "Europe/London"

ACTUALS_FILE = DATA_DIR / "actuals.csv.gz"
FORECASTS_FILE = DATA_DIR / "forecasts.csv.gz"
