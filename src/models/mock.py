"""HTTP contract fixtures, intentionally not a quantitative simulation engine."""
import math

from api.schemas import Metrics, SimulationRequest, SimulationResponse

MODEL_VERSION = "stage1-contract-fixture-v1"


def mock_result(config: SimulationRequest, pool: dict, run_id: str, data_hash: str, settings: dict) -> SimulationResponse:
    """Return constant-price, zero-fee fixtures with explicit unavailable fields."""
    p0 = pool["p0"]
    cost = config.gas_usd / config.capital

    def metric(width: float | None) -> dict:
        return Metrics(half_width=width, p_low=p0 * math.exp(-width) if width is not None else p0 * 1e-9,
                       p_high=p0 * math.exp(width) if width is not None else p0 * 1e9,
                       active_share=1, fees=0, il=0, gas=cost, net=-cost,
                       excess_vs_hodl=-cost, q5=-cost, exit_prob=0).model_dump()

    specs = [("full", "Full range", None), ("fixed", "Cố định ±20% (log)", 0.2),
             ("vol_scaled", "Theo biến động", max(0.01, 1.5 * config.vol_annual * math.sqrt(config.horizon_days / 365))),
             ("dynamic", "Động (recenter)", 0.2), ("optimizer", "Optimizer — fixture chưa tối ưu", 0.2)]
    return SimulationResponse.model_validate({
        "optimum": metric(0.2),
        "sweep": [metric(0.005 * 1.22**i) for i in range(20)],
        "strategies": [{"id": name, "label": label, **metric(width)} for name, label, width in specs],
        "sample_paths": [[p0] * (config.horizon_days + 1) for _ in range(min(30, config.n_paths))],
        "pnl_path": [{"day": day, "lp": -cost, "hodl": 0} for day in range(config.horizon_days + 1)],
        "stress": [{"shock": shock, "lp_return": None, "hodl_return": None, "excess_vs_hodl": None,
                    "status": "Chưa tính; engine Python thuộc bước 2."} for shock in [-0.3, 0.3]],
        "liquidity_ticks": [],
        "meta": {"run_id": run_id, "seed": config.seed, "model_version": MODEL_VERSION,
                 "data_hash": data_hash,
                 "assumptions": {
                     "warning": settings["research"]["warning"],
                     "fixture_only": True,
                     "description": "Giá hằng, phí và IL bằng 0; gas mở vị thế = gas_usd. Chỉ kiểm tra hợp đồng API, không phải kết quả Monte Carlo hay khoảng khuyến nghị.",
                     "requested_price_model": config.price_model,
                     "implemented_price_model": None,
                     "returns_unit": "fraction_of_initial_capital",
                     "price_unit": f"{pool['quote']}/{pool['base']}",
                     "volatility_unit": "annual_fraction",
                     "liquidity_ticks_status": "unavailable_no_onchain_data",
                     "stress_status": "not_implemented",
                     "settings": settings,
                     "limitations": ["MEV/JIT chưa mô hình hóa", "Chưa có trượt giá rebalance", "Chưa có thanh khoản nền thật", "WBTC/WETH cần giá WETH/USD point-in-time để quy về USD"],
                 }},
    })
