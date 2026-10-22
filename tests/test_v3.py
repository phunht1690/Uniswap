"""Analytic invariants and numerical edge cases independent of JS bugs."""
import numpy as np
import pytest

from src.models.v3 import TICK_SPACING, il_v2, pos, price_to_tick, tick_to_price


def test_v2_il_reference_values():
    assert float(il_v2(2)) == pytest.approx(-0.0571909584)
    assert float(il_v2(4)) == pytest.approx(-0.2)
    assert float(il_v2(1)) == 0
    assert float(il_v2(0.5)) == pytest.approx(float(il_v2(2)))


@pytest.mark.parametrize("width", [1e-10, 1e-7, 0.001, 0.2, 10, 50, None])
def test_initial_value_conservation_and_piecewise_inventory(width):
    position = pos(50000, 1, width)
    assert float(position.value(1)) == pytest.approx(50000, abs=1e-8)
    x, y = position.amounts(position.pl * 0.9)
    assert float(y) == pytest.approx(0, abs=1e-10)
    x, y = position.amounts(position.pu * 1.1)
    assert float(x) == pytest.approx(0, abs=1e-10)
    assert np.isfinite(position.value(np.array([0.5, 1, 2]))).all()


def test_very_wide_v3_converges_to_v2():
    prices = np.array([0.1, 0.5, 1, 2, 4, 10])
    position = pos(10000, 1, 60)
    np.testing.assert_allclose(position.value(prices), 10000 * np.sqrt(prices), rtol=1e-12)


@pytest.mark.parametrize("decimals0,decimals1,invert", [(0, 0, False), (18, 6, False), (6, 18, True)])
def test_ticks_prices_and_token_order_round_trip(decimals0, decimals1, invert):
    ticks = np.array([-887200, -10000, -60, 0, 60, 10000, 887200])
    prices = tick_to_price(ticks, decimals0, decimals1, invert)
    recovered = price_to_tick(prices, decimals0, decimals1, invert)
    np.testing.assert_array_equal(recovered, ticks)


def test_tick_spacing_and_bounds():
    assert TICK_SPACING == {100: 1, 500: 10, 3000: 60, 10000: 200}
    assert int(price_to_tick(tick_to_price(101), spacing=60)) == 60
    assert int(price_to_tick(tick_to_price(101), spacing=60, rounding="ceil")) == 120
    with pytest.raises(ValueError):
        tick_to_price(887273)
    with pytest.raises(ValueError):
        price_to_tick(0)
