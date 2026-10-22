"""Read-only Ethereum RPC discovery, pinned snapshots, ticks and event cursors."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from eth_hash.auto import keccak

from src.data.common import SourceError, coverage_row

FACTORY = "0x1f98431c8ad98523631ae4a59f267346ea31f984"
TOKENS = {"WETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
          "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7", "WBTC": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"}
PAIRS = [("WETH", "USDC", [500, 3000]), ("WETH", "USDT", [500, 3000]),
         ("WBTC", "WETH", [500, 3000]), ("USDC", "USDT", [100, 500])]
EVENTS = {"swap": "Swap(address,address,int256,int256,uint160,uint128,int24)",
          "mint": "Mint(address,address,int24,int24,uint128,uint256,uint256)",
          "burn": "Burn(address,int24,int24,uint128,uint256,uint256)"}


def selector(signature):
    return "0x" + keccak(signature.encode())[:4].hex()


def word(value):
    return format(value % (1 << 256), "064x")


def address_word(address):
    return address.lower().removeprefix("0x").rjust(64, "0")


def words(data):
    data = data.removeprefix("0x")
    if len(data) % 64:
        raise SourceError("ethereum_rpc: invalid ABI response length")
    return [int(data[i:i + 64], 16) for i in range(0, len(data), 64)]


def signed(value, bits=256):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >= (1 << (bits - 1)) else value


def specs():
    return [{"id": f"{base.lower()}-{quote.lower()}-{fee}", "label": f"{base}/{quote} {fee / 10000:g}%",
             "base": base, "quote": quote, "base_address": TOKENS[base], "quote_address": TOKENS[quote],
             "fee_tier": fee, "fee_rate": fee / 1e6} for base, quote, fees in PAIRS for fee in fees]


class RPC:
    def __init__(self, context, endpoint="https://ethereum-rpc.publicnode.com"):
        self.context, self.endpoint = context, endpoint

    def request(self, method, params, ttl=None):
        payload, meta = self.context.json("ethereum_rpc", self.endpoint, method="POST",
                                          body={"jsonrpc": "2.0", "method": method, "params": params, "id": 1}, ttl=ttl)
        if "error" in payload:
            raise SourceError("ethereum_rpc: " + str(payload["error"].get("message", payload["error"])))
        return payload["result"], meta

    def batch(self, calls, block, size=20):
        output, lineage = [], []
        for start in range(0, len(calls), size):
            subset = calls[start:start + size]
            body = [{"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": to, "data": data}, block], "id": index + 1}
                    for index, (to, data) in enumerate(subset)]
            payload, meta = self.context.json("ethereum_rpc", self.endpoint, method="POST", body=body)
            lineage.append(meta["file_path"])
            if not isinstance(payload, list):
                raise SourceError("ethereum_rpc: batch unavailable: " + str(payload.get("error", "unknown response")))
            ordered = {row["id"]: row for row in payload}
            for index in range(len(subset)):
                result = ordered.get(index + 1, {})
                if "result" not in result:
                    raise SourceError("ethereum_rpc: call error: " + str(result.get("error", "missing response")))
                output.append(result["result"])
        return output, lineage


def fetch(context, endpoint="https://ethereum-rpc.publicnode.com", *, pool_specs=None, tokens=None,
          expected_chain_id=1, network='eth', snapshot_name='onchain_pool_snapshot', gas_name='gas_block_snapshot'):
    rpc = RPC(context, endpoint)
    chain, chain_meta = rpc.request("eth_chainId", [], ttl=86400)
    if int(chain, 16) != expected_chain_id:
        raise SourceError(f"ethereum_rpc: expected chainId={expected_chain_id}")
    block, block_meta = rpc.request("eth_getBlockByNumber", ["finalized", False], ttl=30)
    tag = block["number"]
    timestamp = pd.to_datetime(int(block["timestamp"], 16), unit="s", utc=True).isoformat()
    pool_specs = specs() if pool_specs is None else pool_specs
    tokens = TOKENS if tokens is None else tokens
    calls = [(FACTORY, selector("getPool(address,address,uint24)") + address_word(p["base_address"]) + address_word(p["quote_address"]) + word(p["fee_tier"])) for p in pool_specs]
    addresses, lineage = rpc.batch(calls, tag)
    found = []
    for spec, result in zip(pool_specs, addresses):
        address = "0x" + result[-40:]
        if int(address, 16):
            found.append({**spec, "address": address.lower()})
    calls = []
    for pool in found:
        calls += [(pool["address"], selector(signature)) for signature in ["token0()", "token1()", "fee()", "slot0()", "liquidity()"]]
    results, more = rpc.batch(calls, tag)
    lineage += more
    decimals_result, token_lineage = rpc.batch([(address, selector("decimals()")) for address in tokens.values()], tag)
    decimals = {address: words(result)[0] for address, result in zip(tokens.values(), decimals_result)}
    rows = []
    for index, pool in enumerate(found):
        token0, token1, fee, slot, liquidity = results[index * 5:(index + 1) * 5]
        token0, token1 = "0x" + token0[-40:].lower(), "0x" + token1[-40:].lower()
        if {token0, token1} != {pool["base_address"], pool["quote_address"]} or words(fee)[0] != pool["fee_tier"]:
            raise SourceError("ethereum_rpc: pool token/fee verification failed")
        state = words(slot)
        d0, d1 = decimals[token0], decimals[token1]
        raw_ratio = (state[0] / 2**96)**2
        p1_per_0 = raw_ratio * 10**(d0 - d1)
        inverted = pool["base_address"] != token0
        rows.append({**pool, "chain_id":expected_chain_id,"network":network,"token0": token0, "token1": token1, "decimals0": d0, "decimals1": d1,
                     "inverted": inverted, "p0": 1 / p1_per_0 if inverted else p1_per_0,
                     "sqrt_price_x96": str(state[0]), "tick": signed(state[1], 24), "liquidity_raw": str(words(liquidity)[0]),
                     "block_number": int(tag, 16), "block_hash": block["hash"], "data_asof": timestamp,
                     "source": "ethereum_rpc", "available_at": datetime.now(timezone.utc).isoformat()})
    frame = pd.DataFrame(rows)
    context.frame(snapshot_name, frame, "ethereum_rpc", endpoint, start=timestamp, end=timestamp,
                  lineage=[chain_meta["file_path"], block_meta["file_path"], *lineage, *token_lineage])
    gas = pd.DataFrame([{"timestamp": pd.Timestamp(timestamp), "block_number": int(tag, 16),
                         "base_fee_gwei": int(block.get("baseFeePerGas", "0x0"), 16) / 1e9, "source": "ethereum_rpc"}])
    context.frame(gas_name, gas, "ethereum_rpc", endpoint, start=timestamp, end=timestamp, lineage=[block_meta["file_path"]])
    return rows, rpc, coverage_row("ethereum_rpc", "pool_snapshot", "observed", frame, "Factory-verified token0/token1/fee; one finalized block; raw integers stored as strings.")


def fetch_ticks(context, rpc, pool, quote_usd, *, half_span_ticks=5000):
    spacing = {100: 1, 500: 10, 3000: 60, 10000: 200}[pool["fee_tier"]]
    current = pool["tick"]
    low, high = max(-887272, current - half_span_ticks), min(887272, current + half_span_ticks)
    word_low, word_high = (low // spacing) >> 8, (high // spacing) >> 8
    keys = list(range(word_low, word_high + 1))
    results, lineage = rpc.batch([(pool["address"], selector("tickBitmap(int16)") + word(index)) for index in keys], hex(pool["block_number"]))
    initialized = []
    for position, result in zip(keys, results):
        bitmap = words(result)[0]
        initialized += [(position * 256 + bit) * spacing for bit in range(256)
                        if bitmap & (1 << bit) and low <= (position * 256 + bit) * spacing <= high]
    results, tick_lineage = rpc.batch([(pool["address"], selector("ticks(int24)") + word(index)) for index in initialized], hex(pool["block_number"]))
    net = {tick: signed(words(result)[1], 128) for tick, result in zip(initialized, results)}
    active, current_liquidity = {}, int(pool["liquidity_raw"])
    running = current_liquidity
    for tick in sorted(t for t in initialized if t > current):
        running += net[tick]
        active[tick] = running
    running = current_liquidity
    for tick in sorted((t for t in initialized if t <= current), reverse=True):
        active[tick] = running
        running -= net[tick]
    root_raw = int(pool["sqrt_price_x96"]) / 2**96
    factor = quote_usd / (root_raw * 10**pool["decimals0"]) if pool["inverted"] else quote_usd * root_raw / 10**pool["decimals1"]
    rows = []
    for tick, result in zip(initialized, results):
        values = words(result)
        p1_per_0 = np.exp(tick * np.log(1.0001)) * 10**(pool["decimals0"] - pool["decimals1"])
        rows.append({"pool_id": pool["id"], "tick": tick, "price": 1 / p1_per_0 if pool["inverted"] else p1_per_0,
                     "liquidity_raw": str(active[tick]), "liquidity_net_raw": str(net[tick]), "liquidity_gross_raw": str(values[0]),
                     "liquidity_normalized_usd": float(active[tick] * factor), "data_asof": pool["data_asof"],
                     "block_number": pool["block_number"], "source": "ethereum_rpc"})
    if any(int(row["liquidity_raw"]) < 0 for row in rows):
        raise SourceError("ethereum_rpc: negative reconstructed tick liquidity")
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=["pool_id", "tick", "price", "liquidity_raw", "liquidity_net_raw", "liquidity_gross_raw",
                                      "liquidity_normalized_usd", "data_asof", "block_number", "source"])
    context.frame("ticks_" + pool["id"], frame, "ethereum_rpc", rpc.endpoint, start=pool["data_asof"], end=pool["data_asof"], lineage=[*lineage, *tick_lineage])
    return frame, float(current_liquidity * factor), coverage_row("ethereum_rpc", "ticks_" + pool["id"], "window_snapshot", frame,
                                                                 "Current initialized-tick window only; never assigned backward to historical dates.")


def fetch_events(context, rpc, pool, *, from_block, to_block, max_chunks=20, chunk_size=1000):
    """Resume a bounded event backfill. A request cap always remains explicitly partial."""
    name = "events_" + pool["id"]
    if from_block < 0 or to_block < from_block or to_block > pool["block_number"]:
        raise ValueError("Events require an ordered range ending at or before the finalized snapshot")
    checkpoint = context.checkpoint_value(name) or {}
    if checkpoint.get("requested_start_block") != from_block:
        checkpoint = {"next_block": from_block, "parts": []}
    cursor, parts = max(from_block, checkpoint["next_block"]), checkpoint["parts"]
    topics = ["0x" + keccak(signature.encode()).hex() for signature in EVENTS.values()]
    def logs(start, end):
        try:
            payload, meta = rpc.request("eth_getLogs", [{"address": pool["address"], "fromBlock": hex(start), "toBlock": hex(end), "topics": [topics]}])
            return [meta["file_path"]]
        except SourceError as exc:
            message = str(exc).lower()
            # Split provider range/result caps, but do not amplify rate-limit failures.
            if start == end or not any(text in message for text in ["range", "too many", "limit exceeded", "response size"]):
                raise
            middle = (start + end) // 2
            return logs(start, middle) + logs(middle + 1, end)
    for _ in range(max_chunks):
        if cursor > to_block:
            break
        end = min(to_block, cursor + chunk_size - 1)
        parts.extend(logs(cursor, end))
        context.checkpoint(name, {"next_block": end + 1, "parts": parts, "requested_start_block": from_block,
                                  "requested_end_block": to_block, "complete": end >= to_block})
        cursor = end + 1
    rows = []
    topic_names = dict(zip(topics, EVENTS))
    import json
    for part in parts:
        payload = json.loads((context.root / part).read_text(encoding="utf-8"))["result"]
        for event in payload:
            if not from_block <= int(event["blockNumber"], 16) <= to_block:
                continue
            values = words(event["data"])
            kind = topic_names[event["topics"][0]]
            row = {"pool_id": pool["id"], "event": kind, "block_number": int(event["blockNumber"], 16),
                   "block_hash": event["blockHash"], "transaction_hash": event["transactionHash"], "log_index": int(event["logIndex"], 16),
                   "removed": event.get("removed", False), "data_raw": event["data"], "topics_raw": json.dumps(event["topics"]),
                   "source": "ethereum_rpc"}
            if kind == "swap":
                row.update(amount0_raw=str(signed(values[0])), amount1_raw=str(signed(values[1])), sqrt_price_x96=str(values[2]), liquidity_raw=str(values[3]), tick=signed(values[4], 24))
                ratio = (values[2] / 2**96)**2 * 10**(pool["decimals0"] - pool["decimals1"])
                row["price_quote_per_base"] = 1 / ratio if pool["inverted"] else ratio
            else:
                offset = 1 if kind == "mint" else 0
                row.update(tick_lower=signed(int(event["topics"][2], 16), 24), tick_upper=signed(int(event["topics"][3], 16), 24),
                           liquidity_raw=str(values[offset]), amount0_raw=str(values[offset + 1]), amount1_raw=str(values[offset + 2]))
            row["amount0"] = int(row["amount0_raw"]) / 10**pool["decimals0"]
            row["amount1"] = int(row["amount1_raw"]) / 10**pool["decimals1"]
            row["amount_base"] = row["amount1"] if pool["inverted"] else row["amount0"]
            row["amount_quote"] = row["amount0"] if pool["inverted"] else row["amount1"]
            rows.append(row)
    frame = pd.DataFrame(rows)
    if len(frame):
        frame = frame.loc[~frame.removed].drop_duplicates(["transaction_hash", "log_index"]).sort_values(["block_number", "log_index"])
    else:
        frame = pd.DataFrame(columns=["pool_id", "event", "block_number", "block_hash", "transaction_hash", "log_index", "removed", "data_raw", "topics_raw", "source"])
    context.frame(name, frame, "ethereum_rpc", rpc.endpoint, start=str(from_block), end=str(min(cursor - 1, to_block)), lineage=parts)
    status = "complete_requested_window" if cursor > to_block else "partial_checkpointed"
    return frame, coverage_row("ethereum_rpc", name, status, frame, "Block ranges, not timestamps; raw swap/mint/burn events; no fee/USD interpolation.",
                               requested_start_block=from_block, requested_end_block=to_block, next_block=cursor)
