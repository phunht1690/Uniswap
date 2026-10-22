"""Verify the local data cache, file hashes and embedded run assumptions."""
import csv
import hashlib

import duckdb
import pyarrow.parquet as pq
import numpy as np
import pandas as pd
import pytest

from src.data.bootstrap import bootstrap


def synthetic_history():
    rng = np.random.default_rng(2023)
    index = pd.date_range("2023-01-01", periods=400, freq="D", tz="UTC")
    returns = rng.normal(0, 0.02, len(index))
    return pd.DataFrame({"timestamp": index, "price": np.exp(np.cumsum(returns)),
                         "volume_usd": 1e6 * (1 + np.abs(returns) * 20)})


def write_logged_history(root, frame, logged=True):
    path = root / "data/processed/history_weth-usdc-500.parquet"
    frame.to_parquet(path, index=False)
    if logged:
        from src.data.bootstrap import LOG_FIELDS
        with (root / "data/source_log.csv").open("a", encoding="utf-8", newline="") as stream:
            csv.DictWriter(stream, fieldnames=LOG_FIELDS).writerow({
                "source": "local_unit_test", "endpoint": "local://synthetic-history-for-tests-only",
                "downloaded_at_utc": "2024-02-05T00:00:00Z", "period_start": "2023-01-01", "period_end": "2024-02-04",
                "row_count": len(frame), "file_path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "data_kind": "illustrative"})


def test_bootstrap_is_idempotent_and_all_generated_data_is_logged(tmp_path):
    first = bootstrap(tmp_path)
    log = tmp_path / "data/source_log.csv"
    before = log.read_bytes()
    assert bootstrap(tmp_path) == first
    assert log.read_bytes() == before
    with log.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3
    for row in rows:
        path = tmp_path / row["file_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
        assert row["source"] == "local_mock"
        assert row["data_kind"] == "illustrative"
        assert row["period_start"] == row["period_end"] == ""
    assert pq.read_table(tmp_path / "data/processed/mock_pools.parquet").num_rows == 4
    with duckdb.connect(str(tmp_path / "data/processed/catalog.duckdb"), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM mock_pools").fetchone()[0] == 4


def test_run_records_include_all_history_preference_and_fixed_splits(client):
    meta = client.post("/api/v1/simulate", json={}).json()["meta"]
    settings = meta["assumptions"]["settings"]
    assert settings["sources"]["history"]["mode"] == "all_available"
    assert settings["sources"]["history"]["start"] is None
    assert settings["research"]["splits"]["use_test_for_selection"] is False
    assert settings["research"]["estimation"]["feature_lag_periods"] == 1
    assert meta["data_asof"] is None
    assert meta["assumptions"]["implemented_price_model"] == "gbm"
    assert meta["assumptions"]["market_data_kind"] == "illustrative"


@pytest.mark.parametrize("model", ["bootstrap", "garch"])
def test_api_historical_models_use_only_logged_pre_asof_samples(client, tmp_path, model):
    frame = synthetic_history()
    config = {"price_model": model, "calibration_asof": "2023-10-01T00:00:00Z", "n_paths": 20, "horizon_days": 10}
    write_logged_history(tmp_path, frame, logged=False)
    missing_log = client.post("/api/v1/simulate", json=config)
    assert missing_log.status_code == 400
    assert "hash khớp" in missing_log.json()["detail"]
    write_logged_history(tmp_path, frame)
    first = client.post("/api/v1/simulate", json=config)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["meta"]["assumptions"]["implemented_price_model"] == model
    assert body["meta"]["data_kind"] == "illustrative"
    changed = frame.copy()
    future = changed.timestamp >= pd.Timestamp(config["calibration_asof"])
    changed.loc[future, "price"] *= 100
    changed.loc[future, "volume_usd"] *= 100
    write_logged_history(tmp_path, changed)
    # Recompute without cached result to prove point-in-time isolation end to end.
    (tmp_path / "outputs/runs" / (body["meta"]["run_id"] + ".json")).unlink()
    repeated = client.post("/api/v1/simulate", json=config)
    assert repeated.status_code == 200
    assert repeated.json() == body
