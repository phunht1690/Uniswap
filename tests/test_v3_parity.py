"""Compare Python against the unchanged supplied JS on identical input paths."""
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from src.evaluation.metrics import summarize
from src.models.fees import scenario_volumes
from src.models.price_models import PricePaths
from src.models.strategies import simulate_strategy
from src.models.v3 import pos

HERE = Path(__file__).parent


def oracle(payload):
    node = shutil.which("node")
    assert node, "Node.js 18+ is required for genuine JS/Python parity tests."
    process = subprocess.run([node, str(HERE / "js_oracle.cjs")], input=json.dumps(payload),
                             text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    return json.loads(process.stdout)


def test_position_values_match_original_js_below_inside_above():
    specs = []
    for center in [0.8, 1.0, 3.2]:
        for width in [None, 0.0001, 0.01, 0.2, 1.0]:
            specs.append({"capital": 1000, "center": center, "width": width,
                          "prices": [center * p for p in [0.1, 0.7, 0.999, 1, 1.001, 1.4, 3]]})
    expected = oracle({"positions": specs})["positions"]
    errors = []
    for spec, reference in zip(specs, expected):
        position = pos(spec["capital"], spec["center"], spec["width"])
        actual = position.value(np.asarray(spec["prices"]))
        errors.extend(np.abs(actual - reference["values"]))
        np.testing.assert_allclose(position.L, reference["L"], rtol=1e-10)
    assert max(errors) < 1e-6


@pytest.mark.parametrize("mode,js_mode", [("full", "full"), ("fixed", "fixed"), ("dynamic", "dyn")])
def test_strategy_cashflows_match_js_with_shared_prices_and_shocks(mode, js_mode):
    prices = np.array([[1, 1.1, 1.4, 0.8, 0.7, 1.0, 1.3, 0.9],
                       [1, 0.9, 0.7, 1.2, 1.5, 1.1, 0.8, 0.7],
                       [1, 1.0, 1.01, 0.99, 1.0, 1.02, 1.0, 1.0]], dtype=float)
    shocks = np.column_stack([np.zeros(3), np.abs(np.diff(np.log(prices), axis=1))])
    options = {"cap": 50000, "sig": 0.65, "gas": 15, "tvl": 180, "v": 140, "fee": 0.0005, "reb": 2}
    payload = {"paths": [{"a": a.tolist(), "z": z.tolist()} for a, z in zip(prices, shocks)], "width": 0.12, "options": options}
    expected = oracle(payload)["results"]
    paths = PricePaths(prices, shocks, np.full_like(prices, options["sig"] / np.sqrt(365)))
    volumes = scenario_volumes(paths, options["v"] * 1e6)
    result = simulate_strategy(prices, volumes, capital=options["cap"], gas_usd=options["gas"],
                               fee_rate=options["fee"], background_liquidity=options["tvl"] * 1e6 * 3 / 2,
                               mode=mode, half_width=0.12, min_gap=2, max_rebalances=365)
    for python_name, js_name in [("fees", "fees"), ("gas", "gas"), ("il", "il"), ("excess", "ex"),
                                 ("active_share", "act"), ("exited", "exit")]:
        values = np.asarray([row[js_name] for row in expected[js_mode]])
        assert np.max(np.abs(getattr(result, python_name) - values)) < 1e-6
    metrics = summarize(result, options["cap"], None if mode == "full" else 0.12, 3200)
    legacy = expected[js_mode + "_aggregate"]
    for py_key, js_key in [("fees", "fees"), ("il", "il"), ("gas", "gas"), ("excess_vs_hodl", "ex"), ("q5", "q5")]:
        assert abs(metrics[py_key] - legacy[js_key]) < 1e-6
    # Isolate the original aggregation bug rather than reproducing it in research.
    assert metrics["active_share"] == pytest.approx(legacy["act"] * options["cap"])
    assert metrics["exit_prob"] == pytest.approx(legacy["exit"] * options["cap"])
