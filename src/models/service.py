"""Content-addressed result storage independent of the HTTP transport."""
from pathlib import Path

from api.schemas import PoolList, RunRecord, SimulationRequest
from src.data.bootstrap import bootstrap
from src.data.history import HistoryUnavailable, history_snapshot
from src.data.market import MarketCatalog, MarketUnavailable, aware
from src.models.engine import MODEL_VERSION, numerical_versions, simulate
from src.utils.config import load_config
from src.utils.serialization import atomic_json, digest


class UnknownPool(ValueError):
    pass


class StageNotImplemented(ValueError):
    pass


class SimulationInputError(ValueError):
    pass


class SimulationService:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.settings = {name: load_config(name) for name in ["pools", "sources", "research"]}
        self.pools = {p["id"]: p for p in self.settings["pools"]["pools"]}
        self.dataset = bootstrap(state_dir)
        self.market = MarketCatalog(state_dir)

    def pool_list(self):
        observed = self.market.registry()
        if observed is not None:
            return self.market.pool_list(observed)
        rows = [{**{key: value for key, value in pool.items() if key != "vol_annual"},
                 "vol_assumption_annual": pool["vol_annual"]} for pool in self.pools.values()]
        return PoolList(pools=rows)

    def simulate(self, config: SimulationRequest):
        observed = self.market.registry()
        pools = self.pools if observed is None else observed[0]
        if config.pool not in pools:
            raise UnknownPool("Pool không tồn tại. Xem danh sách tại /api/v1/pools.")
        history, history_hash, provenance = None, None, []
        market = None
        if observed is not None:
            pool = pools[config.pool]
            available = aware(pool["available_at"])
            if config.calibration_asof is None:
                config = config.model_copy(update={"calibration_asof": available.to_pydatetime()})
            if aware(config.calibration_asof) < available:
                raise SimulationInputError(f"Snapshot pool/ticks chỉ biết từ {available.isoformat()}; không được dùng cho calibration_asof cũ hơn. Backtest cần snapshot lịch sử riêng.")
            history, history_hash, provenance = self.market.history(config.pool, config.calibration_asof, required=config.price_model != "gbm")
            ticks, ticks_hash, ticks_provenance = self.market.ticks(pool)
            market = {"ticks": ticks, "provenance": {"registry_hash": observed[1], "registry_source": observed[2],
                      "ticks_hash": ticks_hash, "ticks_source": ticks_provenance, "block_number": pool["block_number"],
                      "block_hash": pool["block_hash"], "available_at": pool["available_at"], "context_available_at": pool["context_available_at"]}}
        elif config.price_model != "gbm":
            try:
                history, history_hash, provenance = history_snapshot(self.state_dir, config.pool, config.calibration_asof)
            except (HistoryUnavailable, ValueError) as exc:
                raise SimulationInputError(str(exc)) from exc
        data_hash = digest({"market": market["provenance"] if market is not None else self.dataset["data_hash"],
                            "calibration_snapshot": history_hash, "calibration_provenance": provenance})
        run_id = digest({"config": config.model_dump(mode="json"), "data_hash": data_hash,
                         "settings": self.settings, "model_version": MODEL_VERSION,
                         "numerical_versions": numerical_versions(config.price_model)})
        path = self.state_dir / "outputs/runs" / f"{run_id}.json"
        if path.exists():
            return RunRecord.model_validate_json(path.read_text(encoding="utf-8")).result
        try:
            result = simulate(config, pools[config.pool], self.settings, run_id, data_hash, history, provenance, market)
        except ValueError as exc:
            raise SimulationInputError("Không thể chạy mô hình với dữ liệu/tham số hiện tại: " + str(exc)) from exc
        atomic_json(path, RunRecord(config=config, result=result).model_dump(mode="json"))
        return result

    def get_run(self, run_id: str) -> RunRecord:
        path = self.state_dir / "outputs/runs" / f"{run_id}.json"
        return RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
