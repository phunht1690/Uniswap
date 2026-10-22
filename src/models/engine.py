"""Research Monte Carlo with logged observed inputs or explicit local fixtures."""
import importlib.metadata as metadata

import numpy as np

from api.schemas import SimulationRequest, SimulationResponse
from src.evaluation.metrics import summarize
from src.models.fees import observed_volumes, scenario_volumes
from src.models.price_models import gbm, garch, stationary_bootstrap
from src.models.strategies import select_optimum, simulate_strategy, width_grid
from src.models.v3 import pos

MODEL_VERSION = "stage4-observed-inputs-v2"


def numerical_versions(price_model):
    names = ["numpy"] if price_model == "gbm" else ["numpy", "pandas"]
    if price_model == "garch":
        names += ["arch", "scipy", "statsmodels"]
    return {name: metadata.version(name) for name in names}


def simulate(config: SimulationRequest, pool, settings, run_id, data_hash, history=None, provenance=None, market=None):
    if config.price_model == "gbm":
        paths = gbm(config.vol_annual, config.horizon_days, config.n_paths, config.seed)
        effective_vol = config.vol_annual
    elif config.price_model == "bootstrap":
        paths = stationary_bootstrap(history, config.calibration_asof, config.horizon_days, config.n_paths,
                                     config.seed, config.bootstrap_mean_block_days)
        effective_vol = float(paths.daily_sd[0, 1] * np.sqrt(365))
    else:
        paths = garch(history, config.calibration_asof, config.horizon_days, config.n_paths, config.seed)
        effective_vol = float(paths.daily_sd[0, 1] * np.sqrt(365))
    mean_volume = pool["volume_24h_usd"]
    if history is not None:
        mean_volume = float(history.volume_usd.mean())
    compatibility = settings["research"]["html_compatibility"]
    simulation_settings = settings["research"]["simulation"]
    optimizer_settings = settings["research"]["optimizer"]
    volume_info = None
    if market is not None:
        estimation = settings["research"]["estimation"]
        volumes, volume_info = observed_volumes(paths, history, config.calibration_asof, pool["volume_24h_usd"],
                                                lookback_days=estimation.get("volume_fit_lookback_days", 180),
                                                min_regime_rows=estimation.get("min_volume_regime_rows", 10),
                                                factor_cap=simulation_settings["volume_factor_cap"], shock_scale=simulation_settings["volume_shock_scale"])
    else:
        volumes = scenario_volumes(paths, mean_volume, simulation_settings["volume_factor_cap"], simulation_settings["volume_shock_scale"])
    concentration = compatibility["background_concentration"]
    background = pool["background_liquidity_normalized_usd"] if market is not None else pool["tvl_usd"] * concentration / 2
    common = dict(capital=config.capital, gas_usd=config.gas_usd, fee_rate=pool["fee_rate"],
                  background_liquidity=background, min_gap=config.min_rebalance_gap_days,
                  max_rebalances=config.max_rebalances, slippage_bps=config.rebalance_slippage_bps,
                  rebalance_gas_multiplier=compatibility["dynamic_rebalance_gas_multiplier"])

    def evaluate(mode, width, trace=False):
        result = simulate_strategy(paths.prices, volumes, mode=mode, half_width=width,
                                   trace_index=config.path_index if trace else None, **common)
        return result, summarize(result, config.capital, width, pool["p0"])

    grid = width_grid(effective_vol, config.horizon_days, config.min_half_width, config.max_half_width,
                      size=optimizer_settings["grid_points"], width_floor=optimizer_settings["auto_max_width_floor_log"],
                      sigma_multiplier=optimizer_settings["auto_max_width_sigma_multiplier"])
    sweep = []
    for width in grid:
        _, point = evaluate("fixed", float(width))
        point["feasible"] = point["exit_prob"] <= config.risk_max_exit_prob
        sweep.append(point)
    optimum = select_optimum(sweep, config.risk_max_exit_prob)
    scaled_width = max(simulation_settings["min_scaled_half_width_log"], compatibility["volatility_multiplier"] * effective_vol * np.sqrt(config.horizon_days / 365))
    strategies = []
    for name, label, mode, width in [("full", "Full range", "full", None),
                                      ("fixed", "Cố định ±20% (log)", "fixed", compatibility["fixed_half_width_log"]),
                                      ("vol_scaled", "Theo biến động (1,5σ√T)", "fixed", scaled_width),
                                      ("dynamic", "Động (recenter)", "dynamic", scaled_width)]:
        _, point = evaluate(mode, width)
        point["feasible"] = point["exit_prob"] <= config.risk_max_exit_prob
        strategies.append({"id": name, "label": label, **point})
    trace, stress, messages = [], [], []
    if optimum is not None:
        selected_result, _ = evaluate("fixed", optimum["half_width"], trace=True)
        trace = selected_result.trace
        strategies.append({"id": "optimizer", "label": "Optimizer (đề xuất trong mô phỏng)", **optimum})
        position = pos(config.capital, 1, optimum["half_width"])
        for shock in [-0.3, 0.3]:
            lp = (float(position.value(1 + shock)) + optimum["fees"] * config.capital - config.gas_usd) / config.capital - 1
            hodl = shock / 2
            stress.append({"shock": shock, "lp_return": lp, "hodl_return": hodl, "excess_vs_hodl": lp - hodl,
                           "status": "Minh họa: cú sốc cuối kỳ, cộng phí kỳ vọng giữ cố định; không phải stress phí/thanh khoản nội sinh."})
    else:
        messages.append("Không có range trên lưới thỏa xác suất rời range tối đa. optimum=null; nới độ rộng tối đa, giảm chân trời hoặc điều chỉnh ngưỡng rủi ro.")
    return SimulationResponse.model_validate({
        "optimum": optimum, "sweep": sweep, "strategies": strategies,
        "sample_paths": (paths.prices[:30] * pool["p0"]).tolist(), "pnl_path": trace, "stress": stress,
        "liquidity_ticks": market["ticks"] if market is not None else [],
        "meta": {"run_id": run_id, "seed": config.seed, "model_version": MODEL_VERSION, "data_hash": data_hash,
                 "engine_status": "numpy_simulation", "optimization_status": "feasible" if optimum is not None else "infeasible",
                 "messages": messages,
                 "data_kind": "observed_snapshot" if market is not None else "illustrative",
                 "data_label": "Dữ liệu đầu vào quan sát · kết quả mô phỏng" if market is not None else "Dữ liệu minh họa",
                 "data_asof": pool["data_asof"] if market is not None else None,
                 "assumptions": {
                     "warning": settings["research"]["warning"], "fixture_only": False,
                     "market_data_kind": "observed_snapshot" if market is not None else "illustrative", "implemented_price_model": config.price_model,
                     "effective_config": config.model_dump(mode="json"),
                     "pool": {key: pool.get(key) for key in ["id", "label", "base", "quote", "p0", "fee_tier", "tvl_usd", "volume_24h_usd", "quote_usd", "address", "block_number", "data_asof", "available_at"]},
                     "market_snapshot": market["provenance"] if market is not None else None,
                     "price_model": paths.info, "numerical_versions": numerical_versions(config.price_model),
                     "effective_vol_annual_for_width": effective_vol,
                     "returns_unit": "fraction_of_initial_capital", "price_unit": f"{pool['quote']}/{pool['base']}",
                     "liquidity_unit": "initial_USD_value_at_normalized_price_1_not_raw_onchain_L",
                     "background_liquidity": {"method": "observed_current_raw_L_normalized_to_initial_USD", "normalized_liquidity": background,
                                              "future_liquidity": "Current active L held constant across future days and prices", "tick_interval_convention": "Right of each tick in ascending raw tick order"} if market is not None else {"method": "illustrative_TVL_times_CONC_over_2", "concentration": concentration},
                     "volume_method": volume_info if market is not None else ("paired_historical_samples" if config.price_model == "bootstrap" else "mean_volume_times_min_3_abs_innovation_over_0.8_daily_sd; sigma0_uses_mean"),
                     "quote_usd_assumption": "Quote/USD held constant in each scenario, including WETH for WBTC/WETH; not a joint USD price forecast.",
                     "fees_compounded": False, "gas_open_transactions": 1, "gas_rebalance_transactions": compatibility["dynamic_rebalance_gas_multiplier"],
                     "gas_close_transactions": 0, "slippage_method": "bps_times_recentered_inventory_value_as_separate_cash_cost",
                     "first_rebalance": "May occur on day 1; min_gap separates subsequent recenters, matching supplied JS.",
                     "rebalance_timing": "At observed close, after fees for that bar; new range applies from next bar.",
                     "solvency_constraint": "Not imposed; separate cost account can yield negative total wealth at very large gas.",
                     "q5_definition": "sorted_terminal_excess[floor(n_paths*0.05)]",
                     "exit_probability_definition": "Ever outside range at daily observation times; intraday crossings unobserved.",
                     "optimizer": {"grid_points": len(grid), "objective": "mean_excess_vs_hodl", "constraint": "empirical_daily_ever_exit_probability", "grid_selection_is_not_out_of_sample_validation": True},
                     "calibration_provenance": provenance or [], "liquidity_ticks_status": "observed_pinned_snapshot" if market is not None else "unavailable_no_onchain_data",
                     "settings": settings,
                     "limitations": ["Current observed snapshot is frozen in forward scenarios" if market is not None else "Pool presets and background liquidity are illustrative", "No MEV/JIT or market impact", "No intraday fee attribution", "Flat gas; slippage is a configurable approximation", "No historical backtest or untouched-test empirical result yet"],
                 }},
    })
