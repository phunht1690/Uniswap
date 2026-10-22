"""Exercise API contracts, provenance labels, resource bounds and run retrieval."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import create_app


def test_health_and_dashboard(client):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["engine_status"] == "numpy_simulation"
    assert health.json()["stage"] == 5
    assert client.get("/api/v1/data/status").json()["mode"] == "not_downloaded"
    page = client.get("/")
    assert page.status_code == 200
    assert "RangeLab" in page.text
    assert "không phải lời khuyên đầu tư" in page.text
    assert client.get("/dashboard/").status_code == 200
    assert "Dữ liệu minh họa" in client.get('/legacy').text
    assert client.get("/openapi.json").status_code == 200


def test_pool_provenance_and_quote_units(client):
    response = client.get("/api/v1/pools").json()
    assert len(response["pools"]) == 4
    assert response["data_asof"] is None
    for pool in response["pools"]:
        assert pool["data_kind"] == "illustrative"
        assert pool["vol_realized_7d"] is None
        assert pool["vol_realized_30d"] is None
        assert pool["fee_rate"] == pool["fee_tier"] / 1_000_000
    btc = next(p for p in response["pools"] if p["base"] == "WBTC")
    assert btc["quote"] == "WETH"  # p0=28 is WETH per WBTC, not USD.


def test_run_is_repeatable_and_retrievable_after_restart(client, tmp_path):
    config = {"pool": "weth-usdc-500", "n_paths": 35, "horizon_days": 12, "seed": 42}
    first_response = client.post("/api/v1/simulate", json=config)
    assert first_response.status_code == 200
    first = first_response.json()
    assert client.post("/api/v1/simulate", json=config).json() == first
    run_id = first["meta"]["run_id"]
    assert len(run_id) == 64
    stored = client.get(f"/api/v1/runs/{run_id}").json()
    assert stored["result"] == first
    assert stored["config"]["seed"] == 42
    with TestClient(create_app(state_dir=tmp_path)) as restarted:
        assert restarted.post("/api/v1/simulate", json=stored["config"]).json() == first
        (tmp_path / "outputs/runs" / (run_id + ".json")).unlink()
        assert restarted.post("/api/v1/simulate", json=stored["config"]).json() == first
    assert len(first["sample_paths"]) == 30
    assert len(first["sample_paths"][0]) == 13
    assert len(first["pnl_path"]) == 13
    assert len(first["strategies"]) == 5
    assert len(first["sweep"]) == 20
    assert first["meta"]["optimization_status"] == "feasible"
    assert first["optimum"]["exit_prob"] <= stored["config"]["risk_max_exit_prob"]
    assert first["liquidity_ticks"] == []
    assert all(point["lp_return"] is not None for point in first["stress"])
    assert len(set(first["sample_paths"][0])) > 1
    selected = first["pnl_path"][-1]
    assert selected["lp"] != selected["hodl"]


def test_seed_and_parameter_changes_get_new_ids(client):
    original = client.post("/api/v1/simulate", json={}).json()["meta"]["run_id"]
    for config in [{"seed": 43}, {"gas_usd": 30}, {"risk_max_exit_prob": 0.1}, {"path_index": 1}]:
        changed = client.post("/api/v1/simulate", json=config)
        assert changed.status_code == 200
        assert changed.json()["meta"]["run_id"] != original


@pytest.mark.parametrize("config", [
    {"capital": 0}, {"horizon_days": 366}, {"horizon_days": -1}, {"n_paths": 5001},
    {"vol_annual": -0.1}, {"gas_usd": -1}, {"risk_max_exit_prob": 1.1},
    {"price_model": "unknown"}, {"seed": -1}, {"min_rebalance_gap_days": 0},
    {"path_index": 300}, {"n_paths": 5000, "horizon_days": 365},
    {"unexpected_secret": "should-not-appear-in-error"}, {"max_rebalances": -1},
    {"rebalance_slippage_bps": 1001}, {"min_half_width": 0.2, "max_half_width": 0.1},
    {"calibration_asof": "2024-01-01T00:00:00"}, {"capital": 1e-100},
])
def test_invalid_input_has_vietnamese_error_without_body_echo(client, config):
    response = client.post("/api/v1/simulate", json=config)
    assert response.status_code == 422
    assert "Tham số không hợp lệ" in response.json()["detail"]
    assert "should-not-appear-in-error" not in response.text


def test_nonfinite_values_and_malformed_json_are_rejected(client):
    for body in ['{"vol_annual": NaN}', '{"gas_usd": Infinity}', '{"capital": 1e999}', '{']:
        response = client.post("/api/v1/simulate", content=body, headers={"Content-Type": "application/json"})
        assert response.status_code == 422


def test_zero_vol_and_very_large_gas_are_finite_simulation_cases(client):
    result = client.post("/api/v1/simulate", json={"vol_annual": 0, "gas_usd": 1_000_000, "capital": 1000})
    assert result.status_code == 200
    optimum = result.json()["optimum"]
    assert optimum["gas"] == 1000
    assert optimum["excess_vs_hodl"] == pytest.approx(optimum["fees"] - optimum["il"] - optimum["gas"])
    assert optimum["net"] < 0
    assert result.json()["meta"]["engine_status"] == "numpy_simulation"
    assert result.json()["optimum"]["exit_prob"] == 0


def test_unknown_pool_and_missing_calibration_history(client):
    assert client.post("/api/v1/simulate", json={"pool": "not-a-pool"}).status_code == 400
    for model in ["bootstrap", "garch"]:
        response = client.post("/api/v1/simulate", json={"price_model": model})
        assert response.status_code == 400
        assert "calibration_asof" in response.json()["detail"]
        with_asof = client.post("/api/v1/simulate", json={"price_model": model, "calibration_asof": "2024-01-01T00:00:00Z"})
        assert with_asof.status_code == 400
        assert "Chưa có lịch sử" in with_asof.json()["detail"]


def test_no_feasible_range_is_explicit(client):
    response = client.post("/api/v1/simulate", json={"min_half_width": 1e-6, "max_half_width": 2e-6,
                                                    "risk_max_exit_prob": 0, "horizon_days": 30})
    assert response.status_code == 200
    body = response.json()
    assert body["optimum"] is None
    assert body["meta"]["optimization_status"] == "infeasible"
    assert len(body["strategies"]) == 4
    assert body["pnl_path"] == []
    assert body["stress"] == []
    assert body["meta"]["messages"]
    assert all(point["feasible"] is False for point in body["sweep"])


def test_missing_or_unsafe_run_ids(client):
    assert client.get("/api/v1/runs/" + "a" * 64).status_code == 404
    assert client.get("/api/v1/runs/not-a-hash").status_code == 422


def test_backtest_does_not_fabricate_history(client):
    route = "/api/v1/backtest/weth-usdc-500"
    assert client.get(route, params={"start": "2022-01-01", "end": "2026-06-30"}).status_code == 503
    assert client.get(route, params={"start": "2025-01-01", "end": "2022-01-01"}).status_code == 400
    assert client.get(route, params={"start": "invalid", "end": "2026-06-30"}).status_code == 422


def test_cors_is_limited_to_local_development(client):
    response = client.options("/api/v1/simulate", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options("/api/v1/simulate", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 400


def test_cache_permission_error_returns_clear_503(client, tmp_path, monkeypatch):
    original_open = Path.open

    def guarded_open(path, mode="r", *args, **kwargs):
        if path.parent == tmp_path / "outputs/runs" and "x" in mode:
            raise PermissionError("test-only denied cache write")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    response = client.post("/api/v1/simulate", json={"n_paths": 10, "horizon_days": 7})
    assert response.status_code == 503
    assert "quyền" in response.json()["detail"]
    assert "outputs/runs" in response.json()["detail"]
