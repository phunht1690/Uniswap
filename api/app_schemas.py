"""Contracts for the RangeLab multi-page research workbench."""
from typing import Any,Literal
from pydantic import Field,model_validator
from api.schemas import ApiModel,SimulationRequest,BacktestRequest


class WorkbenchRequest(ApiModel):
    config: SimulationRequest = Field(default_factory=SimulationRequest)
    volume_daily_override_usd: float|None = Field(default=None,ge=0,le=1e12)
    rebalance_policy: Literal['none','weekly','threshold','hedged'] = 'none'
    delta_threshold: float = Field(default=.1,ge=.01,le=.5)
    market_snapshot_id: str|None = Field(default=None,pattern='^[0-9a-f]{64}$')


class LiveSnapshotRequest(ApiModel):
    pool: str = Field(pattern='^[a-z0-9-]{1,80}$')


class WorkbenchRecord(ApiModel):
    kind: Literal['workbench'] = 'workbench'
    config: WorkbenchRequest
    result: dict[str,Any]


class StressRequest(ApiModel):
    run_id: str = Field(pattern='^[0-9a-f]{64}$')
    price_shock_pct: float = Field(default=-30,ge=-90,le=200)
    volatility_multiplier: float = Field(default=1.5,ge=0,le=5)
    gas_multiplier: float = Field(default=2,ge=0,le=10)


class SensitivityRequest(ApiModel):
    run_id: str = Field(pattern='^[0-9a-f]{64}$')
    low_vol_pct: float = Field(default=30,ge=0,le=500)
    high_vol_pct: float = Field(default=120,ge=0,le=500)
    steps: int = Field(default=10,ge=2,le=20)

    @model_validator(mode='after')
    def ordered(self):
        if self.low_vol_pct>=self.high_vol_pct:raise ValueError('Biên volatility cần tăng dần.')
        return self


class BacktestComparison(BacktestRequest):
    half_width: float = Field(default=.15,ge=.000001,le=20)
    volatility_window_days: int = Field(default=14,ge=7,le=90)
    strategies: list[Literal['full','fixed','vol_scaled','dynamic','optimizer','hodl']] = Field(default_factory=lambda:['full','fixed','vol_scaled','dynamic','hodl'],min_length=1,max_length=6)
