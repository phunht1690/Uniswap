"""Common-market simulations for static and dynamic concentrated liquidity."""
from dataclasses import dataclass

import numpy as np

from src.models.fees import fee_amount
from src.models.v3 import Position, pos


@dataclass
class StrategyResult:
    fees: np.ndarray
    gas: np.ndarray
    il: np.ndarray
    excess: np.ndarray
    net: np.ndarray
    active_share: np.ndarray
    exited: np.ndarray
    rebalances: np.ndarray
    rebalance_cost: np.ndarray
    inventory: np.ndarray
    hodl: np.ndarray
    trace: list
    hedge_pnl: np.ndarray | None = None


def simulate_strategy(prices, volumes, *, capital, gas_usd, fee_rate, background_liquidity,
                      mode="fixed", half_width=0.2, min_gap=7, max_rebalances=365,
                      slippage_bps=0.0, trace_index=None, rebalance_gas_multiplier=2):
    """Keep fees in cash; charge one opening gas and two gas units per recenter.

    Decisions use the observed close and take effect after that bar's fee accrual.
    min_gap separates recenters; as in the supplied JS the first may occur on day 1.
    All prices/liquidity are in initial normalized quote-value units, with quote/USD
    held fixed in the illustrative model. Fees, gas and slippage are USD cash flows.
    """
    prices, volumes = np.asarray(prices, dtype=float), np.asarray(volumes, dtype=float)
    if prices.ndim != 2 or prices.shape[1] < 2 or prices.shape != volumes.shape:
        raise ValueError("prices and volumes must have shape (n_paths, horizon+1)")
    if not np.isfinite(prices).all() or np.any(prices <= 0) or not np.allclose(prices[:, 0], 1):
        raise ValueError("Prices must be finite, positive and normalized to initial price 1")
    if mode not in {"full", "fixed", "dynamic"} or capital <= 0 or gas_usd < 0 or min_gap < 1 or max_rebalances < 0 or slippage_bps < 0:
        raise ValueError("Invalid strategy parameters")
    count, steps = prices.shape
    horizon = steps - 1
    background = np.broadcast_to(np.asarray(background_liquidity, dtype=float), prices.shape)
    width = None if mode == "full" else half_width
    po = pos(np.full(count, capital), np.ones(count), width)
    gas = np.full(count, gas_usd)
    rebalances = np.zeros(count, dtype=int)
    rebalance_cost = np.zeros(count)
    trace = []
    if trace_index is not None:
        if not 0 <= trace_index < count:
            raise ValueError("trace_index outside path array")
        trace.append({"day": 0, "lp": -gas_usd / capital, "hodl": 0.0})
    if mode != "dynamic":
        active = (prices[:, 1:] >= po.pl[:, None]) & (prices[:, 1:] <= po.pu[:, None])
        fee_matrix = fee_amount(volumes[:, 1:], fee_rate, po.L[:, None], background[:, 1:], active)
        fees = fee_matrix.sum(axis=1)
        active_share, exited = active.mean(axis=1), np.any(~active, axis=1)
        if trace_index is not None:
            index = trace_index
            single = Position(po.pl[index], po.pu[index], po.L[index])
            inventory_path = single.value(prices[index, 1:])
            returns = (inventory_path + np.cumsum(fee_matrix[index]) - gas_usd) / capital - 1
            trace += [{"day": day, "lp": float(lp), "hodl": float((1 + prices[index, day]) / 2 - 1)} for day, lp in enumerate(returns, start=1)]
    else:
        fees, active_count = np.zeros(count), np.zeros(count)
        exited = np.zeros(count, dtype=bool)
        last_rebalance = np.full(count, -min_gap)
        for day in range(1, steps):
            price = prices[:, day]
            active = (price >= po.pl) & (price <= po.pu)
            fees += fee_amount(volumes[:, day], fee_rate, po.L, background[:, day], active)
            active_count += active
            exited |= ~active
            reset = ~active & ((day - last_rebalance) >= min_gap) & (rebalances < max_rebalances)
            if np.any(reset):
                current_value = po.value(price)
                replacement = pos(current_value[reset], price[reset], half_width)
                new_low, new_high, new_liquidity = po.pl.copy(), po.pu.copy(), po.L.copy()
                new_low[reset], new_high[reset], new_liquidity[reset] = replacement.pl, replacement.pu, replacement.L
                po = Position(new_low, new_high, new_liquidity)
                gas[reset] += rebalance_gas_multiplier * gas_usd
                rebalance_cost[reset] += current_value[reset] * slippage_bps / 10000
                rebalances[reset] += 1
                last_rebalance[reset] = day
            if trace_index is not None:
                index = trace_index
                wealth = po.value(price)[index] + fees[index] - gas[index] - rebalance_cost[index]
                trace.append({"day": day, "lp": float(wealth / capital - 1), "hodl": float((1 + price[index]) / 2 - 1)})
        active_share = active_count / horizon
    inventory = po.value(prices[:, -1])
    hodl = capital / 2 * (1 + prices[:, -1])
    excess = inventory + fees - gas - rebalance_cost - hodl
    net = (inventory + fees - gas - rebalance_cost) / capital - 1
    return StrategyResult(fees, gas, hodl - inventory, excess, net, active_share, exited, rebalances, rebalance_cost, inventory, hodl, trace)


def width_grid(vol_annual, horizon_days, minimum=0.005, maximum=None, size=20, width_floor=0.5, sigma_multiplier=4):
    upper = maximum if maximum is not None else max(width_floor, sigma_multiplier * vol_annual * np.sqrt(horizon_days / 365))
    if minimum <= 0 or upper < minimum:
        raise ValueError("Invalid width grid bounds")
    return np.geomspace(minimum, upper, size)


def select_optimum(sweep, risk_max_exit_prob):
    feasible = [point for point in sweep if point["exit_prob"] <= risk_max_exit_prob]
    return max(feasible, key=lambda point: point["excess_vs_hodl"]) if feasible else None
