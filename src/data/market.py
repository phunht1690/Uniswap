"""Load logged observed inputs without silently substituting illustrative values."""
import csv
import hashlib
import json
from io import BytesIO
import re
from pathlib import Path

import numpy as np
import pandas as pd

from api.schemas import Pool, PoolList
from src.data.history import HistoryUnavailable, history_snapshot
from src.utils.serialization import digest


class MarketUnavailable(ValueError):
    pass


def logged_payload(root, path):
    try:
        content = path.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        relative = path.relative_to(root).as_posix()
        with (root / "data/source_log.csv").open(encoding="utf-8", newline="") as stream:
            matches = [row for row in csv.DictReader(stream) if row["file_path"] == relative and row["sha256"] == sha]
        if not matches or matches[-1]["data_kind"] == "illustrative":
            raise MarketUnavailable(f"Dữ liệu {path.name} chưa có hash/nhãn quan sát khớp source_log; tải lại dữ liệu trước khi dùng API.")
        provenance = {key: matches[-1][key] for key in ["source", "endpoint", "data_kind"]}
        return content, sha, provenance
    except (OSError, KeyError) as exc:
        raise MarketUnavailable(f"Không đọc được dữ liệu hoặc source log cho {path.name}; chạy lại bộ tải và kiểm tra quyền thư mục data.") from exc


def aware(value):
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None or pd.isna(timestamp):
        raise MarketUnavailable("Snapshot thị trường cần timestamp UTC có múi giờ.")
    return timestamp.tz_convert("UTC")


def realized_vol(history, days):
    if history is None or len(history) < days + 1:
        return None
    sample = history.tail(days + 1)
    if not sample.index.to_series().diff().dropna().eq(pd.Timedelta(days=1)).all():
        return None
    return float(np.log(sample.price).diff().dropna().std(ddof=1) * np.sqrt(365))


class MarketCatalog:
    def __init__(self, root):
        self.root = Path(root)

    def registry(self):
        path = self.root / "data/processed/pool_registry.json"
        if not path.exists():
            return None
        content, sha, provenance = logged_payload(self.root, path)
        try:
            payload = json.loads(content)
            if payload["data_kind"] != "observed_snapshot" or not payload["pools"]:
                raise ValueError("empty/incorrect registry")
            pools = {}
            for row in payload["pools"]:
                name = row["id"]
                if not re.fullmatch(r"[a-z0-9-]{1,80}", name) or name in pools:
                    raise ValueError("invalid/duplicate pool ID")
                if not re.fullmatch(r"0x[0-9a-f]{40}", row["address"]):
                    raise ValueError("invalid address")
                for key in ["p0", "quote_usd", "background_liquidity_normalized_usd"]:
                    if not np.isfinite(row[key]) or row[key] <= 0:
                        raise ValueError("invalid price/liquidity unit")
                for key in ["tvl_usd", "volume_24h_usd"]:
                    if not np.isfinite(row[key]) or row[key] < 0:
                        raise ValueError("invalid TVL/volume")
                if not isinstance(row["inverted"], bool) or not all(isinstance(row[key], int) and 0 <= row[key] <= 36 for key in ["decimals0", "decimals1"]):
                    raise ValueError("invalid token decimals/order")
                if not 0 < int(row["sqrt_price_x96"]) < 2**160 or not 0 < int(row["liquidity_raw"]) < 2**128:
                    raise ValueError("invalid raw slot0/liquidity")
                ratio = (int(row["sqrt_price_x96"]) / 2**96)**2 * 10**(row["decimals0"] - row["decimals1"])
                expected_price = 1 / ratio if row["inverted"] else ratio
                if not np.isclose(expected_price, row["p0"], rtol=1e-10, atol=0):
                    raise ValueError("price differs from raw slot0")
                if row["fee_tier"] not in {100, 500, 3000, 10000} or row["fee_rate"] != row["fee_tier"] / 1e6:
                    raise ValueError("invalid fee")
                row = dict(row)
                row["available_at"] = max(aware(row["available_at"]), aware(row["context_available_at"]), aware(row["data_asof"])).isoformat()
                pools[name] = row
            return pools, sha, provenance
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise MarketUnavailable("Registry quan sát không hợp lệ hoặc thiếu context/liquidity; chạy lại ingestion đầy đủ. API không thay bằng preset giả.") from exc

    def history(self, pool, asof, required=False):
        path = self.root / "data/processed" / f"history_{pool}.parquet"
        if not path.exists() and not required:
            return None, None, []
        try:
            return history_snapshot(self.root, pool, asof)
        except (HistoryUnavailable, ValueError, OSError) as exc:
            raise MarketUnavailable(str(exc)) from exc

    def pool_list(self, registry):
        pools, _, _ = registry
        output = []
        for row in pools.values():
            history, _, _ = self.history(row["id"], row["available_at"])
            vol7, vol30 = realized_vol(history, 7), realized_vol(history, 30)
            output.append(Pool(**{key: row[key] for key in ["id", "label", "base", "quote", "fee_tier", "fee_rate", "p0", "tvl_usd", "volume_24h_usd", "address", "block_number", "quote_usd", "background_liquidity_normalized_usd"]},
                               vol_realized_7d=vol7, vol_realized_30d=vol30, vol_assumption_annual=vol30,
                               data_asof=aware(row["data_asof"]).to_pydatetime(), available_at=aware(row["available_at"]).to_pydatetime(),
                               history_start=history.index.min().to_pydatetime() if history is not None and len(history) else None,
                               history_end=history.index.max().to_pydatetime() if history is not None and len(history) else None,
                               sources=["ethereum_rpc" if row.get('chain_id',1)==1 else 'arbitrum_rpc', "geckoterminal"], data_kind="observed_snapshot",
                               chain_id=row.get('chain_id',1), network=row.get('network','eth'),
                               warnings=[] if vol30 is not None else ["Chưa đủ 31 ngày liên tiếp để tính vol 30d; cần nhập kịch bản biến động."]))
        return PoolList(pools=output, data_kind="observed_snapshot", data_label="Dữ liệu pool quan sát · kết quả là mô phỏng",
                        data_asof=min(pool.data_asof for pool in output))

    def ticks(self, pool):
        path = self.root / "data/processed" / ("ticks_" + pool["id"] + ".parquet")
        content, sha, provenance = logged_payload(self.root, path)
        try:
            frame = pd.read_parquet(BytesIO(content))
            required = {"tick", "price", "liquidity_raw", "liquidity_normalized_usd", "block_number", "data_asof"}
            if not required.issubset(frame.columns) or frame.empty or frame.tick.duplicated().any():
                raise ValueError("missing/duplicate ticks")
            if not frame.block_number.eq(pool["block_number"]).all() or not pd.to_datetime(frame.data_asof, utc=True).eq(aware(pool["data_asof"])).all():
                raise ValueError("tick snapshot differs from pool block")
            root_raw = int(pool["sqrt_price_x96"]) / 2**96
            factor = pool["quote_usd"] / (root_raw * 10**pool["decimals0"]) if pool["inverted"] else pool["quote_usd"] * root_raw / 10**pool["decimals1"]
            expected = int(pool["liquidity_raw"]) * factor
            if not np.isclose(expected, pool["background_liquidity_normalized_usd"], rtol=1e-10):
                raise ValueError("raw/normalized L mismatch")
            raw = frame.liquidity_raw.map(int)
            normalized = frame.liquidity_normalized_usd.to_numpy(dtype=float)
            prices = frame.price.to_numpy(dtype=float)
            if not np.isfinite(normalized).all() or not np.isfinite(prices).all() or (normalized < 0).any() or (prices <= 0).any() or raw.lt(0).any():
                raise ValueError("invalid tick values")
            if not np.allclose(raw.map(lambda value: float(value * factor)), normalized, rtol=1e-10):
                raise ValueError("tick L units differ")
            ratios = np.exp(frame.tick.to_numpy(dtype=float) * np.log(1.0001)) * 10**(pool["decimals0"] - pool["decimals1"])
            expected_prices = 1 / ratios if pool["inverted"] else ratios
            if not np.allclose(expected_prices, prices, rtol=1e-8, atol=0):
                raise ValueError("tick prices differ from decimals/order")
            ticks = [{"tick": int(row.tick), "price": float(row.price), "liquidity": float(row.liquidity_normalized_usd)} for row in frame.sort_values("tick").itertuples()]
            return ticks, sha, provenance
        except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
            raise MarketUnavailable("Tick snapshot không hợp lệ, sai block hoặc sai đơn vị L; tải lại snapshot trước khi mô phỏng.") from exc
