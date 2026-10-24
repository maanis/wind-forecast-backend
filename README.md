# UK Wind Forecast Accuracy – Backend

API for a day-ahead power buying team: (1) the latest wind forecast available at decision time, (2) quantified forecast accuracy. National-level wind only, Elexon data (FUELHH actuals, WINDFOR forecasts), January 2026 delivery days.

> **AI disclosure:** this project was built with AI assistance (Claude by Anthropic) for code generation and design discussion; all code was reviewed and tested by the author.

## Key design decision
For delivery day **D** (Europe/London), the buyer decides on **D-1** before the day-ahead auction closes. For every half-hour on D we use the **most recent WINDFOR forecast published at or before D-1 at the cutoff time** (default `09:30` London, configurable via `cutoff` param / `DEFAULT_CUTOFF`). Forecasts published after the cutoff are never used, so accuracy numbers are not flattered by information the buyer did not have. *Verify the exact market gate time with the client; it is an assumption.*

Error = `forecast - actual` (MW); positive = over-forecast (the risky direction for a buyer: they under-procure).

## Structure
```
backend/
  app/
    main.py       FastAPI routes
    pipeline.py   decision-time forecast selection + join to actuals (core logic)
    metrics.py    MAE, RMSE, bias, wMAPE, error percentiles, per-day, per-horizon
    elexon.py     Elexon BMRS client (chunked, retrying)
    store.py      loads cached CSVs once
    config.py     env config
  scripts/ingest.py   downloads & caches data (or --synthetic)
  tests/              pytest: cutoff logic, metrics, API
  data/               actuals.csv.gz, forecasts.csv.gz (commit after ingest)
  api/index.py, vercel.json   Vercel entrypoint
  Dockerfile, requirements.txt
docker-compose.yml
```

## Run
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m scripts.ingest              # real Elexon data -> data/*.csv.gz
# python -m scripts.ingest --synthetic  # offline demo data (NOT real)

uvicorn app.main:app --reload         # http://localhost:8000/docs
pytest -q
```
Docker: `docker compose up --build` (ingest first so `backend/data` has files).

## Endpoints
| Route | Purpose |
|---|---|
| `GET /api/meta` | data coverage, defaults |
| `GET /api/forecast?date=2026-01-15&cutoff=09:30` | decision-time forecast for day D + actuals + accuracy |
| `GET /api/accuracy?start=&end=&cutoff=` | overall + daily metrics |
| `GET /api/accuracy/horizon?start=&end=&bucket_hours=6` | error vs forecast lead time |
| `GET /health` | liveness |

## Metrics
MAE, RMSE, bias, wMAPE (Σ|e|/Σactual; used instead of MAPE because wind is often near zero), P10/P50/P90 of signed error, P95 of absolute error.

## Deploy (Vercel)
Data is pre-ingested and committed, so the deployed app does not call Elexon at runtime. Set the Vercel project root to `backend/`. Live link: _TODO_

## Notes / limitations
- Data is cached to CSV rather than a DB: dataset is small and static for the pilot window.
- Forecasts with lead time > `MAX_HORIZON_HOURS` (72) are dropped at ingest to keep the file small.
- Missing actuals are excluded from metrics (not interpolated).
- No demand data (out of scope), so procurement need is expressed as forecast ± error band, not a MW purchase figure.
