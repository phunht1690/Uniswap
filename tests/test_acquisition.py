import csv
import hashlib
import json

import httpx
import pandas as pd
import pytest

from src.data.common import Acquisition, SourceError, record_count, safe_url
from src.data import binance, geckoterminal, the_graph
from src.data.ethereum import EVENTS, fetch_events, signed, word, words
from eth_hash.auto import keccak


def context(tmp_path, handler, monkeypatch):
    monkeypatch.setattr("src.data.common.time.sleep", lambda _: None)
    result = Acquisition(tmp_path, transport=httpx.MockTransport(handler), requests_per_second=10000)
    result.source_delay = {}
    return result


def test_retry_cache_and_corrupt_cache_refetch(tmp_path, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "0"}, json={"error": "busy"}) if len(calls) == 1 else httpx.Response(200, json=[[1], [2]])
    ctx = context(tmp_path, handler, monkeypatch)
    first, meta = ctx.json("test", "https://example.org/history")
    assert first == [[1], [2]] and len(calls) == 2
    assert ctx.json("test", "https://example.org/history")[0] == first
    assert len(calls) == 2 and ctx.cache_hits == 1
    raw = tmp_path / meta["file_path"]
    raw.write_text("corrupt")
    ctx.json("test", "https://example.org/history")
    # Immutable content must be verified; a corrupt cached file cannot be accepted.
    assert len(calls) == 3
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == meta["sha256"]
    ctx.close()


def test_redaction_in_url_body_response_and_ledger(tmp_path, monkeypatch):
    secret = "secret-value-never-save"
    ctx = context(tmp_path, lambda request: httpx.Response(400, json={"echo": secret}), monkeypatch)
    ctx.secrets = (secret,)
    with pytest.raises(SourceError) as error:
        ctx.json("test", f"https://user:password@example.org/api/{secret}/subgraphs/id/foo?api_key={secret}", method="POST", body={"key": secret})
    assert secret not in str(error.value)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()
            assert b"user:password" not in path.read_bytes()
    ctx.close()


def test_frame_versions_and_ledger_idempotent(tmp_path, monkeypatch):
    ctx = context(tmp_path, lambda _: httpx.Response(500), monkeypatch)
    frame = pd.DataFrame({"value": [1, 2]})
    one = ctx.frame("sample", frame, "fixture", "local://test", lineage=["raw.json"])
    size = ctx.log_path.stat().st_size
    ctx.frame("sample", frame, "fixture", "local://test", lineage=["raw.json"])
    assert size == ctx.log_path.stat().st_size
    ctx.frame("sample", pd.DataFrame({"value": [3]}), "fixture", "local://test")
    versions = list((tmp_path / "data/processed/_versions/sample").glob("*.parquet"))
    assert len(versions) == 2
    assert any(hashlib.sha256(path.read_bytes()).hexdigest() == one["sha256"] for path in versions)
    for row in csv.DictReader(ctx.log_path.open()):
        path = tmp_path / row["file_path"]
        if "_versions" in row["file_path"]:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    ctx.close()


def test_binance_timestamp_units_and_closed_bar():
    ms = 1704067200000
    def row(time): return [time, "10", "12", "9", "11", "20", time + 1, "220", 10, "1", "1", "0"]
    daily = binance.normalize([row(ms)], "ETHUSDT", "1d")
    micro = binance.normalize([row(ms * 1000)], "ETHUSDT", "1d")
    assert daily.equals(micro)
    assert daily.timestamp.iloc[0] == pd.Timestamp("2024-01-02", tz="UTC")
    assert "volume_usd" not in daily and daily.volume_quote.iloc[0] == 220


def test_gecko_drops_open_bucket_and_keeps_gaps():
    pool = {"id": "fixture"}
    timestamp = 1704067200
    rows = [[timestamp + d * 86400, 10, 12, 9, 11, 100] for d in [0, 2, 3]]
    result = geckoterminal.normalize(rows, pool, "day", pd.Timestamp("2024-01-04T12:00:00Z"))
    assert list(result.timestamp.dt.day) == [2, 4]
    assert result.volume_usd.sum() == 200
    with pytest.raises(SourceError):
        geckoterminal.normalize([[timestamp, 10, 9, 8, 11, 100]], pool, "day", pd.Timestamp("2024-01-05T00:00:00Z"))


def test_rpc_signed_bigints_roundtrip():
    huge = 2**150 + 123456789
    assert words("0x" + word(huge))[0] == huge
    assert signed(words("0x" + word(-huge))[0]) == -huge
    assert signed(int(word(-887272), 16), 24) == -887272
    with pytest.raises(SourceError): words("0x123")


def test_events_decode_mint_burn_and_resume_without_loss(tmp_path, monkeypatch):
    ctx = context(tmp_path, lambda _: httpx.Response(500), monkeypatch)
    pool = {"id": "fixture", "address": "0x" + "1" * 40, "block_number": 20, "decimals0": 6, "decimals1": 18, "inverted": True}
    names = {"0x" + keccak(value.encode()).hex(): name for name, value in EVENTS.items()}
    topic = {value: key for key, value in names.items()}
    events = []
    for index, kind in enumerate(["mint", "burn", "swap"]):
        values = [123, 2**100, 2000000, 3 * 10**18] if kind == "mint" else [2**100, 2000000, 3 * 10**18]
        topics = [topic[kind], "0x" + word(1), "0x" + word(-60), "0x" + word(60)]
        if kind == "swap": values, topics = [-2000000, 3 * 10**18, 2**96, 2**100, -1], [topic[kind]]
        events.append({"data": "0x" + "".join(word(value) for value in values), "topics": topics, "blockNumber": hex(10 + index), "blockHash": "0xblock", "transactionHash": f"0xtx{index}", "logIndex": hex(index)})
    class FakeRPC:
        endpoint = "https://example.org/rpc"
        calls = 0
        def request(self, method, params):
            self.calls += 1
            start, end = int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16)
            payload = {"result": [event for event in events if start <= int(event["blockNumber"], 16) <= end]}
            path = tmp_path / f"part{start}.json"
            path.write_text(json.dumps(payload))
            return payload["result"], {"file_path": path.name}
    rpc = FakeRPC()
    frame, cov = fetch_events(ctx, rpc, pool, from_block=10, to_block=12, max_chunks=1, chunk_size=1)
    assert len(frame) == 1 and cov["status"] == "partial_checkpointed"
    frame, cov = fetch_events(ctx, rpc, pool, from_block=10, to_block=12, max_chunks=5, chunk_size=1)
    assert len(frame) == 3 and cov["status"] == "complete_requested_window"
    assert frame.iloc[0].liquidity_raw == str(2**100)
    assert frame.iloc[0].tick_lower == -60
    assert frame.iloc[2].amount_base == 3 and frame.iloc[2].amount_quote == -2
    calls = rpc.calls
    assert len(fetch_events(ctx, rpc, pool, from_block=10, to_block=12)[0]) == 3 and rpc.calls == calls
    # A different requested range must not inherit a completed cursor.
    assert len(fetch_events(ctx, rpc, pool, from_block=11, to_block=11)[0]) == 1
    ctx.close()


def test_graph_missing_key_makes_no_request(tmp_path, monkeypatch):
    monkeypatch.delenv("THE_GRAPH_API_KEY", raising=False)
    ctx = context(tmp_path, lambda _: pytest.fail("Missing key must not send a request"), monkeypatch)
    with pytest.raises(SourceError, match="unavailable"):
        the_graph.fetch(ctx, {"address": "0x" + "1" * 40})
    ctx.close()


def test_record_counts_and_url_sanitization():
    assert record_count({"result": [1, 2, 3]}) == 3
    assert record_count({"data": {"attributes": {"ohlcv_list": [[1], [2]]}}}) == 2
    assert "password" not in safe_url("https://user:password@example.org/foo?token=value")
    assert "value" not in safe_url("https://example.org/foo?token=value")


def test_gecko_paginates_and_takes_explicit_usd_volume(tmp_path, monkeypatch):
    base, quote = "0x" + "1" * 40, "0x" + "2" * 40
    calls = []
    def handler(request):
        calls.append(request)
        old = "before_timestamp" in request.url.params
        volume = 100 if request.url.params["currency"] == "usd" else 0.04
        return httpx.Response(200, json={"data": {"attributes": {"ohlcv_list": [] if old else [[1704067200, 10, 12, 9, 11, volume]]}},
                                        "meta": {"base": {"address": base}, "quote": {"address": quote}}})
    ctx = context(tmp_path, handler, monkeypatch)
    result, coverage = geckoterminal.fetch(ctx, {"id": "fixture", "address": base, "base_address": base, "quote_address": quote}, end="2024-01-03T00:00:00Z")
    assert result.volume_usd.iloc[0] == 100 and result.price.iloc[0] == 11
    assert coverage["status"] == "provider_limited"
    assert len(calls) == 3
    assert calls[-1].url.params["before_timestamp"] == "1704067199"
    ctx.close()


def test_fred_missing_values_remain_missing_and_not_predictive(tmp_path, monkeypatch):
    from src.data.fred import fetch
    ctx = context(tmp_path, lambda _: httpx.Response(200, text="observation_date,DFF\n2024-01-01,5.33\n2024-01-02,.\n"), monkeypatch)
    frame, row = fetch(ctx)
    assert pd.isna(frame.value.iloc[1]) and not frame.predictive_eligible.any()
    assert row["start"].startswith("2024-01-01")
    ctx.close()


def test_graph_cursor_snapshot_and_secret_redaction(tmp_path, monkeypatch):
    monkeypatch.setenv("THE_GRAPH_API_KEY", "key-to-be-redacted")
    monkeypatch.delenv("UNISWAP_SUBGRAPH_ID", raising=False)
    pool = {"id": "fixture", "address": "0x" + "1" * 40, "decimals0": 6, "decimals1": 18, "inverted": True}
    calls = []
    def handler(request):
        query = json.loads(request.content)["query"]
        calls.append(query)
        row = {"id": "last", "date": 1704067200, "sqrtPrice": str(2**96), "volumeUSD": "123", "liquidity": str(2**100)}
        return httpx.Response(200, json={"data": {"poolDayDatas": [row]}})
    ctx = context(tmp_path, handler, monkeypatch)
    frame, coverage = the_graph.fetch(ctx, pool, block_number=18000000)
    assert len(frame) == 1 and frame.price.iloc[0] == 1e12
    assert frame.timestamp.iloc[0] == pd.Timestamp("2024-01-02", tz="UTC")
    assert coverage["status"] == "complete_indexed_snapshot"
    assert "number: 18000000" in calls[0]
    the_graph.fetch(ctx, pool, block_number=18000000)
    assert len(calls) == 1
    for path in (tmp_path / "data/raw").rglob("*"):
        if path.is_file(): assert b"key-to-be-redacted" not in path.read_bytes()
    ctx.close()


def test_lagged_ingestion_features_reject_calendar_gaps(tmp_path, monkeypatch):
    from src.data.quality import derive_features
    ctx = context(tmp_path, lambda _: httpx.Response(500), monkeypatch)
    times = pd.date_range("2024-01-01", periods=12, tz="UTC").delete(6)
    frame = pd.DataFrame({"timestamp": times, "price": [100 + i for i in range(11)], "volume_usd": [100] * 11})
    ctx.frame("history_fixture", frame, "fixture", "local://test")
    derive_features(ctx)
    result = pd.read_parquet(tmp_path / "data/processed/features_fixture.parquet")
    assert result.vol_realized_7d.isna().all()
    ctx.close()
