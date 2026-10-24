import numpy as np
import pandas as pd

EMPTY = {"n": 0, "mae": None, "rmse": None, "bias": None, "wmape": None,
         "p10_error": None, "p50_error": None, "p90_error": None,
         "p95_abs_error": None, "mean_actual": None}


def summarize(df: pd.DataFrame) -> dict:
    """Error metrics on rows that have both forecast and actual. error = forecast - actual."""
    d = df.dropna(subset=["forecast", "actual"])
    if len(d) == 0:
        return dict(EMPTY)
    e = d["error"].to_numpy(dtype=float)
    a = d["actual"].to_numpy(dtype=float)
    tot = a.sum()
    return {
        "n": int(len(d)),
        "mae": float(np.abs(e).mean()),
        "rmse": float(np.sqrt((e ** 2).mean())),
        "bias": float(e.mean()),
        # weighted MAPE: robust where actual ~ 0 (plain MAPE is not)
        "wmape": float(np.abs(e).sum() / tot) if tot > 0 else None,
        "p10_error": float(np.percentile(e, 10)),
        "p50_error": float(np.percentile(e, 50)),
        "p90_error": float(np.percentile(e, 90)),
        "p95_abs_error": float(np.percentile(np.abs(e), 95)),
        "mean_actual": float(a.mean()),
    }


def daily(df: pd.DataFrame) -> list[dict]:
    return [{"date": day.strftime("%Y-%m-%d"), **summarize(g)}
            for day, g in df.groupby("target_date")]


def by_horizon(df: pd.DataFrame, bucket_h: int = 6) -> list[dict]:
    d = df.dropna(subset=["forecast", "actual"]).copy()
    d = d[d["horizon_h"] >= 0]
    d["bucket"] = (d["horizon_h"] // bucket_h * bucket_h).astype(int)
    return [{"horizon_from_h": int(b), "horizon_to_h": int(b + bucket_h), **summarize(g)}
            for b, g in d.groupby("bucket")]
