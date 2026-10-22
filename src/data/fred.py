"""Public FRED CSV controls; latest-vintage observations are descriptive only."""
from io import BytesIO

import pandas as pd

from src.data.common import coverage_row


def fetch(context, series="DFF"):
    endpoint = "https://fred.stlouisfed.org/graph/graph.csv"
    content, meta = context.request("fred", "GET", endpoint, params={"id": series}, extension="csv", ttl=86400)
    raw = pd.read_csv(BytesIO(content), na_values=".")
    value = raw.columns[-1]
    frame = pd.DataFrame({"timestamp": pd.to_datetime(raw.iloc[:, 0], utc=True), "value": pd.to_numeric(raw[value], errors="coerce"),
                          "series": series, "source": "fred", "vintage": "latest_download_not_realtime", "predictive_eligible": False})
    context.frame("macro_" + series.lower(), frame, "fred", endpoint, start=frame.timestamp.min().isoformat(), end=frame.timestamp.max().isoformat(), lineage=[meta["file_path"]])
    note = "Latest revised vintage; do not use for point-in-time predictive backtest without release/vintage data."
    if series == "DTWEXBGS":
        note += " Broad trade-weighted USD index, not ICE DXY."
    return frame, coverage_row("fred", "macro_" + series.lower(), "complete_available", frame, note)
