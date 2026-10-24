import pytest
from fastapi.testclient import TestClient

from app import config, store
from scripts import ingest


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    config.ACTUALS_FILE = d / "actuals.csv.gz"
    config.FORECASTS_FILE = d / "forecasts.csv.gz"
    a, f = ingest.synthetic()
    a.to_csv(config.ACTUALS_FILE, index=False, compression="gzip")
    f.to_csv(config.FORECASTS_FILE, index=False, compression="gzip")
    store.load.cache_clear()
    from app.main import app
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_forecast_day_respects_cutoff(client):
    r = client.get("/api/forecast", params={"date": "2026-01-15", "cutoff": "09:30"})
    assert r.status_code == 200
    j = r.json()
    assert len(j["points"]) == 48
    assert j["forecast_published_to"] <= "2026-01-14T09:30:00+00:00"


def test_accuracy_and_horizon(client):
    j = client.get("/api/accuracy").json()
    assert j["overall"]["n"] > 1000 and len(j["daily"]) == 31
    h = client.get("/api/accuracy/horizon").json()["buckets"]
    assert h[0]["rmse"] < h[-1]["rmse"]  # error grows with lead time


def test_validation(client):
    assert client.get("/api/forecast", params={"date": "bad"}).status_code == 422
    assert client.get("/api/accuracy", params={"cutoff": "99:99"}).status_code == 422
