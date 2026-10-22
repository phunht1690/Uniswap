"""Risk constraints, rebalance timing, decomposition and degenerate scenarios."""
import numpy as np
import pytest

from src.evaluation.metrics import decomposition_error, summarize
from src.models.fees import scenario_volumes
from src.models.price_models import gbm
from src.models.strategies import select_optimum, simulate_strategy, width_grid

COMMON = dict(capital=50000, gas_usd=15, fee_rate=0.0005, background_liquidity=100_000_000)


def test_zero_volatility_has_finite_fees_and_no_exit():
    paths = gbm(0, 30, 100, 42)
    volumes = scenario_volumes(paths, 1_000_000)
    result = simulate_strategy(paths.prices, volumes, half_width=1e-8, **COMMON)
    assert np.isfinite(result.excess).all()
    assert np.all(result.fees > 0)
    assert np.all(result.active_share == 1)
    assert not result.exited.any()
    assert decomposition_error(result) < 1e-8


@pytest.mark.parametrize("mode", ["full", "fixed", "dynamic"])
def test_components_add_to_excess_and_pnl_endpoint(mode):
    paths = gbm(1, 90, 60, 13)
    result = simulate_strategy(paths.prices, scenario_volumes(paths, 2e6), mode=mode,
                               half_width=0.1, min_gap=7, slippage_bps=8, trace_index=12, **COMMON)
    assert decomposition_error(result) < 1e-8
    assert result.trace[-1]["lp"] == pytest.approx(result.net[12], abs=1e-12)
    assert result.net[12] - result.trace[-1]["hodl"] == pytest.approx(result.excess[12] / COMMON["capital"])
    assert np.all((result.active_share >= 0) & (result.active_share <= 1))


def test_activity_and_exit_are_not_divided_by_capital():
    prices = np.array([[1, 1.1, 1.4], [1, 1, 1]])
    results = [simulate_strategy(prices, np.zeros_like(prices), half_width=0.2,
                                 **{**COMMON, "capital": capital}) for capital in [1000, 100000]]
    for result in results:
        metrics = summarize(result, 1000, 0.2, 1)
        assert metrics["active_share"] == 0.75
        assert metrics["exit_prob"] == 0.5


def test_rebalance_limit_minimum_gap_and_gas():
    prices = np.array([[1, 2, 0.5, 2, 0.5, 2, 0.5]])
    result = simulate_strategy(prices, np.zeros_like(prices), mode="dynamic", half_width=0.01,
                               min_gap=2, max_rebalances=2, slippage_bps=10, **COMMON)
    assert result.rebalances[0] == 2
    assert result.gas[0] == 5 * COMMON["gas_usd"]
    assert result.rebalance_cost[0] > 0
    disabled = simulate_strategy(prices, np.zeros_like(prices), mode="dynamic", half_width=0.01,
                                 max_rebalances=0, **COMMON)
    assert disabled.rebalances[0] == 0
    assert disabled.gas[0] == COMMON["gas_usd"]


def test_recenter_does_not_collect_fees_for_the_same_outside_bar():
    prices = np.array([[1, 1.5, 1.5]])
    volumes = np.array([[0, 1e6, 0]])
    result = simulate_strategy(prices, volumes, mode="dynamic", half_width=0.01, **COMMON)
    assert result.fees[0] == 0
    assert result.active_share[0] == 0.5


def test_infeasible_optimizer_never_returns_an_unqualified_fallback():
    points = [{"half_width": 0.01, "exit_prob": 0.8, "excess_vs_hodl": 0.2},
              {"half_width": 0.2, "exit_prob": 0.3, "excess_vs_hodl": 0.1}]
    assert select_optimum(points, 0.1) is None
    assert select_optimum(points, 0.4)["half_width"] == 0.2
    assert select_optimum(points, 1)["half_width"] == 0.01
    assert len(width_grid(0.65, 60)) == 20


def test_very_large_gas_is_charged_without_hiding_losses():
    prices = np.ones((5, 10))
    result = simulate_strategy(prices, np.zeros_like(prices), **{**COMMON, "gas_usd": 1e6})
    np.testing.assert_allclose(result.net, -20, atol=1e-12)
    np.testing.assert_allclose(result.excess, -1e6, atol=1e-8)
