"""Change observations at/after t and confirm decisions and fits before t agree."""
import numpy as np
import pandas as pd
import pytest

from src.features.point_in_time import before_asof, chronological_splits, lagged_features, tuning_sample
from src.models.price_models import fit_garch, stationary_bootstrap


def history():
    rng = np.random.default_rng(90210)
    index = pd.date_range("2022-01-01", "2026-01-10", freq="D", tz="UTC")
    returns = rng.normal(0, 0.02, len(index))
    return pd.DataFrame({"price": np.exp(np.cumsum(returns)), "volume_usd": 1e6 * (1 + np.abs(returns) * 20)}, index=index)


def test_lagged_features_do_not_change_when_current_or_future_data_changes():
    original = history()
    t = pd.Timestamp("2024-04-01", tz="UTC")
    changed = original.copy()
    changed.loc[t:, "price"] *= 10
    changed.loc[t:, "volume_usd"] *= 100
    pd.testing.assert_frame_equal(lagged_features(original).loc[:t], lagged_features(changed).loc[:t])
    assert lagged_features(original).iloc[:7].vol_annual.isna().all()
    expected_volume = original.loc[original.index < t].volume_usd.tail(7).mean()
    assert lagged_features(original).loc[t, "volume_usd"] == pytest.approx(expected_volume, rel=0, abs=1e-8)


def test_current_observation_excluded_from_bootstrap_and_garch_fit():
    original = history().iloc[:300]
    t = original.index[220]
    changed = original.copy()
    changed.loc[t:, "price"] *= 100
    changed.loc[t:, "volume_usd"] *= 100
    pd.testing.assert_frame_equal(before_asof(original, t), before_asof(changed, t))
    first = stationary_bootstrap(original, t, 15, 20, 42)
    second = stationary_bootstrap(changed, t, 15, 20, 42)
    np.testing.assert_array_equal(first.prices, second.prices)
    np.testing.assert_array_equal(first.volumes, second.volumes)
    assert fit_garch(original, t) == fit_garch(changed, t)


def test_test_partition_cannot_change_tuning_sample():
    original = history()
    changed = original.copy()
    changed.loc[changed.index.year >= 2025, "price"] *= 1000
    changed.loc[changed.index.year >= 2025, "volume_usd"] *= 1000
    pd.testing.assert_frame_equal(tuning_sample(original), tuning_sample(changed))
    splits = chronological_splits(original)
    assert set(splits["train"].index.year) == {2022, 2023}
    assert set(splits["validation"].index.year) == {2024}
    assert set(splits["test"].index.year) == {2025, 2026}
    assert tuning_sample(original).index.max() < pd.Timestamp("2025-01-01", tz="UTC")
