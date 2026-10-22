"""Monetary components divide by capital; probabilities never do."""
import numpy as np


def summarize(result, capital, half_width, p0, p_low=None, p_high=None):
    excess = np.sort(result.excess / capital)
    index = min(len(excess) - 1, int(len(excess) * 0.05))
    # Preserve the supplied JS order-statistic definition, not interpolated quantile.
    tail_count = max(1, int(np.ceil(len(excess) * 0.05)))
    lower = p0 * (1e-9 if half_width is None else np.exp(-half_width))
    upper = p0 * (1e9 if half_width is None else np.exp(half_width))
    return {"half_width": half_width, "p_low": float(lower if p_low is None else p_low),
            "p_high": float(upper if p_high is None else p_high),
            "fees": float(np.mean(result.fees) / capital), "il": float(np.mean(result.il) / capital),
            "gas": float(np.mean(result.gas) / capital), "net": float(np.mean(result.net)),
            "excess_vs_hodl": float(np.mean(result.excess) / capital),
            "q5": float(excess[index]), "cvar5": float(np.mean(excess[:tail_count])),
            "active_share": float(np.mean(result.active_share)), "exit_prob": float(np.mean(result.exited)),
            "rebalance_count": float(np.mean(result.rebalances)),
            "rebalance_cost": float(np.mean(result.rebalance_cost) / capital)}


def decomposition_error(result):
    reconstructed = result.fees - result.il - result.gas - result.rebalance_cost
    return float(np.max(np.abs(result.excess - reconstructed)))
