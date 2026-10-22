"""All available public spot klines, cursor-paginated with no API key."""
import numpy as np
import pandas as pd

from src.data.common import SourceError, coverage_row

ENDPOINT = "https://data-api.binance.vision/api/v3/klines"
DURATIONS = {"1d": pd.Timedelta(days=1), "1h": pd.Timedelta(hours=1)}


def normalize(rows, symbol, interval):
    records = []
    for row in rows:
        unit = "us" if int(row[0]) >= 100_000_000_000_000 else "ms"
        opening = pd.to_datetime(int(row[0]), unit=unit, utc=True).as_unit("ns")
        values = [float(row[index]) for index in [1, 2, 3, 4, 5, 7]]
        if not np.isfinite(values).all() or min(values[:4]) <= 0 or min(values[4:]) < 0:
            raise SourceError("binance: invalid OHLCV row; no silent imputation")
        records.append({"timestamp": opening + DURATIONS[interval], "period_start": opening,
                        "open": values[0], "high": values[1], "low": values[2], "price": values[3],
                        "volume_base": values[4], "volume_quote": values[5], "trade_count": int(row[8]),
                        "symbol": symbol, "interval": interval, "source": "binance", "dataset_kind": "offchain_reference"})
    return pd.DataFrame(records)


def fetch(context, symbol, interval="1d", *, end=None):
    end = pd.Timestamp(end or pd.Timestamp.now(tz="UTC"))
    if end.tzinfo is None:
        raise ValueError("end must be timezone-aware")
    cursor, pages, lineage = 0, [], []
    dataset = f"reference_{symbol.lower()}_{interval}"
    while True:
        immutable = cursor + 1001 * int(DURATIONS[interval].total_seconds() * 1000) < int(end.timestamp() * 1000)
        payload, meta = context.json("binance", ENDPOINT, params={"symbol": symbol, "interval": interval, "limit": 1000, "startTime": cursor},
                                     ttl=None if immutable else 1800, start="earliest_available", end=end.isoformat())
        if not isinstance(payload, list):
            raise SourceError("binance: klines response is not an array")
        if not payload:
            break
        frame = normalize(payload, symbol, interval)
        frame = frame.loc[frame.timestamp <= end]
        pages.append(frame)
        lineage.append(meta["file_path"])
        unit_divisor = 1000 if int(payload[-1][0]) >= 100_000_000_000_000 else 1
        next_cursor = int(payload[-1][0]) // unit_divisor + 1
        if next_cursor <= cursor:
            raise SourceError("binance: non-advancing cursor")
        cursor = next_cursor
        context.checkpoint(dataset, {"cursor_ms": cursor, "raw_pages": lineage, "status": "in_progress", "end": end.isoformat()})
        if len(payload) < 1000 or pd.to_datetime(cursor, unit="ms", utc=True) >= end:
            break
    if not pages:
        return pd.DataFrame(), coverage_row("binance", dataset, "unavailable", note="No records returned")
    result = pd.concat(pages, ignore_index=True).drop_duplicates("timestamp", keep="last").sort_values("timestamp").reset_index(drop=True)
    context.frame(dataset, result, "binance", ENDPOINT, start=result.timestamp.min().isoformat(), end=result.timestamp.max().isoformat(), lineage=lineage)
    context.checkpoint(dataset, {"cursor_ms": cursor, "raw_pages": lineage, "status": "complete_available", "end": end.isoformat()})
    row = coverage_row("binance", dataset, "complete_available", result, "CEX reference; volume is not Uniswap pool volume. Timestamp is bar-close availability.")
    expected = pd.date_range(result.timestamp.min(), result.timestamp.max(), freq="D" if interval == "1d" else "h")
    row["missing_intervals"] = len(expected.difference(pd.DatetimeIndex(result.timestamp)))
    return result, row
