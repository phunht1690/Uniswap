"""Read only provenance-logged daily history; acquisition belongs to step 3."""
import csv
import hashlib
from io import BytesIO
from pathlib import Path

import pandas as pd

from src.features.point_in_time import before_asof
from src.utils.serialization import digest


class HistoryUnavailable(ValueError):
    pass


def history_snapshot(root: Path, pool: str, asof):
    if asof is None:
        raise HistoryUnavailable("Bootstrap/GARCH cần calibration_asof có múi giờ; chỉ dùng dữ liệu trước mốc này.")
    path = root / "data/processed" / f"history_{pool}.parquet"
    log = root / "data/source_log.csv"
    if not path.exists() or not log.exists():
        raise HistoryUnavailable("Chưa có lịch sử pool được ghi nguồn. Thu thập dữ liệu ở bước 3 hoặc chọn price_model=gbm; không tự thay bằng lịch sử giả.")
    content = path.read_bytes()
    file_hash = hashlib.sha256(content).hexdigest()
    relative = path.relative_to(root).as_posix()
    with log.open(encoding="utf-8", newline="") as stream:
        matching = [row for row in csv.DictReader(stream) if row["file_path"] == relative and row["sha256"] == file_hash]
    if not matching:
        raise HistoryUnavailable("File lịch sử chưa có hash khớp trong data/source_log.csv; cần ghi nguồn trước khi chạy.")
    frame = pd.read_parquet(BytesIO(content))
    if "timestamp" not in frame:
        raise HistoryUnavailable("Lịch sử cần các cột timestamp UTC, price và volume_usd.")
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True, errors="raise")
    frame = before_asof(frame.set_index("timestamp"), asof)
    snapshot = [{"timestamp": index.isoformat(), "price": float(row.price), "volume_usd": float(row.volume_usd)}
                for index, row in frame.iterrows()]
    # Appending future records must not alter a point-in-time run or its hash.
    snapshot_hash = digest(snapshot)
    provenance = [{key: row.get(key, "") for key in ["source", "endpoint", "data_kind"]} for row in matching[-1:]]
    return frame, snapshot_hash, provenance
