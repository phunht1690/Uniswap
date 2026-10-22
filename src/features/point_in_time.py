"""Every feature at t uses observations strictly before t; never backfill."""
import numpy as np
import pandas as pd

from src.utils.config import load_config


def validate_history(history):
    if not {"price", "volume_usd"}.issubset(history.columns):
        raise ValueError("History requires price and volume_usd")
    result = history.copy()
    if not isinstance(result.index, pd.DatetimeIndex) or result.index.tz is None:
        raise ValueError("History index must be timezone-aware UTC timestamps")
    result.index = result.index.tz_convert("UTC")
    if not result.index.is_monotonic_increasing or result.index.has_duplicates:
        raise ValueError("History must be sorted and have unique timestamps")
    values = result[["price", "volume_usd"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values[:, 0] <= 0).any() or (values[:, 1] < 0).any():
        raise ValueError("History must contain finite positive prices and nonnegative volumes")
    return result


def before_asof(history, asof):
    frame = validate_history(history)
    timestamp = pd.Timestamp(asof)
    if timestamp.tzinfo is None:
        raise ValueError("asof must include a timezone")
    return frame.loc[frame.index < timestamp.tz_convert("UTC")].copy()


def daily_pairs(history, asof, min_rows=30):
    frame = before_asof(history, asof)
    if len(frame) < min_rows + 1:
        raise ValueError(f"Need at least {min_rows + 1} daily price observations before asof")
    if not (frame.index.to_series().diff().dropna() == pd.Timedelta(days=1)).all():
        raise ValueError("Daily models require consecutive daily observations; do not backfill gaps")
    pairs = pd.DataFrame({"log_return": np.log(frame.price).diff(), "volume_usd": frame.volume_usd}).iloc[1:]
    return pairs


def lagged_features(history, window=7):
    frame = validate_history(history)
    returns = np.log(frame.price).diff()
    return pd.DataFrame({"vol_annual": returns.rolling(window, min_periods=window).std(ddof=1).shift(1) * np.sqrt(365),
                         "volume_usd": frame.volume_usd.rolling(window, min_periods=window).mean().shift(1)})


def chronological_splits(history):
    """Fixed train/validation/test definitions; acquisition may cover earlier years."""
    frame = validate_history(history)
    spec = load_config("research")["splits"]
    result = {}
    for name in ["warmup", "train", "validation", "test"]:
        start, end = spec[name]["start"], spec[name]["end"]
        low = frame.index.min() if start == "earliest_available" else pd.Timestamp(start, tz="UTC")
        high = pd.Timestamp("2027-01-01", tz="UTC") if end == "latest_available_in_2026" else pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        result[name] = frame.loc[(frame.index >= low) & (frame.index < high)].copy()
    combined = pd.concat(list(result.values()))
    if combined.index.has_duplicates:
        raise ValueError("Configured research partitions overlap")
    return result


def tuning_sample(history):
    splits = chronological_splits(history)
    return pd.concat([splits["train"], splits["validation"]]).sort_index()
