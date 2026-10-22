"""Observed-data contracts use isolated, explicitly synthetic source fixtures."""
import copy
import math

import numpy as np
import pandas as pd
import pytest

from src.data.common import Acquisition
from src.models.fees import observed_volumes
from src.models.price_models import gbm
from src.utils.serialization import atomic_json


@pytest.fixture
def observed(client, tmp_path):
    context = Acquisition(tmp_path)
    root_raw = math.sqrt(1e12 / 2500)
    integer_root = int(root_raw * 2**96)
    raw_l = 2**100 + 17
    factor = 1 / (integer_root / 2**96 * 1e6)
    tick = int(math.log(root_raw**2) / math.log(1.0001))
    base = {"id": "weth-usdc-500", "label": "WETH/USDC synthetic observation fixture", "base": "WETH", "quote": "USDC",
            "address": "0x" + "1" * 40, "p0": 2500., "fee_tier": 500, "fee_rate": .0005,
            "tvl_usd": 123456789., "volume_24h_usd": 23456789., "quote_usd": 1., "block_number": 123, "block_hash": "0xfixture",
            "decimals0": 6, "decimals1": 18, "sqrt_price_x96": str(integer_root), "liquidity_raw": str(raw_l), "inverted": True,
            "background_liquidity_normalized_usd": raw_l * factor, "data_asof": "2024-05-31T23:45:00Z",
            "available_at": "2024-06-01T00:00:00Z", "context_available_at": "2024-05-31T23:55:00Z"}
    pools = [base, {**base, "id": "weth-usdc-3000", "fee_tier": 3000, "fee_rate": .003, "address": "0x" + "2" * 40}]
    rng = np.random.default_rng(712)
    timestamps = pd.date_range("2023-06-01", "2024-06-07", tz="UTC")
    returns = rng.normal(0, .02, len(timestamps))
    history = pd.DataFrame({"timestamp": timestamps, "price": 2500 * np.exp(np.cumsum(returns)), "volume_usd": 2e7 * (1 + 15 * np.abs(returns))})
    for pool in pools:
        ticks = pd.DataFrame([{"tick": tick + shift, "price": 1 / (1.0001**(tick + shift) * 1e-12), "liquidity_raw": str(raw_l),
                               "liquidity_normalized_usd": raw_l * factor, "block_number": 123, "data_asof": pool["data_asof"]} for shift in [-50, 0, 50]])
        context.frame("ticks_" + pool["id"], ticks, "local_unit_test", "local://synthetic-observed-fixture", kind="observed_snapshot")
        context.frame("history_" + pool["id"], history, "local_unit_test", "local://synthetic-observed-fixture", kind="observed_snapshot")
    def save():
        path = tmp_path / "data/processed/pool_registry.json"
        atomic_json(path, {"data_kind": "observed_snapshot", "pools": pools})
        context.log("local_unit_test", "local://synthetic-observed-fixture", path, len(pools), kind="observed_snapshot")
    save()
    yield {"context": context, "pools": pools, "history": history, "save": save, "root": tmp_path}
    context.close()


def test_observed_pools_and_live_inputs_replace_presets(client, observed):
    response = client.get("/api/v1/pools").json()
    assert response["data_kind"] == "observed_snapshot" and len(response["pools"]) == 2
    pool = response["pools"][0]
    assert pool["p0"] == 2500 and pool["vol_realized_30d"] > 0
    assert pool["history_end"] < pool["available_at"]
    assert client.get("/api/v1/health").json()["data_kind"] == "observed_snapshot"
    result = client.post("/api/v1/simulate", json={"n_paths": 12, "horizon_days": 5}).json()
    assert result["meta"]["data_kind"] == "observed_snapshot" and len(result["liquidity_ticks"]) == 3
    assumptions = result["meta"]["assumptions"]
    assert assumptions["background_liquidity"]["method"] == "observed_current_raw_L_normalized_to_initial_USD"
    assert assumptions["effective_config"]["calibration_asof"].startswith("2024-06-01")
    assert assumptions["volume_method"]["feature_lag_periods"] == 1
    assert assumptions["market_snapshot"]["block_number"] == 123
    replay = client.post("/api/v1/simulate", json=assumptions["effective_config"]).json()
    assert replay == result


def test_current_snapshot_cannot_be_backdated(client, observed):
    response = client.post("/api/v1/simulate", json={"calibration_asof": "2024-05-01T00:00:00Z"})
    assert response.status_code == 400 and "không được dùng" in response.json()["detail"]


def test_observed_fees_do_not_use_tvl_concentration_proxy(client, observed):
    config = {"n_paths": 15, "horizon_days": 7, "vol_annual": 0, "gas_usd": 0}
    first = client.post("/api/v1/simulate", json=config).json()
    observed["pools"][0]["tvl_usd"] *= 1e8
    observed["save"]()
    second = client.post("/api/v1/simulate", json=config).json()
    assert second["meta"]["run_id"] != first["meta"]["run_id"]
    assert [row["fees"] for row in first["sweep"]] == [row["fees"] for row in second["sweep"]]


def test_corrupt_observed_registry_never_silently_becomes_mock(client, observed):
    path = observed["root"] / "data/processed/pool_registry.json"
    path.write_text("{}")
    assert client.get("/api/v1/pools").status_code == 503
    assert client.post("/api/v1/simulate", json={}).status_code == 503
    assert client.get("/api/v1/health").json()["status"] == "degraded"


def test_missing_tick_file_and_wrong_liquidity_units_are_rejected(client, observed):
    observed["pools"][0]["background_liquidity_normalized_usd"] *= 1e12
    observed["save"]()
    wrong = client.post("/api/v1/simulate", json={})
    assert wrong.status_code == 503 and "sai đơn vị" in wrong.json()["detail"]
    observed["pools"][0]["background_liquidity_normalized_usd"] /= 1e12
    observed["save"]()
    (observed["root"] / "data/processed/ticks_weth-usdc-500.parquet").unlink()
    assert client.post("/api/v1/simulate", json={}).status_code == 503


def test_future_history_mutation_leaves_observed_forecast_identical(client, observed):
    config = {"n_paths": 10, "horizon_days": 5, "price_model": "bootstrap"}
    first = client.post("/api/v1/simulate", json=config)
    assert first.status_code == 200, first.text
    frame = observed["history"].copy()
    future = frame.timestamp >= pd.Timestamp("2024-06-01", tz="UTC")
    frame.loc[future, "price"] *= 100
    frame.loc[future, "volume_usd"] *= 100
    observed["context"].frame("history_weth-usdc-500", frame, "local_unit_test", "local://synthetic-observed-fixture", kind="observed_snapshot")
    run_id = first.json()["meta"]["run_id"]
    (observed["root"] / "outputs/runs" / (run_id + ".json")).unlink()
    assert client.post("/api/v1/simulate", json=config).json() == first.json()


def test_observed_gbm_uses_24h_volume_when_history_is_absent(client, observed):
    (observed["root"] / "data/processed/history_weth-usdc-500.parquet").unlink()
    result = client.post("/api/v1/simulate", json={"n_paths": 10, "horizon_days": 3}).json()
    assert result["meta"]["assumptions"]["volume_method"]["method"] == "observed_24h_volume_times_capped_innovation"
    assert client.post("/api/v1/simulate", json={"price_model": "garch"}).status_code == 503


def test_volume_regime_fit_uses_only_past_and_calendar_windows(observed):
    frame = observed["history"].set_index("timestamp")
    asof = pd.Timestamp("2024-06-01", tz="UTC")
    paths = gbm(.4, 10, 12, 42)
    first, info = observed_volumes(paths, frame, asof, 100)
    modified = frame.copy()
    modified.loc[modified.index >= asof, ["price", "volume_usd"]] *= 10000
    second, repeat_info = observed_volumes(paths, modified, asof, 100)
    np.testing.assert_array_equal(first, second)
    assert info == repeat_info and info["feature_lag_periods"] == 1
    changed = frame.copy()
    changed.loc[changed.index < asof, "volume_usd"] *= 2
    doubled, _ = observed_volumes(paths, changed, asof, 100)
    np.testing.assert_allclose(doubled, 2 * first)
    zero, _ = observed_volumes(gbm(0, 10, 12, 42), frame, asof, 100)
    assert np.isfinite(zero).all()
