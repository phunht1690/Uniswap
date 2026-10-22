"""Vectorized Uniswap v3 inventory math in one consistent quote numeraire."""
from dataclasses import dataclass

import numpy as np

MIN_TICK, MAX_TICK = -887272, 887272
TICK_SPACING = {100: 1, 500: 10, 3000: 60, 10000: 200}
LOG_TICK = np.log(1.0001)


def positive(value, name):
    array = np.asarray(value, dtype=float)
    if np.any(~np.isfinite(array)) or np.any(array <= 0):
        raise ValueError(f"{name} must be finite and positive")
    return array


@dataclass(frozen=True)
class Position:
    pl: np.ndarray
    pu: np.ndarray
    liquidity: np.ndarray

    @property
    def L(self):
        return self.liquidity

    def amounts(self, price):
        price = positive(price, "price")
        q = np.clip(price, self.pl, self.pu)
        root = np.sqrt(q)
        # expm1 avoids catastrophic cancellation in very narrow ranges.
        x = self.liquidity / root * -np.expm1((np.log(q) - np.log(self.pu)) / 2)
        y = self.liquidity * root * -np.expm1((np.log(self.pl) - np.log(q)) / 2)
        return x, y

    def value(self, price):
        x, y = self.amounts(price)
        return x * price + y

    val = value


def position_from_bounds(capital, center, p_low, p_high):
    capital, center, low, high = np.broadcast_arrays(positive(capital, "capital"), positive(center, "center"),
                                                    positive(p_low, "p_low"), positive(p_high, "p_high"))
    if np.any((low >= high) | (center < low) | (center > high)):
        raise ValueError("Bounds must contain center and have positive width")
    root = np.sqrt(center)
    denominator = root * (-np.expm1((np.log(center) - np.log(high)) / 2)
                          - np.expm1((np.log(low) - np.log(center)) / 2))
    return Position(low, high, capital / denominator)


def pos(capital, center=1.0, half_width=None):
    """Match the supplied JS pos(); full range uses its finite 1e-9..1e9 bounds."""
    center = positive(center, "center")
    if half_width is None:
        low, high = 1e-9, 1e9
    else:
        width = positive(half_width, "half_width")
        if np.any(width > 80):
            raise ValueError("half_width must not exceed 80 log units")
        low, high = center * np.exp(-width), center * np.exp(width)
    return position_from_bounds(capital, center, low, high)


def il_v2(price_ratio):
    ratio = positive(price_ratio, "price_ratio")
    return 2 * np.sqrt(ratio) / (1 + ratio) - 1


def tick_to_price(tick, decimals0=0, decimals1=0, invert=False):
    tick = np.asarray(tick, dtype=float)
    if np.any(~np.isfinite(tick)) or np.any(tick != np.floor(tick)) or np.any((tick < MIN_TICK) | (tick > MAX_TICK)):
        raise ValueError("tick must be an integer in the v3 protocol bounds")
    price = np.exp(tick * LOG_TICK + (decimals0 - decimals1) * np.log(10.0))
    return 1 / price if invert else price


def price_to_tick(price, decimals0=0, decimals1=0, invert=False, spacing=1, rounding="floor"):
    price = positive(price, "price")
    if spacing not in TICK_SPACING.values() or rounding not in {"floor", "ceil"}:
        raise ValueError("Unsupported tick spacing or rounding")
    log_price = -np.log(price) if invert else np.log(price)
    raw = (log_price - (decimals0 - decimals1) * np.log(10.0)) / LOG_TICK / spacing
    nearest = np.rint(raw)
    raw = np.where(np.abs(raw - nearest) < 1e-8, nearest, raw)
    tick = (np.floor(raw) if rounding == "floor" else np.ceil(raw)) * spacing
    if np.any((tick < MIN_TICK) | (tick > MAX_TICK)):
        raise ValueError("price maps outside v3 protocol bounds")
    return tick.astype(np.int64)
