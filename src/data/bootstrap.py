"""Materialize clearly labelled local fixtures; never download market data."""
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from src.utils.config import load_config, make_directories, state_directory
from src.utils.serialization import atomic_json, digest

_lock = Lock()
LOG_FIELDS = ["source", "endpoint", "downloaded_at_utc", "period_start", "period_end", "row_count", "file_path", "sha256", "data_kind"]


def log_file(root: Path, path: Path, row_count: int) -> None:
    """Record local generation explicitly; no timestamp is a market-data as-of."""
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    log = root / "data/source_log.csv"
    prior = []
    if log.exists():
        with log.open(encoding="utf-8", newline="") as stream:
            prior = list(csv.DictReader(stream))
    relative = path.relative_to(root).as_posix()
    if any(row["sha256"] == sha and row["file_path"] == relative for row in prior):
        return
    with log.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LOG_FIELDS)
        if not prior:
            writer.writeheader()
        writer.writerow(dict(source="local_mock", endpoint="local://supplied-html-pool-presets",
                             downloaded_at_utc=datetime.now(timezone.utc).isoformat(),
                             period_start="", period_end="", row_count=row_count,
                             file_path=relative, sha256=sha, data_kind="illustrative"))


def bootstrap(root: Path | None = None) -> dict:
    """Cache raw JSON and Parquet and expose a local DuckDB catalog view."""
    root = root or state_directory()
    with _lock:
        make_directories(root)
        pools = load_config("pools")["pools"]
        payload = {"data_kind": "illustrative", "data_asof": None, "pools": pools}
        raw = root / "data/raw/mock/pools.json"
        parquet = root / "data/processed/mock_pools.parquet"
        catalog = root / "data/processed/catalog.duckdb"
        old = json.loads(raw.read_text(encoding="utf-8")) if raw.exists() else None
        changed = old != payload
        if changed:
            atomic_json(raw, payload)
        log_file(root, raw, len(pools))
        if changed or not parquet.exists():
            rows = [{**p, "data_kind": "illustrative", "data_asof": None} for p in pools]
            pq.write_table(pa.Table.from_pylist(rows), parquet)
        log_file(root, parquet, len(pools))
        if changed or not catalog.exists():
            with duckdb.connect(str(catalog)) as connection:
                location = parquet.resolve().as_posix().replace("'", "''")
                connection.execute(f"CREATE OR REPLACE TABLE mock_pools AS SELECT * FROM read_parquet('{location}')")
        log_file(root, catalog, len(pools))
        return {"data_kind": "illustrative", "rows": len(pools), "data_hash": digest(payload)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(bootstrap(), ensure_ascii=False))
    print("Dữ liệu minh họa cục bộ. Chưa tải dữ liệu lịch sử/on-chain; bộ tải thật thuộc bước 3.")
