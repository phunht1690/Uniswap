"""Fees with consistent normalized liquidity units and explicit volume scenarios."""
import numpy as np
import pandas as pd

from src.features.point_in_time import before_asof


def fee_amount(volume_usd, fee_rate, own_liquidity, background_liquidity, active):
    volume, own, background = np.broadcast_arrays(np.asarray(volume_usd, dtype=float), np.asarray(own_liquidity, dtype=float),
                                                 np.asarray(background_liquidity, dtype=float))
    if not all(np.isfinite(x).all() for x in [volume, own, background]) or min(volume.min(), own.min(), background.min()) < 0:
        raise ValueError("Volume and liquidity must be finite and nonnegative")
    if not 0 <= fee_rate <= 1:
        raise ValueError("fee_rate must be a fraction between 0 and 1")
    share = np.divide(own, own + background, out=np.zeros_like(own), where=(own + background) > 0)
    return volume * fee_rate * share * np.asarray(active, dtype=bool)


def scenario_volumes(paths, mean_volume_usd, factor_cap=3.0, shock_scale=0.8):
    if paths.volumes is not None:
        return paths.volumes
    ratio = np.ones_like(paths.prices)
    np.divide(paths.abs_innovation, paths.daily_sd * shock_scale, out=ratio, where=paths.daily_sd > 0)
    # At sigma=0 the JS 0/0 expression is undefined; use the declared mean volume.
    result = mean_volume_usd * np.minimum(factor_cap, ratio)
    result[:, 0] = 0
    return result


def observed_volumes(paths, history, asof, volume_24h_usd, *, lookback_days=180, min_regime_rows=10, factor_cap=3.0, shock_scale=0.8):
    """Fit frozen volume means against lagged realized-volatility regimes."""
    if paths.volumes is not None:
        return paths.volumes, {"method": "paired_historical_return_volume_bootstrap"}
    mean = float(volume_24h_usd)
    info = {"method": "observed_24h_volume_times_capped_innovation", "volume_24h_usd": mean}
    baseline = np.full_like(paths.prices, mean)
    if history is not None and len(history):
        past = before_asof(history, asof)
        returns = np.log(past.price).diff()
        lagged_vol = returns.rolling(30, min_periods=30).std(ddof=1).shift(1) * np.sqrt(365)
        consecutive = past.index.to_series().diff().eq(pd.Timedelta(days=1)).rolling(30, min_periods=30).sum().eq(30).shift(1, fill_value=False)
        sample = pd.DataFrame({"lagged_vol": lagged_vol.where(consecutive), "volume": past.volume_usd})
        sample = sample.loc[sample.index >= pd.Timestamp(asof) - pd.Timedelta(days=lookback_days)].dropna()
        recent = past.loc[past.index >= pd.Timestamp(asof) - pd.Timedelta(days=30), "volume_usd"]
        mean = float(recent.mean()) if len(recent) else float(volume_24h_usd)
        baseline.fill(mean)
        info = {"method": "trailing_30d_mean_volume_times_capped_innovation" if len(recent) else "observed_24h_volume_times_capped_innovation", "mean_volume_usd": mean,
                "calibration_last_timestamp": past.index[-1].isoformat(), "lookback_days": lookback_days,
                "feature_lag_periods": 1, "history_rows": len(past)}
        if len(sample) >= min_regime_rows * 3:
            cuts = np.quantile(sample.lagged_vol, [1 / 3, 2 / 3])
            if cuts[1] > cuts[0] + 1e-12:
                groups = np.searchsorted(cuts, sample.lagged_vol.to_numpy(), side="right")
                counts = [int(np.count_nonzero(groups == index)) for index in range(3)]
                levels = [float(sample.volume.to_numpy()[groups == index].mean()) if counts[index] >= min_regime_rows else mean for index in range(3)]
                future = np.searchsorted(cuts, paths.daily_sd * np.sqrt(365), side="right")
                baseline = np.asarray(levels)[future]
                info.update(method="lagged_volatility_regime_means_times_capped_innovation", volatility_cutpoints_annual=cuts.tolist(),
                            regime_mean_volume_usd=levels, regime_rows=counts, fitted_rows=len(sample))
    ratio = np.ones_like(paths.prices)
    np.divide(paths.abs_innovation, paths.daily_sd * shock_scale, out=ratio, where=paths.daily_sd > 0)
    result = baseline * np.minimum(factor_cap, ratio)
    result[:, 0] = 0
    info.update(innovation_factor_cap=factor_cap, innovation_scale=shock_scale, zero_volatility_uses_regime_mean=True,
                note="Volume regimes are estimated before asof; the innovation multiplier remains a declared scenario assumption.")
    return result, info
