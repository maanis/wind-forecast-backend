
from pathlib import Path
import pandas as pd

DATA = Path("data")
actuals = pd.read_csv(DATA / "actuals.csv.gz")
forecasts = pd.read_csv(DATA / "forecasts.csv.gz")

print("\n=== 1. ACTUALS ===")
print("Rows:", len(actuals))
print("Columns:", actuals.columns.tolist())

# Expected 48 half-hour intervals per day for January 2026.
expected = pd.date_range(
    "2026-01-01 00:00",
    "2026-02-01 00:00",
    freq="30min",
    inclusive="left",
    tz="UTC",
)

actuals["startTime"] = pd.to_datetime(
    actuals["startTime"], utc=True, errors="coerce"
)

print("Invalid timestamps:", actuals["startTime"].isna().sum())

actual_times = actuals["startTime"].dropna()
print("Duplicate startTime rows:", actual_times.duplicated().sum())

actual_jan = actuals[
    actuals["startTime"].ge(pd.Timestamp("2026-01-01", tz="UTC"))
    & actuals["startTime"].lt(pd.Timestamp("2026-02-01", tz="UTC"))
]

present = set(actual_jan["startTime"].dropna())
missing = [t for t in expected if t not in present]

print("January rows:", len(actual_jan))
print("Unique January intervals:", len(present))
print("Missing intervals:", len(missing))
if missing:
    print("First missing intervals:", missing[:10])

print("\n=== 2. FORECASTS ===")
print("Rows:", len(forecasts))
print("Columns:", forecasts.columns.tolist())

forecasts["startTime"] = pd.to_datetime(
    forecasts["startTime"], utc=True, errors="coerce"
)
forecasts["publishTime"] = pd.to_datetime(
    forecasts["publishTime"], utc=True, errors="coerce"
)

print("Invalid target timestamps:", forecasts["startTime"].isna().sum())
print("Invalid publication timestamps:", forecasts["publishTime"].isna().sum())

forecast_jan = forecasts[
    forecasts["startTime"].ge(pd.Timestamp("2026-01-01", tz="UTC"))
    & forecasts["startTime"].lt(pd.Timestamp("2026-02-01", tz="UTC"))
].copy()

print("January target rows:", len(forecast_jan))
print(
    "Unique target intervals:",
    forecast_jan["startTime"].nunique(),
)
print(
    "Unique publication timestamps:",
    forecast_jan["publishTime"].nunique(),
)
print(
    "Duplicate target + publication pairs:",
    forecast_jan.duplicated(["startTime", "publishTime"]).sum(),
)
print(
    "Earliest publication:",
    forecast_jan["publishTime"].min(),
)
print(
    "Latest publication:",
    forecast_jan["publishTime"].max(),
)

# For each delivery day, select forecasts published by
# 09:30 Europe/London on the previous day.
forecast_jan["delivery_date"] = (
    forecast_jan["startTime"].dt.date
)

forecast_jan["cutoff_utc"] = forecast_jan[
    "delivery_date"
].map(
    lambda day: pd.Timestamp(
        f"{day} 09:30",
        tz="Europe/London",
    ).tz_convert("UTC") - pd.Timedelta(days=1)
)

eligible = forecast_jan[
    forecast_jan["publishTime"].le(forecast_jan["cutoff_utc"])
].copy()

latest = (
    eligible.sort_values("publishTime")
    .drop_duplicates("startTime", keep="last")
)

print("\n=== 3. CUTOFF COVERAGE ===")
print("Eligible forecast rows:", len(eligible))
print("Intervals with an eligible forecast:", latest["startTime"].nunique())
print("January intervals:", len(expected))
print(
    "Intervals without eligible forecasts:",
    len(set(expected) - set(latest["startTime"])),
)

if not latest.empty:
    print("\nSample selected forecasts:")
    print(latest[["startTime", "publishTime", "generation"]].head(10))

print("\n=== 4. VALUE CHECKS ===")
if "generation" in actuals:
    print("Actual null generation:", actuals["generation"].isna().sum())
    print("Actual negative generation:", (actuals["generation"] < 0).sum())

if "generation" in forecasts:
    print("Forecast null generation:", forecasts["generation"].isna().sum())
    print("Forecast negative generation:", (forecasts["generation"] < 0).sum())
