"""Historical evaluation contracts. Estimates and subsequent P&L are separate."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.schemas.portfolio import Estimates, PortfolioResult, PortfolioReview


class BacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_mode: Literal["real", "synthetic"] = "real"
    start_date: date = date(2024, 1, 2)
    end_date: date = date(2025, 12, 31)
    window: Literal["rolling", "expanding"] = "rolling"
    training_sessions: int = Field(126, ge=20, le=756)
    frequency: Literal["monthly", "quarterly"] = "monthly"
    risk_aversion: FiniteFloat = Field(3, ge=0, le=10000)
    carbon_penalty: FiniteFloat = Field(.1, ge=0, le=10)
    penalties: list[FiniteFloat] = Field(default_factory=lambda: [0,.05,.1,.25], min_length=1, max_length=6)
    max_weight: FiniteFloat = Field(.25, gt=0, le=1)
    long_gross: FiniteFloat = Field(.5, gt=0, le=2)
    short_gross: FiniteFloat = Field(.5, gt=0, le=2)
    company_ids: list[int] = Field(default_factory=list, max_length=40)
    sectors: list[Literal["Energy", "Industrials", "Pharmaceuticals"]] = Field(default_factory=list, max_length=3)
    min_assets: int = Field(4, ge=2, le=40)
    min_candidates: int = Field(2, ge=1, le=20)
    min_observations: int = Field(60, ge=20, le=756)
    min_annual_observations: int = Field(252, ge=60, le=1000)
    shrinkage: FiniteFloat = Field(.05, ge=0, le=1)
    risk_free_rate: FiniteFloat | None = Field(0, gt=-1, le=1)

    @model_validator(mode="after")
    def coherent(self):
        if not date(1900,1,1) <= self.start_date < self.end_date <= date(2199,12,31):
            raise ValueError("Require 1900 <= evaluation start < end <= 2199")
        if (self.end_date-self.start_date).days > 1096:
            raise ValueError("Prototype evaluation range is limited to three years")
        if self.training_sessions < self.min_observations:
            raise ValueError("Training sessions must meet min_observations")
        if len(set(self.company_ids)) != len(self.company_ids) or any(i <= 0 for i in self.company_ids):
            raise ValueError("Selected company IDs must be positive and unique")
        if len(set(self.sectors)) != len(self.sectors) or any(p < 0 or p > 10 for p in self.penalties):
            raise ValueError("Sectors must be unique; penalties must lie in [0,10]")
        return self


class MembershipEvent(BaseModel):
    company_id: int
    effective: date
    published: date
    active: bool


class HistoricalReview(PortfolioReview):
    known_from: date
    historical_price_vintage_verified: bool = False
    evidence: str = Field(min_length=8)


class HistoryReviewFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calendar: list[date]
    coverage_start: date
    coverage_end: date
    universe_kind: Literal["historical-index-membership", "documented-research-universe"]
    universe_reference: str = Field(min_length=8)
    membership_history_verified: bool = False
    membership_events: list[MembershipEvent]
    reviews: dict[str,list[HistoricalReview]]


class BacktestReadiness(BaseModel):
    status: str
    synthetic: bool
    provenance: str
    blockers: list[str]
    company_count: int
    price_count: int
    adjusted_price_count: int
    scheduled_periods: int = 0
    decision_dates: list[date] = Field(default_factory=list)
    exclusions: dict[str,int] = Field(default_factory=dict)


class DailyPnl(BaseModel):
    date: date
    realized_return: float
    equity: float
    cumulative_return: float
    gross_exposure: float
    net_exposure: float
    long_positions: int
    short_positions: int


class FinancialMetrics(BaseModel):
    cumulative_return: float
    annualized_return: float | None
    annualized_volatility: float | None
    sharpe_ratio: float | None
    maximum_drawdown: float
    daily_observations: int
    evaluation_periods: int
    annualization_reason: str | None
    turnover_l1_total: float
    turnover_l1_average: float
    average_gross_exposure: float
    average_net_exposure: float
    average_long_positions: float
    average_short_positions: float


class Rebalance(BaseModel):
    decision_date: date
    training_start: date
    training_end: date
    holding_end: date
    eligible_ids: list[int]
    exclusions: dict[str,str]
    in_sample: Estimates
    target_portfolio: PortfolioResult
    pretrade_weights: dict[int,float]
    weight_changes: dict[int,float]
    turnover_l1: float
    sector_allocations: dict[str,dict[str,float]]
    realized_period_return: float


class CarbonMetrics(BaseModel):
    average_rebalance_score: float
    score_definition_changed: bool
    average_paired_difference_from_baseline: float | None = None


class StrategyHistory(BaseModel):
    carbon_penalty: float
    initial_date: date
    daily: list[DailyPnl]
    rebalances: list[Rebalance]
    financial: FinancialMetrics
    carbon: CarbonMetrics


class BacktestResponse(BaseModel):
    status: str
    message: str
    configuration: BacktestRequest
    readiness: BacktestReadiness
    strategies: list[StrategyHistory] = Field(default_factory=list)
    assumptions: list[str]
    warnings: list[str]
