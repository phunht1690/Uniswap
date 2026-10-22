"""Optional authenticated v3 indexer; public-only ingestion never invokes it."""
import json
import os
import re

import pandas as pd

from src.data.common import SourceError, coverage_row

DEFAULT_SUBGRAPH = "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
FIELDS = {
    "poolDayDatas": "id date sqrtPrice liquidity tick tvlUSD volumeUSD feesUSD txCount",
    "poolHourDatas": "id periodStartUnix sqrtPrice liquidity tick tvlUSD volumeUSD feesUSD txCount",
    "swaps": "id timestamp amount0 amount1 amountUSD sqrtPriceX96 tick logIndex transaction { id blockNumber }",
    "mints": "id timestamp amount amount0 amount1 amountUSD tickLower tickUpper logIndex transaction { id blockNumber }",
    "burns": "id timestamp amount amount0 amount1 amountUSD tickLower tickUpper logIndex transaction { id blockNumber }",
    "ticks": "id tickIdx liquidityGross liquidityNet",
}


def fetch(context, pool, entity="poolDayDatas", *, block_number=None, block_timestamp=None, max_pages=50):
    key = os.getenv("THE_GRAPH_API_KEY")
    if not key:
        raise SourceError("the_graph: THE_GRAPH_API_KEY unavailable; no authenticated request sent")
    if key not in context.secrets:
        context.secrets += (key,)
    if entity not in FIELDS or not re.fullmatch(r"0x[0-9a-f]{40}", pool["address"]):
        raise ValueError("Invalid entity or pool address")
    subgraph = os.getenv("UNISWAP_SUBGRAPH_ID") or DEFAULT_SUBGRAPH
    if not re.fullmatch(r"[A-Za-z0-9]+", subgraph):
        raise ValueError("Invalid subgraph ID")
    endpoint = f"https://gateway.thegraph.com/api/{key}/subgraphs/id/{subgraph}"
    def query(text, ttl=None):
        payload, meta = context.json("the_graph", endpoint, method="POST", body={"query": text}, ttl=ttl)
        if payload.get("errors"):
            raise SourceError("the_graph: GraphQL query rejected; inspect redacted raw response")
        return payload["data"], meta
    if block_number is None:
        data, _ = query("{ _meta { block { number hash } hasIndexingErrors } }", ttl=30)
        if data["_meta"]["hasIndexingErrors"]:
            raise SourceError("the_graph: indexer reports indexing errors")
        block_number = int(data["_meta"]["block"]["number"])
    name = "graph_" + entity.lower() + "_" + pool["id"]
    checkpoint = context.checkpoint_value(name) or {}
    if checkpoint.get("snapshot_block") != block_number:
        checkpoint = {"cursor": "", "parts": []}
    cursor, parts = checkpoint["cursor"], checkpoint["parts"]
    complete = checkpoint.get("complete", False)
    for _ in range(max_pages):
        if complete: break
        where = f'pool: {json.dumps(pool["address"])}, id_gt: {json.dumps(cursor)}'
        text = f'{{ {entity}(first: 1000, orderBy: id, orderDirection: asc, block: {{number: {int(block_number)}}}, where: {{{where}}}) {{ {FIELDS[entity]} }} }}'
        data, meta = query(text)
        page = data[entity]
        parts.append(meta["file_path"])
        if page:
            next_cursor = page[-1]["id"]
            if next_cursor <= cursor:
                raise SourceError("the_graph: non-advancing ID cursor")
            cursor = next_cursor
        complete = len(page) < 1000
        context.checkpoint(name, {"snapshot_block": block_number, "cursor": cursor, "parts": parts, "complete": complete})
    rows = []
    for part in parts:
        rows.extend(json.loads((context.root / part).read_text(encoding="utf-8"))["data"][entity])
    frame = pd.json_normalize(rows).drop_duplicates("id") if rows else pd.DataFrame()
    if len(frame):
        frame["pool_id"], frame["source"], frame["snapshot_block"] = pool["id"], "the_graph", block_number
        if entity in {"poolDayDatas", "poolHourDatas"}:
            time_column, seconds = ("date", 86400) if entity == "poolDayDatas" else ("periodStartUnix", 3600)
            frame["period_start"] = pd.to_datetime(frame[time_column].astype("int64"), unit="s", utc=True)
            frame["timestamp"] = frame.period_start + pd.Timedelta(seconds=seconds)
            ratio = (frame.sqrtPrice.map(int) / 2**96)**2 * 10**(pool["decimals0"] - pool["decimals1"])
            frame["price"] = 1 / ratio if pool["inverted"] else ratio
            frame["volume_usd"] = frame.volumeUSD.astype(float)
            frame["predictive_eligible"] = block_timestamp is not None
            if block_timestamp is not None:
                cutoff = pd.Timestamp(block_timestamp)
                if cutoff.tzinfo is None:
                    raise ValueError("block_timestamp must include a timezone")
                frame = frame.loc[frame.timestamp <= cutoff]
            # Drop an indexer's still-open period, never use its final close early.
            frame = frame.loc[frame.timestamp <= pd.Timestamp.now(tz="UTC")]
        elif "timestamp" in frame:
            frame["timestamp"] = pd.to_datetime(frame.timestamp.astype("int64"), unit="s", utc=True)
        context.frame(name, frame, "the_graph", endpoint, lineage=parts)
    return frame, coverage_row("the_graph", name, "complete_indexed_snapshot" if complete else "partial_checkpointed", frame,
                                "ID cursor with pinned indexer block; USD estimates are the subgraph's derived values. Authenticated live path requires user's key.", snapshot_block=block_number)
