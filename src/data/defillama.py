"""Pool TVL/volume context and all available TVL history; never use protocol APR."""
import pandas as pd

from src.data.common import coverage_row

POOLS = "https://yields.llama.fi/pools"


def fetch(context, pool_specs, *, context_name='defillama_pool_context'):
    payload, meta = context.json("defillama", POOLS, ttl=3600)
    matches = {}
    for spec in pool_specs:
        tokens = {spec["base_address"].lower(), spec["quote_address"].lower()}
        fee_percent = spec["fee_tier"] / 10000
        for row in payload.get("data", []):
            if row.get("chain") != spec.get('chain','Ethereum') or row.get("project") != "uniswap-v3":
                continue
            if set(t.lower() for t in row.get("underlyingTokens", [])) != tokens:
                continue
            try:
                fee = float(str(row.get("poolMeta", "")).replace("%", "").strip())
            except ValueError:
                continue
            if abs(fee - fee_percent) < 1e-9:
                matches[spec["id"]] = {"pool_id": spec["id"], "defillama_id": row["pool"],
                                        "tvl_usd": row.get("tvlUsd"), "volume_24h_usd": row.get("volumeUsd1d"),
                                        "fee_tier": spec["fee_tier"], "fetched_at": meta["downloaded_at_utc"], "source": "defillama"}
                break
    frame = pd.DataFrame(list(matches.values()))
    if len(frame):
        context.frame(context_name, frame, "defillama", POOLS, lineage=[meta["file_path"]])
    coverage = [coverage_row("defillama", "pool_context", "observed", frame, "Only TVL and volume retained; APY/APR columns excluded.")]
    for pool_id, record in matches.items():
        endpoint = "https://yields.llama.fi/chart/" + record["defillama_id"]
        try:
            data, history_meta = context.json("defillama", endpoint, ttl=3600)
            rows = [{"timestamp": pd.Timestamp(row["timestamp"]), "tvl_usd": float(row["tvlUsd"]),
                     "pool_id": pool_id, "source": "defillama"} for row in data.get("data", []) if row.get("tvlUsd") is not None]
            history = pd.DataFrame(rows)
            if len(history):
                history["timestamp"] = pd.to_datetime(history.timestamp, utc=True)
                history = history.sort_values("timestamp").drop_duplicates("timestamp")
                context.frame("tvl_" + pool_id, history, "defillama", endpoint, start=history.timestamp.min().isoformat(), end=history.timestamp.max().isoformat(), lineage=[history_meta["file_path"]])
            coverage.append(coverage_row("defillama", "tvl_" + pool_id, "complete_available", history, "Provider's available TVL history; not historical active liquidity or swap volume."))
        except Exception as exc:
            coverage.append(coverage_row("defillama", "tvl_" + pool_id, "unavailable", note=str(exc)))
    return matches, coverage
