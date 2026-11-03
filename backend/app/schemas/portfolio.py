"""Portfolio HTTP contracts; weights and returns are decimal fractions."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator


class PortfolioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_mode: Literal["real", "synthetic"] = "real"
    company_ids: list[int] = Field(default_factory=list, max_length=40)
    start_date: date = date(2024, 1, 2)
    end_date: date = date(2024, 12, 31)
    as_of: date = date(2025, 1, 2)
    risk_aversion: FiniteFloat = Field(3, ge=0, le=10000)
    carbon_penalty: FiniteFloat = Field(0.1, ge=0, le=10)
    long_gross: FiniteFloat = Field(0.5, gt=0, le=2)
    short_gross: FiniteFloat = Field(0.5, gt=0, le=2)
    max_weight: FiniteFloat = Field(0.25, gt=0, le=1)
    selection: Literal["auto", "manual"] = "auto"
    long_ids: list[int] = Field(default_factory=list, max_length=40)
    short_ids: list[int] = Field(default_factory=list, max_length=40)
    carbon_metric: Literal["scope1+2-market-based"] = "scope1+2-market-based"
    penalties: list[FiniteFloat] = Field(
        default_factory=lambda: [0, 0.01, 0.05, 0.1, 0.25], min_length=1, max_length=20
    )
    min_assets: int = Field(4, ge=2, le=40)
    min_candidates: int = Field(2, ge=1, le=20)
    min_observations: int = Field(60, ge=20, le=5000)
    shrinkage: FiniteFloat = Field(0.05, ge=0, le=1)

    @model_validator(mode="after")
    def coherent(self):
        if not date(1900, 1, 1) <= self.start_date < self.end_date < self.as_of <= date(2199, 12, 31):
            raise ValueError("Require 1900 <= start_date < end_date < as_of <= 2199")
        for values in (self.company_ids, self.long_ids, self.short_ids):
            if len(set(values)) != len(values) or any(i <= 0 for i in values):
                raise ValueError("Company IDs must be positive and unique")
        if set(self.long_ids) & set(self.short_ids):
            raise ValueError("Long and short candidate groups must be disjoint")
        if self.selection == "auto" and (self.long_ids or self.short_ids):
            raise ValueError("Automatic selection cannot include manual candidate groups")
        if self.selection == "manual" and (not self.long_ids or not self.short_ids):
            raise ValueError("Manual selection requires both candidate groups")
        if any(p < 0 or p > 10 for p in self.penalties):
            raise ValueError("Sensitivity penalties must lie in [0,10]")
        return self


class CompanyChoice(BaseModel):
    id: int
    name: str
    sector: str


class Readiness(BaseModel):
    status: Literal["ready", "insufficient", "infeasible", "invalid_inputs"]
    data_mode: str
    synthetic: bool
    provenance: str
    blockers: list[str]
    available_companies: list[CompanyChoice]
    selected_count: int
    eligible_count: int
    price_count: int
    adjusted_price_count: int
    emission_count: int
    aligned_observations: int
    long_ids: list[int] = Field(default_factory=list)
    short_ids: list[int] = Field(default_factory=list)


class AssetInput(BaseModel):
    company_id: int
    name: str
    sector: str
    expected_return_annual: float
    carbon_score: float
    emissions_tco2e: float
    original_emission: dict
    price_source: str
    emission_source: str
    disclosure_date: date
    disclosure_year: int
    dropped_return_intervals: int


class Estimates(BaseModel):
    start_date: date
    end_date: date
    as_of: date
    observations: int
    interval_start: date
    interval_end: date
    assets: list[AssetInput]
    covariance_annual: list[list[float]]
    shrinkage: float
    covariance_repair: str
    selection_method: str
    units: str = "annual arithmetic return; annual variance; dimensionless relative carbon score"


class Position(BaseModel):
    company_id: int
    name: str
    sleeve: Literal["long", "short"]
    weight: float
    carbon_score: float
    emissions_tco2e: float


class PortfolioResult(BaseModel):
    carbon_penalty: float
    positions: list[Position]
    expected_return_annual: float
    variance_annual: float
    volatility_annual: float
    carbon_exposure_score: float
    long_exposure: float
    short_exposure: float
    gross_exposure: float
    net_exposure: float
    objective_value: float
    solver: str
    solver_status: str
    max_constraint_violation: float


class Difference(BaseModel):
    expected_return_annual: float
    volatility_annual: float
    carbon_exposure_score: float
    long_exposure: float
    short_exposure: float
    composition_l1: float
    weights: dict[int, float]


class Comparison(BaseModel):
    traditional: PortfolioResult
    carbon_aware: PortfolioResult
    difference: Difference


class Sensitivity(BaseModel):
    portfolios: list[PortfolioResult]
    carbon_nonincreasing: bool
    carbon_reduced: bool
    tolerance: float


class PortfolioResponse(BaseModel):
    status: Literal["success", "insufficient", "infeasible", "invalid_inputs", "solver_error"]
    message: str
    configuration: PortfolioRequest
    readiness: Readiness
    estimates: Estimates | None = None
    portfolio: PortfolioResult | None = None
    comparison: Comparison | None = None
    sensitivity: Sensitivity | None = None
    warnings: list[str]


class PortfolioReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_dates: list[date]
    price_source_id: int
    emission_source_id: int
    methodology: str
    adjustment_verified: bool = False
    carbon_period_verified: bool = False
    comparability_group: str | None = None
