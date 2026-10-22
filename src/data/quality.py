"""Lagged features and local integrity checks; no model fitting or OOS selection."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from src.data.common import atomic_bytes, record_count
from src.features.point_in_time import lagged_features
from src.utils.serialization import atomic_json


def derive_features(context):
    for path in sorted((context.root / "data/processed").glob("history_*.parquet")):
        frame = pd.read_parquet(path).set_index("timestamp")
        result = frame[["price", "volume_usd"]].copy()
        for days in [7, 30]:
            features = lagged_features(frame, days)
            # Rolling row windows are invalid across missing calendar days.
            consecutive = frame.index.to_series().diff().eq(pd.Timedelta(days=1)).rolling(days, min_periods=days).sum().eq(days).shift(1, fill_value=False)
            result[f"vol_realized_{days}d"] = features.vol_annual.where(consecutive)
            result[f"mean_volume_{days}d_usd"] = features.volume_usd.where(consecutive)
        result["feature_lag_periods"] = 1
        context.frame("features_" + path.stem.removeprefix("history_"), result.reset_index(), "local_normalization", "local://lagged-features",
                      kind="derived_lagged", lineage=[context.reference(path)])


def audit(root):
    """Verify every current payload's hash against the source ledger."""
    root = Path(root)
    log = root / "data/source_log.csv"
    rows = list(csv.DictReader(log.open(encoding="utf-8", newline=""))) if log.exists() else []
    known = {(row["file_path"], row["sha256"]) for row in rows}
    missing, invalid, checked, summary = [], [], 0, []
    for path in sorted((root / "data/raw").rglob("*")) + sorted((root / "data/processed").rglob("*")):
        if not path.is_file() or path.name in {".gitkeep", "request.json", "catalog_manifest.json"}:
            continue
        relative = path.relative_to(root).as_posix()
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if (relative, sha) not in known:
            missing.append(relative)
        checked += 1
        if path.suffix == ".parquet" and "_versions" not in path.parts:
            frame = pd.read_parquet(path)
            item = {"dataset": path.stem, "rows": len(frame), "sha256": sha}
            if "timestamp" in frame and len(frame):
                times = pd.to_datetime(frame.timestamp, utc=True)
                item.update(start=times.min().isoformat(), end=times.max().isoformat(), duplicates=int(times.duplicated().sum()))
                if item["duplicates"]: invalid.append(relative + ": duplicate timestamps")
            if path.stem.startswith(("history_", "hourly_", "reference_")) and len(frame):
                if not frame.timestamp.is_monotonic_increasing or (frame.price <= 0).any() or frame.price.isna().any():
                    invalid.append(relative + ": invalid price/time ordering")
            summary.append(item)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "files_checked": checked,
              "missing_hashes": missing, "invalid_datasets": invalid, "datasets": summary,
              "ok": not missing and not invalid}
    atomic_json(root / "data/quality_report.json", report)
    if not report["ok"]:
        raise ValueError(f"Data audit failed: {len(missing)} unlogged payloads, {len(invalid)} invalid datasets")
    return report


def repair_raw_row_counts(root):
    """Upgrade early probe metadata counts without changing observed payload bytes."""
    root = Path(root)
    log = root / "data/source_log.csv"
    rows = list(csv.DictReader(log.open(encoding="utf-8", newline="")))
    for row in rows:
        path = root / row["file_path"]
        if row["file_path"].startswith("data/raw/") and path.suffix == ".json" and path.exists():
            try: row["row_count"] = record_count(json.loads(path.read_text(encoding="utf-8")))
            except (ValueError, UnicodeDecodeError): row["row_count"] = 0
    import io
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    atomic_bytes(log, output.getvalue().encode("utf-8"))
    for path in (root / "data/raw").rglob("request.json"):
        metadata = json.loads(path.read_text(encoding="utf-8"))
        raw = root / metadata["file_path"]
        if raw.suffix == ".json":
            try: metadata["row_count"] = record_count(json.loads(raw.read_text(encoding="utf-8")))
            except (ValueError, UnicodeDecodeError): metadata["row_count"] = 0
            atomic_json(path, metadata)
    lineage_path = root / "data/lineage.json"
    if lineage_path.exists():
        lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
        artifacts = lineage["artifacts"]
        counts = {(row["file_path"], row["sha256"]): int(row["row_count"]) for row in rows}
        for relative, entry in list(artifacts.items()):
            if (relative, entry["sha256"]) in counts:
                entry["row_count"] = counts[(relative, entry["sha256"])]
            path = root / relative
            version = root / "data/processed/_versions" / path.stem / (entry["sha256"] + path.suffix)
            version_entry = artifacts.get(version.relative_to(root).as_posix())
            if version_entry is not None and entry.get("lineage"):
                version_entry["lineage"] = entry["lineage"]
        atomic_json(lineage_path, lineage)
