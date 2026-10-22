"""Seed reproducibility, joint bootstrap samples and estimated GARCH recursion."""
import numpy as np
import pandas as pd
import pytest

from src.features.point_in_time import daily_pairs
from src.models.price_models import fit_garch, gbm, garch, stationary_bootstrap


@pytest.fixture
def historical_sample():
    rng = np.random.default_rng(2024)
    returns = rng.normal(0, 0.015, 400)
    index = pd.date_range("2023-01-01", periods=401, freq="D", tz="UTC")
    return pd.DataFrame({"price": 100 * np.exp(np.r_[0, np.cumsum(returns)]),
                         "volume_usd": np.r_[1e6, 1e6 * (1 + 20 * np.abs(returns))]}, index=index)


def test_gbm_same_seed_same_array_and_different_seed_changes_paths():
    first = gbm(0.65, 90, 200, 42)
    repeated = gbm(0.65, 90, 200, 42)
    np.testing.assert_array_equal(first.prices, repeated.prices)
    assert not np.array_equal(first.prices, gbm(0.65, 90, 200, 43).prices)
    assert first.prices.shape == (200, 91)
    assert np.all(first.prices > 0)


def test_stationary_bootstrap_preserves_return_volume_pairs(historical_sample):
    asof = pd.Timestamp("2024-02-01", tz="UTC")
    pairs = daily_pairs(historical_sample, asof)
    result = stationary_bootstrap(historical_sample, asof, 20, 30, 42, mean_block_days=5)
    repeated = stationary_bootstrap(historical_sample, asof, 20, 30, 42, mean_block_days=5)
    np.testing.assert_array_equal(result.prices, repeated.prices)
    # Identify each sampled observation by its unique volume, then check its return.
    by_volume = dict(zip(pairs.volume_usd.to_numpy(), pairs.log_return.to_numpy()))
    returns = np.diff(np.log(result.prices), axis=1)
    expected = np.array([[by_volume[volume] for volume in row] for row in result.volumes[:, 1:]])
    np.testing.assert_allclose(returns, expected, atol=1e-14)
    assert result.info["calibration_last_timestamp"] < asof.isoformat()


def test_garch_arch_fit_and_seeded_simulation(historical_sample):
    asof = pd.Timestamp("2024-02-01", tz="UTC")
    fitted = fit_garch(historical_sample, asof)
    assert fitted["omega"] >= 0
    assert fitted["alpha"] + fitted["beta"] <= 1 + 1e-6
    first = garch(historical_sample, asof, 10, 12, 42)
    second = garch(historical_sample, asof, 10, 12, 42)
    np.testing.assert_array_equal(first.prices, second.prices)
    assert np.isfinite(first.prices).all()
    assert np.all(first.daily_sd[:, 1:] >= 0)


def test_historical_models_reject_missing_days_and_constant_garch(historical_sample):
    asof = pd.Timestamp("2024-02-01", tz="UTC")
    with pytest.raises(ValueError, match="consecutive"):
        stationary_bootstrap(historical_sample.drop(historical_sample.index[30]), asof, 10, 10, 42)
    flat = historical_sample.copy()
    flat.price = 1.0
    with pytest.raises(ValueError, match="nonconstant"):
        fit_garch(flat, asof)
