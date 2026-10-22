"""Explicit API contracts. Monetary returns are fractions of initial capital."""
from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_default=True)


class SimulationRequest(ApiModel):
    pool: str = Field(default="weth-usdc-500", min_length=1, max_length=80)
    capital: float = Field(default=50000, ge=1, le=100_000_000)
    horizon_days: int = Field(default=60, ge=1, le=365)
    vol_annual: float = Field(default=0.65, ge=0, le=5)
    gas_usd: float = Field(default=15, ge=0, le=1_000_000)
    risk_max_exit_prob: float = Field(default=0.4, ge=0, le=1)
    min_rebalance_gap_days: int = Field(default=7, ge=1, le=365)
    price_model: Literal["gbm", "bootstrap", "garch"] = "gbm"
    n_paths: int = Field(default=300, ge=1, le=5000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    path_index: int = Field(default=0, ge=0)
    max_rebalances: int = Field(default=52, ge=0, le=365)
    rebalance_slippage_bps: float = Field(default=0, ge=0, le=1000)
    min_half_width: float = Field(default=0.005, ge=1e-6, le=20)
    max_half_width: float | None = Field(default=None, ge=1e-6, le=20)
    calibration_asof: AwareDatetime | None = None
    bootstrap_mean_block_days: float = Field(default=10, ge=1, le=365)

    @model_validator(mode="after")
    def check_budget(self):
        if self.path_index >= self.n_paths:
            raise ValueError("path_index phải nhỏ hơn n_paths.")
        if self.n_paths * self.horizon_days > 1_000_000:
            raise ValueError("n_paths × horizon_days không được vượt 1.000.000; hãy giảm quy mô mô phỏng.")
        if self.max_half_width is not None and self.max_half_width < self.min_half_width:
            raise ValueError("max_half_width phải lớn hơn hoặc bằng min_half_width.")
        if self.calibration_asof is not None:
            self.calibration_asof = self.calibration_asof.astimezone(timezone.utc)
        return self


class Pool(ApiModel):
    id: str
    label: str
    base: str
    quote: str
    fee_tier: int
    fee_rate: float
    p0: float
    tvl_usd: float
    volume_24h_usd: float
    vol_realized_7d: float | None = None
    vol_realized_30d: float | None = None
    vol_assumption_annual: float | None
    data_asof: datetime | None = None
    data_kind: Literal["illustrative", "observed_snapshot"] = "illustrative"
    address: str | None = None
    block_number: int | None = None
    quote_usd: float | None = None
    background_liquidity_normalized_usd: float | None = None
    available_at: datetime | None = None
    history_start: datetime | None = None
    history_end: datetime | None = None
    sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    chain_id: int = 1
    network: str = 'eth'


class PoolList(ApiModel):
    pools: list[Pool]
    data_kind: Literal["illustrative", "observed_snapshot"] = "illustrative"
    data_label: str = "Dữ liệu minh họa"
    data_asof: datetime | None = None


class Metrics(ApiModel):
    half_width: float | None
    p_low: float
    p_high: float
    active_share: float = Field(ge=0, le=1)
    fees: float
    il: float
    gas: float
    net: float
    excess_vs_hodl: float
    q5: float
    exit_prob: float = Field(ge=0, le=1)
    cvar5: float | None = None
    rebalance_count: float = 0
    rebalance_cost: float = 0
    feasible: bool | None = None


class Strategy(Metrics):
    id: str
    label: str


class PnlPoint(ApiModel):
    day: int
    lp: float
    hodl: float


class StressPoint(ApiModel):
    shock: float
    lp_return: float | None
    hodl_return: float | None
    excess_vs_hodl: float | None
    status: str


class LiquidityTick(ApiModel):
    tick: int
    price: float
    liquidity: float


class RunMeta(ApiModel):
    run_id: str
    seed: int
    assumptions: dict[str, Any]
    data_asof: datetime | None = None
    model_version: str
    data_hash: str
    data_kind: Literal["illustrative", "observed_snapshot"] = "illustrative"
    data_label: str = "Dữ liệu minh họa"
    engine_status: Literal["mock_not_implemented", "numpy_simulation"] = "mock_not_implemented"
    optimization_status: Literal["mock_not_optimized", "feasible", "infeasible"] = "mock_not_optimized"
    messages: list[str] = Field(default_factory=list)


class SimulationResponse(ApiModel):
    optimum: Metrics | None
    sweep: list[Metrics]
    strategies: list[Strategy]
    sample_paths: list[list[float]]
    pnl_path: list[PnlPoint]
    stress: list[StressPoint]
    liquidity_ticks: list[LiquidityTick]
    meta: RunMeta


class RunRecord(ApiModel):
    config: SimulationRequest
    result: SimulationResponse


class BacktestQuery(ApiModel):
    start: date
    end: date
    strategy: Literal['full', 'fixed', 'vol_scaled', 'dynamic', 'optimizer'] = 'fixed'
    capital: float = Field(default=50000, ge=1, le=100_000_000)
    gas_usd: float = Field(default=15, ge=0, le=1_000_000)
    half_width: float = Field(default=.2, ge=.000001, le=20)
    min_rebalance_gap_days: int = Field(default=7, ge=1, le=365)
    max_rebalances: int = Field(default=52, ge=0, le=365)
    rebalance_slippage_bps: float = Field(default=0, ge=0, le=1000)
    risk_max_exit_prob: float = Field(default=.4, ge=0, le=1)
    concentration: float = Field(default=3, ge=.1, le=100)
    protocol_fee_fraction: float = Field(default=0, ge=0, le=1)
    volatility_window_days: int = Field(default=30, ge=7, le=90)
    price_source: Literal['pool', 'reference'] = 'pool'
    allow_partial: bool = True
    seed: int = Field(default=42, ge=0, le=2**32-1)


class BacktestRequest(BacktestQuery):
    pool: str = Field(min_length=1, max_length=80)


class BacktestRecord(ApiModel):
    kind: Literal['historical_backtest'] = 'historical_backtest'
    config: BacktestRequest
    result: dict[str, Any]
