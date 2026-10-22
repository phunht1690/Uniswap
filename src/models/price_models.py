"""Seeded GBM, paired stationary bootstrap and arch-estimated GARCH(1,1)."""
from dataclasses import dataclass, field
import warnings

import numpy as np

from src.features.point_in_time import daily_pairs


@dataclass
class PricePaths:
    prices: np.ndarray
    abs_innovation: np.ndarray
    daily_sd: np.ndarray
    volumes: np.ndarray | None = None
    info: dict = field(default_factory=dict)


def gbm(vol_annual, horizon_days, n_paths, seed):
    rng = np.random.default_rng(seed)
    sd = vol_annual / np.sqrt(365)
    innovations = rng.standard_normal((n_paths, horizon_days)) * sd
    prices = np.ones((n_paths, horizon_days + 1))
    prices[:, 1:] = np.exp(np.cumsum(innovations - 0.5 * sd**2, axis=1))
    shocks = np.column_stack([np.zeros(n_paths), np.abs(innovations)])
    return PricePaths(prices, shocks, np.full_like(prices, sd), info={"model": "gbm", "drift_annual": 0.0, "rng": "numpy.PCG64"})


def stationary_bootstrap(history, asof, horizon_days, n_paths, seed, mean_block_days=10):
    pairs = daily_pairs(history, asof)
    rng = np.random.default_rng(seed)
    indices = np.empty((n_paths, horizon_days), dtype=int)
    cursor = rng.integers(len(pairs), size=n_paths)
    for day in range(horizon_days):
        if day:
            restart = rng.random(n_paths) < 1 / mean_block_days
            cursor = np.where(restart, rng.integers(len(pairs), size=n_paths), (cursor + 1) % len(pairs))
        indices[:, day] = cursor
    returns = pairs.log_return.to_numpy()[indices]
    volumes = np.column_stack([np.zeros(n_paths), pairs.volume_usd.to_numpy()[indices]])
    prices = np.column_stack([np.ones(n_paths), np.exp(np.cumsum(returns, axis=1))])
    shocks = np.column_stack([np.zeros(n_paths), np.abs(returns)])
    sd = float(pairs.log_return.std(ddof=1))
    return PricePaths(prices, shocks, np.full_like(prices, sd), volumes,
                      {"model": "bootstrap", "method": "paired_stationary", "mean_block_days": mean_block_days,
                       "calibration_last_timestamp": pairs.index[-1].isoformat(), "calibration_rows": len(pairs), "rng": "numpy.PCG64"})


def fit_garch(history, asof):
    from arch import arch_model
    pairs = daily_pairs(history, asof, min_rows=100)
    returns_percent = pairs.log_return.to_numpy() * 100
    if np.std(returns_percent) < 1e-10:
        raise ValueError("GARCH requires nonconstant historical returns; choose GBM vol=0 for a constant-price scenario")
    with warnings.catch_warnings(record=True) as caught:
        fitted = arch_model(returns_percent, mean="Zero", vol="GARCH", p=1, q=1, dist="normal", rescale=False).fit(disp="off", show_warning=False)
    if fitted.convergence_flag != 0:
        raise ValueError("GARCH optimization did not converge; increase the calibration sample or choose GBM/bootstrap")
    params = {name: float(fitted.params[name]) for name in ["omega", "alpha[1]", "beta[1]"]}
    omega, alpha, beta = params["omega"] / 10000, params["alpha[1]"], params["beta[1]"]
    if not np.isfinite([omega, alpha, beta]).all() or min(omega, alpha, beta) < 0 or alpha + beta > 1 + 1e-6:
        raise ValueError("GARCH parameters are invalid")
    variance = float(np.asarray(fitted.conditional_volatility)[-1] / 100)**2
    last_residual = float(np.asarray(fitted.resid)[-1] / 100)
    return {"omega": omega, "alpha": alpha, "beta": beta, "last_variance": variance,
            "last_residual": last_residual, "volume_mean_usd": float(pairs.volume_usd.mean()),
            "calibration_last_timestamp": pairs.index[-1].isoformat(), "calibration_rows": len(pairs),
            "fit_warnings": [str(item.message) for item in caught]}


def garch(history, asof, horizon_days, n_paths, seed):
    fitted = fit_garch(history, asof)
    rng = np.random.default_rng(seed)
    prices = np.ones((n_paths, horizon_days + 1))
    shocks, sds = np.zeros_like(prices), np.zeros_like(prices)
    variance = np.full(n_paths, fitted["last_variance"])
    residual = np.full(n_paths, fitted["last_residual"])
    for day in range(1, horizon_days + 1):
        variance = fitted["omega"] + fitted["alpha"] * residual**2 + fitted["beta"] * variance
        sd = np.sqrt(np.maximum(variance, 0))
        residual = rng.standard_normal(n_paths) * sd
        prices[:, day] = prices[:, day - 1] * np.exp(residual - 0.5 * variance)
        shocks[:, day], sds[:, day] = np.abs(residual), sd
    return PricePaths(prices, shocks, sds, info={"model": "garch", "fit": fitted, "rng": "numpy.PCG64"})
