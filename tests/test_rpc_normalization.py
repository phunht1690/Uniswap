import math

import pandas as pd
import pytest

from src.data import ethereum
from src.data.common import Acquisition, SourceError


@pytest.mark.parametrize("inverted,d0,d1,quote_usd", [(False, 18, 6, 1.01), (True, 6, 18, 1.01), (False, 8, 18, 2500)])
def test_tick_liquidity_uses_usd_normalization_and_raw_anchor(tmp_path, inverted, d0, d1, quote_usd):
    raw_l = 2**100 + 987654321
    ctx = Acquisition(tmp_path)
    tick = 0
    net = {-60: 100, 60: -200}
    class FakeRPC:
        endpoint = "local://fixture-rpc"
        def batch(self, calls, block):
            if calls and calls[0][1].startswith(ethereum.selector("tickBitmap(int16)")):
                results = []
                for _, data in calls:
                    index = ethereum.signed(int(data[-64:], 16), 16)
                    bitmap = sum(1 << ((value // 60) % 256) for value in net if (value // 60) >> 8 == index)
                    results.append("0x" + ethereum.word(bitmap))
                return results, []
            return ["0x" + ethereum.word(1000) + ethereum.word(net[ethereum.signed(int(data[-64:], 16), 24)]) for _, data in calls], []
    pool = {"id": "fixture", "address": "0x" + "1" * 40, "fee_tier": 3000, "tick": tick, "block_number": 10,
            "sqrt_price_x96": str(2**96), "liquidity_raw": str(raw_l), "decimals0": d0, "decimals1": d1,
            "inverted": inverted, "data_asof": "2024-01-01T00:00:00Z"}
    frame, background, coverage = ethereum.fetch_ticks(ctx, FakeRPC(), pool, quote_usd, half_span_ticks=100)
    assert frame.set_index("tick").loc[-60].liquidity_raw == str(raw_l)
    assert frame.set_index("tick").loc[60].liquidity_raw == str(raw_l - 200)
    # Compare against the USD value of the raw position, in a symmetric raw sqrt range.
    width = .2
    sqrt_price = 1.
    amount0 = raw_l * (1 - math.exp(-width / 2)) / 10**d0
    amount1 = raw_l * (1 - math.exp(-width / 2)) / 10**d1
    token1_per_token0 = 10**(d0 - d1)
    value_quote = amount0 + amount1 / token1_per_token0 if inverted else amount0 * token1_per_token0 + amount1
    expected = value_quote * quote_usd / (2 * (1 - math.exp(-width / 2)))
    assert background == pytest.approx(expected, rel=1e-14)
    assert coverage["status"] == "window_snapshot"
    ctx.close()


def test_factory_snapshot_decimals_and_inverse_price(monkeypatch, tmp_path):
    first = ethereum.specs()[0]
    address = "0x" + "3" * 40
    token0, token1 = first["quote_address"], first["base_address"]
    sqrt_raw = int(math.sqrt(1e12 / 2500) * 2**96)
    class FakeRPC:
        endpoint = "local://fixture-rpc"
        def __init__(self, *args): pass
        def request(self, method, params, ttl=None):
            if method == "eth_chainId": return "0x1", {"file_path": "chain.json"}
            return {"number": "0xa", "timestamp": hex(1704067200), "hash": "0xblock", "baseFeePerGas": hex(10**9)}, {"file_path": "block.json"}
        def batch(self, calls, block):
            assert block == "0xa"
            function = calls[0][1][:10]
            if function == ethereum.selector("getPool(address,address,uint24)"):
                return ["0x" + ethereum.address_word(address)] + ["0x" + ethereum.word(0)] * (len(calls) - 1), []
            if function == ethereum.selector("decimals()"):
                return ["0x" + ethereum.word(d) for d in [18, 6, 6, 8]], []
            return ["0x" + ethereum.address_word(token0), "0x" + ethereum.address_word(token1), "0x" + ethereum.word(500),
                    "0x" + ethereum.word(sqrt_raw) + ethereum.word(198000), "0x" + ethereum.word(2**120 + 7)], []
    monkeypatch.setattr(ethereum, "RPC", FakeRPC)
    ctx = Acquisition(tmp_path)
    pools, _, _ = ethereum.fetch(ctx, "local://fixture-rpc")
    assert len(pools) == 1 and pools[0]["p0"] == pytest.approx(2500)
    assert pools[0]["inverted"] is True
    assert pools[0]["liquidity_raw"] == str(2**120 + 7)
    assert pools[0]["data_asof"] == "2024-01-01T00:00:00+00:00"
    ctx.close()
