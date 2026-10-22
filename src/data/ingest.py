"""Public-only ingestion CLI. Each unavailable source remains in coverage.json."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import duckdb
import pandas as pd

from src.data import binance, coingecko, defillama, ethereum, fred, geckoterminal
from src.data.common import Acquisition, atomic_bytes, coverage_row
from src.utils.config import state_directory
from src.utils.serialization import atomic_json, digest


def catalog(context):
    directory = context.root / "data/processed"
    files = sorted(directory.glob("*.parquet"))
    manifest = {path.stem: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    marker = directory / "catalog_manifest.json"
    old = json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else None
    destination = directory / "research.duckdb"
    if manifest != old or not destination.exists():
        with duckdb.connect(str(destination)) as connection:
            for path in files:
                # Validated local filenames, escaped paths, materialized portable tables.
                name = path.stem.replace('"', '""')
                location = path.resolve().as_posix().replace("'", "''")
                connection.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM read_parquet(\'{location}\')')
        atomic_json(marker, manifest)
    entry = context.log("local_normalization", "local://logged-parquet-catalog", destination, len(files), kind="mixed_catalog")
    entry["lineage"] = [context.reference(path) for path in files]
    return len(files)


def run(root, groups, *, event_chunks=2, event_start=None, event_end=None):
    context = Acquisition(root, secrets=[os.getenv("THE_GRAPH_API_KEY", ""), os.getenv("COINGECKO_API_KEY", "")])
    coverage_path = root / "data/coverage.json"
    previous = json.loads(coverage_path.read_text(encoding="utf-8")) if coverage_path.exists() else {}
    rows = {row["source"] + ":" + row["dataset"]: row for row in previous.get("datasets", [])}
    def add(records):
        if isinstance(records, dict): records = [records]
        for record in records:
            rows[record["source"] + ":" + record["dataset"]] = record
            print(record["source"], record["dataset"], record["status"], record["rows"], flush=True)
        atomic_json(coverage_path, {"mode": "public_only", "updated_at": datetime.now(timezone.utc).isoformat(), "datasets": list(rows.values())})
    def attempt(source, dataset, operation):
        try: return operation()
        except Exception as exc:
            add(coverage_row(source, dataset, "unavailable", note=context_safe(str(exc), context.secrets)))
            return None
    pool_specs = ethereum.specs()
    try:
        if "binance" in groups:
            for symbol in ["ETHUSDT", "BTCUSDT", "ETHUSDC", "USDCUSDT", "ETHBTC"]:
                for interval in ["1d", "1h"]:
                    result = attempt("binance", f"reference_{symbol.lower()}_{interval}", lambda: binance.fetch(context, symbol, interval))
                    if result: add(result[1])
        if "defillama" in groups:
            result = attempt("defillama", "pool_context", lambda: defillama.fetch(context, pool_specs))
            if result: add(result[1])
        if "coingecko" in groups:
            for coin in ["ethereum", "bitcoin", "usd-coin", "tether"]:
                result = attempt("coingecko", "usd_reference_" + coin, lambda: coingecko.fetch(context, coin))
                if result: add(result[1])
        if "fred" in groups:
            for series in ["DFF", "CPIAUCSL", "DTWEXBGS"]:
                result = attempt("fred", "macro_" + series.lower(), lambda: fred.fetch(context, series))
                if result: add(result[1])
        pools, rpc = [], None
        if groups & {"ethereum", "events", "geckoterminal"}:
            result = attempt("ethereum_rpc", "pool_snapshot", lambda: ethereum.fetch(context, os.getenv("ETHEREUM_RPC_URL") or "https://ethereum-rpc.publicnode.com"))
            if result:
                pools, rpc, row = result
                add(row)
        if "geckoterminal" in groups:
            for pool in pools:
                info = attempt("geckoterminal", "context_" + pool["id"], lambda: geckoterminal.metadata(context, pool))
                if info:
                    add(coverage_row("geckoterminal", "context_" + pool["id"], "observed", pd.DataFrame([info]), "Current aggregator TVL/volume/quote USD; availability time is download time."))
                    pool.update({key: info[key] for key in ["tvl_usd", "volume_24h_usd", "quote_usd"]})
                    pool["context_available_at"] = info["data_asof"]
            # Capture every pool's state before slow historical downloads. Public RPC
            # may require archive access once a pinned block becomes sufficiently old.
            if "ethereum" in groups:
                for pool in pools:
                    if "quote_usd" not in pool:
                        continue
                    result = attempt("ethereum_rpc", "ticks_" + pool["id"], lambda: ethereum.fetch_ticks(context, rpc, pool, pool["quote_usd"]))
                    if result:
                        _, normalized, row = result
                        pool["background_liquidity_normalized_usd"] = normalized
                        add(row)
            for pool in pools:
                for interval in ["day", "hour"]:
                    result = attempt("geckoterminal", ("history_" if interval == "day" else "hourly_") + pool["id"], lambda: geckoterminal.fetch(context, pool, interval))
                    if result: add(result[1])
        if "events" in groups:
            for pool in pools:
                # Default is an explicit sample, never called a complete historical backfill.
                start = event_start if event_start is not None else pool["block_number"] - 1999
                end = event_end if event_end is not None else pool["block_number"]
                result = attempt("ethereum_rpc", "events_" + pool["id"], lambda: ethereum.fetch_events(context, rpc, pool, from_block=start, to_block=end, max_chunks=event_chunks))
                if result: add(result[1])
        if pools and "geckoterminal" in groups:
            registry = root / "data/processed/pool_registry.json"
            atomic_json(registry, {"data_kind": "observed_snapshot", "pools": pools})
            version = registry.parent / "_versions/pool_registry" / (hashlib.sha256(registry.read_bytes()).hexdigest() + ".json")
            if not version.exists():
                atomic_bytes(version, registry.read_bytes())
            version_entry = context.log("ethereum_rpc+geckoterminal", "local://verified-pool-registry", version, len(pools), kind="observed_snapshot")
            entry = context.log("ethereum_rpc+geckoterminal", "local://verified-pool-registry", registry, len(pools), kind="observed_snapshot")
            entry["lineage"] = [context.reference(path) for path in [root / "data/processed/onchain_pool_snapshot.parquet",
                                 *[root / "data/processed" / ("context_" + pool["id"] + ".parquet") for pool in pools]] if path.exists()]
            version_entry["lineage"] = entry["lineage"]
        from src.data.quality import derive_features, audit
        derive_features(context)
        add(coverage_row("the_graph", "full_pool_history", "credentials_unavailable", note="Public-only run; full swaps/mints/burns and long poolDay/Hour history require an authenticated indexer or a lengthy RPC backfill. No key was borrowed."))
        for name in ["kaiko", "x", "reddit", "cryptopanic"]:
            add(coverage_row(name, "all", "not_implemented", note="Explicit interface stub; no data or synthetic replacements."))
        tables = catalog(context)
        lineage_path = root / "data/lineage.json"
        prior_lineage = json.loads(lineage_path.read_text(encoding="utf-8")) if lineage_path.exists() else {"artifacts": {}}
        atomic_json(lineage_path, {"artifacts": {**prior_lineage["artifacts"], **context.artifacts}})
        frame = pd.DataFrame(list(rows.values()))
        atomic_bytes(root / "data/coverage.csv", frame.to_csv(index=False).encode("utf-8-sig"))
        context.log("local_normalization", "local://coverage", coverage_path, len(frame), kind="coverage")
        context.log("local_normalization", "local://coverage", root / "data/coverage.csv", len(frame), kind="coverage")
        audit(root)
        print(json.dumps({"requests": context.requests, "cache_hits": context.cache_hits, "datasets": len(frame), "tables": tables}), flush=True)
    finally:
        context.close()


def context_safe(message, secrets):
    from src.data.common import safe_url
    for secret in secrets:
        message = message.replace(secret, "REDACTED") if secret else message
    return message


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=state_directory())
    parser.add_argument("--sources", default="binance,defillama,coingecko,fred,ethereum,geckoterminal,events")
    parser.add_argument("--event-chunks", type=int, default=2)
    parser.add_argument("--event-start-block", type=int)
    parser.add_argument("--event-end-block", type=int)
    args = parser.parse_args()
    allowed = {"binance", "defillama", "coingecko", "fred", "ethereum", "geckoterminal", "events"}
    groups = set(args.sources.split(","))
    if not groups <= allowed or args.event_chunks < 1:
        parser.error("Unknown source or invalid event chunk count")
    run(args.root, groups, event_chunks=args.event_chunks, event_start=args.event_start_block, event_end=args.event_end_block)


if __name__ == "__main__":
    main()
