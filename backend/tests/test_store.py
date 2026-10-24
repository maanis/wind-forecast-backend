from pathlib import Path

from app import config, store


def test_resolve_data_dir_supports_docker_and_local_paths():
    docker_data_dir = config.resolve_data_dir("/app/data")
    assert docker_data_dir.is_absolute()
    assert docker_data_dir.as_posix().endswith("/app/data")
    assert config.resolve_data_dir("data") == config.BASE_DIR / "data"
    assert config.resolve_data_dir("backend/data") == config.BASE_DIR / "data"
    assert config.resolve_data_dir(None) == config.BASE_DIR / "data"


def test_load_committed_gzip_files(monkeypatch):
    data_dir = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "ACTUALS_FILE", data_dir / "actuals.csv.gz")
    monkeypatch.setattr(config, "FORECASTS_FILE", data_dir / "forecasts.csv.gz")
    store.load.cache_clear()

    try:
        actuals, forecasts = store.load()
    finally:
        store.load.cache_clear()

    assert len(actuals) > 0
    assert len(forecasts) > 0
    assert {"startTime", "generation"} <= set(actuals.columns)
    assert {"startTime", "publishTime", "generation"} <= set(forecasts.columns)
