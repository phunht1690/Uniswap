"""Public pool OHLCV, with explicit provider limits and no filled candles."""
import numpy as np
import pandas as pd

from src.data.common import SourceError, coverage_row

BASE = "https://api.geckoterminal.com/api/v2/networks/eth/pools/"
HEADERS = {"Accept": "application/json;version=20230203"}


def metadata(context, pool):
    network=pool.get('network','eth')
    endpoint = BASE.replace('/eth/','/'+network+'/') + pool["address"]
    payload, meta = context.json("geckoterminal", endpoint, headers=HEADERS, ttl=1800)
    item = payload["data"]
    rel = item["relationships"]
    base = rel["base_token"]["data"]["id"].removeprefix(network+'_').lower()
    quote = rel["quote_token"]["data"]["id"].removeprefix(network+'_').lower()
    expected_dex = {'eth': 'uniswap_v3', 'arbitrum': 'uniswap_v3_arbitrum'}.get(network)
    if expected_dex is None or {base, quote} != {pool["base_address"], pool["quote_address"]} or rel["dex"]["data"]["id"] != expected_dex:
        raise SourceError("geckoterminal: pool identity mismatch")
    attributes = item["attributes"]
    quote_usd = float(attributes["quote_token_price_usd"] if quote == pool["quote_address"] else attributes["base_token_price_usd"])
    result = {"pool_id": pool["id"], "address": pool["address"], "tvl_usd": float(attributes["reserve_in_usd"]),
              "volume_24h_usd": float(attributes["volume_usd"]["h24"]), "quote_usd": quote_usd,
              "data_asof": meta["downloaded_at_utc"], "source": "geckoterminal"}
    context.frame("context_" + pool["id"], pd.DataFrame([result]), "geckoterminal", endpoint, lineage=[meta["file_path"]])
    return result


def normalize(rows, pool, timeframe, end):
    records = []
    duration = pd.Timedelta(days=1) if timeframe == "day" else pd.Timedelta(hours=1)
    for row in rows:
        opening = pd.to_datetime(int(row[0]), unit="s", utc=True).as_unit("ns")
        # The open bucket cannot enter a calibration sample.
        if opening + duration > end:
            continue
        values = np.asarray(row[1:6], dtype=float)
        if len(values) != 5 or not np.isfinite(values).all() or min(values[:4]) <= 0 or values[4] < 0:
            raise SourceError("geckoterminal: invalid OHLCV; no silent imputation")
        if values[1] < max(values[0], values[3]) or values[2] > min(values[0], values[3]):
            raise SourceError("geckoterminal: inconsistent OHLC bounds")
        records.append({"timestamp": opening + duration, "period_start": opening,
                        "open": values[0], "high": values[1], "low": values[2], "price": values[3],
                        "volume_usd": values[4], "pool_id": pool["id"], "interval": timeframe,
                        "source": "geckoterminal", "dataset_kind": "onchain_aggregator"})
    return pd.DataFrame(records)


def fetch(context, pool, timeframe="day", *, end=None, max_pages=200):
    if timeframe not in {"day", "hour"}:
        raise ValueError("timeframe must be day or hour")
    end = pd.Timestamp(end or pd.Timestamp.now(tz="UTC"))
    if end.tzinfo is None:
        raise ValueError("end must be timezone-aware")
    endpoint = BASE.replace('/eth/','/'+pool.get('network','eth')+'/') + pool["address"] + "/ohlcv/" + timeframe
    cursor, pages, lineage = None, [], []
    stop, stop_reason = "provider_limited", "Provider returned no older candles"
    for _ in range(max_pages):
        params = {"aggregate": 1, "limit": 1000, "currency": "token", "token": pool["base_address"], "include_empty_intervals": "false"}
        if cursor is not None:
            params["before_timestamp"] = cursor
        try:
            payload, meta = context.json("geckoterminal", endpoint, params=params, headers=HEADERS,
                                         ttl=1800 if cursor is None else 86400)
        except SourceError as exc:
            if not pages:
                raise
            stop = "provider_limited" if any(code in str(exc) for code in ["HTTP 401", "HTTP 403"]) else "partial_provider_error"
            stop_reason = str(exc)
            break
        rows = payload["data"]["attributes"]["ohlcv_list"]
        lineage.append(meta["file_path"])
        if not rows:
            break
        found = {payload.get("meta", {}).get(role, {}).get("address", "").lower() for role in ["base", "quote"]}
        if found != {pool["base_address"], pool["quote_address"]}:
            raise SourceError("geckoterminal: OHLCV token identity mismatch")
        # Request USD explicitly for volume; never infer USD from a stablecoin peg.
        usd_payload, usd_meta = context.json("geckoterminal", endpoint, params={**params, "currency": "usd"}, headers=HEADERS,
                                             ttl=1800 if cursor is None else 86400)
        lineage.append(usd_meta["file_path"])
        usd_rows = {int(row[0]): row for row in usd_payload["data"]["attributes"]["ohlcv_list"]}
        if any(int(row[0]) not in usd_rows for row in rows):
            raise SourceError("geckoterminal: USD and quote candles have mismatched timestamps")
        rows = [[*row[:5], usd_rows[int(row[0])][5]] for row in rows]
        pages.append(normalize(rows, pool, timeframe, end))
        next_cursor = min(int(row[0]) for row in rows) - 1
        if cursor is not None and next_cursor >= cursor:
            raise SourceError("geckoterminal: non-advancing cursor")
        cursor = next_cursor
        context.checkpoint("ohlcv_" + pool["id"] + "_" + timeframe, {"before_timestamp": cursor, "raw_pages": lineage, "status": "in_progress"})
    else:
        stop = "partial_page_limit"
    if not pages:
        return pd.DataFrame(), coverage_row("geckoterminal", pool["id"] + "_" + timeframe, "unavailable")
    result = pd.concat(pages, ignore_index=True).drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    name = "history_" + pool["id"] if timeframe == "day" else "hourly_" + pool["id"]
    context.frame(name, result, "geckoterminal", endpoint, start=result.timestamp.min().isoformat(), end=result.timestamp.max().isoformat(),
                  kind="onchain_aggregator", lineage=lineage)
    context.checkpoint("ohlcv_" + pool["id"] + "_" + timeframe, {"before_timestamp": cursor, "raw_pages": lineage, "status": stop})
    expected = pd.date_range(result.timestamp.min(), result.timestamp.max(), freq="D" if timeframe == "day" else "h")
    return result, coverage_row("geckoterminal", name, stop, result,
                                "All publicly returned candles; pool volume in USD, price in quote/base. Missing intervals remain gaps. Earlier history is not certified complete.",
                                missing_intervals=len(expected.difference(pd.DatetimeIndex(result.timestamp))), pages=len(lineage), stop_reason=stop_reason)
