"""Read-only analytics; real data is the default and never mixed with synthetic."""

import json
import os
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from app.core.database import get_db
from app.models.entities import CarbonEmission, Company, Source, StockPrice
from app.services.analysis import DEFAULTS, MESSAGE, SECTORS, build_pairs, carbon_value, correlate, financial

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class Filters(BaseModel):
    start_year: int = 2023
    end_year: int = 2023
    company_id: int | None = None
    sector: Literal["Energy", "Industrials", "Pharmaceuticals"] | None = None
    metric: Literal["scope1", "scope2", "scope3", "scope1+2"] = "scope1+2"
    methodology: str | None = None
    basis: Literal["market-based", "location-based", "unknown"] = "market-based"
    alignment: Literal["point-in-time", "descriptive"] = "point-in-time"
    mode: Literal["cross-section", "panel"] = "cross-section"
    synthetic: bool = False
    min_pairs: int = Query(5, ge=3, le=10000)
    min_companies: int = Query(5, ge=3, le=10000)
    min_daily_returns: int = Query(60, ge=2, le=1000)
    min_panel_years: int = Query(3, ge=2, le=100)


class CorrelationOut(BaseModel):
    status: Literal["insufficient", "exploratory", "computable"]
    coefficient_pearson: float | None
    coefficient_spearman: float | None
    p_value_pearson: float | None
    p_value_spearman: float | None
    valid_pairs: int
    distinct_companies: int
    periods: list[int]
    exclusions: dict[str, int]
    warnings: list[str]
    points: list[dict]
    message: str | None = None
    alignment: str
    mode: str
    synthetic: bool
    thresholds: dict[str, int]


class FinancialOut(BaseModel):
    company_id: int
    company: str
    status: str
    blockers: list[str]
    daily: list[dict]
    periods: list[dict]
    cumulative_return: float | None
    annualized_volatility: float | None
    valid_returns: int
    price_count: int
    completeness: float | None


class ReturnsOut(BaseModel):
    synthetic: bool
    series: list[FinancialOut]
    carbon: list[dict]
    units: str = "tCO2e"


class ReadinessOut(BaseModel):
    status: str
    message: str | None
    company_count: int
    price_count: int
    adjusted_price_count: int
    emission_count: int
    missing_disclosure_dates: int
    available_years: list[int]
    sector_company_counts: dict[str, int]
    blockers: list[str]
    correlation: CorrelationOut


class ReviewWindow(BaseModel):
    expected_dates: list[date]
    price_source_id: int
    emission_source_id: int
    methodology: str
    adjustment_verified: bool = False
    comparability_group: str | None = None
    carbon_period_verified: bool = False


class DisplayReview(BaseModel):
    expected_dates: list[date]
    adjustment_verified: bool = False


class CompanyReview(BaseModel):
    years: dict[str, ReviewWindow] = {}
    display: DisplayReview | None = None


def load(db, f):
    if not 1900 <= f.start_year <= f.end_year <= 2199:
        raise HTTPException(422, "Require 1900 <= start_year <= end_year <= 2199")
    if f.mode == "cross-section" and f.start_year != f.end_year:
        # Readiness defaults remain useful: callers must explicitly select a cross-section year.
        raise HTTPException(422, "Cross-section requires start_year=end_year; choose panel for multiple years")
    sources = {s.id: s for s in db.scalars(select(Source).where(Source.synthetic == f.synthetic))}
    companies = [
        dict(id=c.id, name=c.name, sector=c.sector, synthetic=f.synthetic)
        for c in db.scalars(select(Company))
        if c.source_id in sources
        and (f.company_id is None or c.id == f.company_id)
        and (f.sector is None or c.sector == f.sector)
    ]
    ids = {c["id"] for c in companies}

    def rows(model):
        return [
            {**{col.name: getattr(r, col.name) for col in model.__table__.columns}, "synthetic": f.synthetic}
            for r in db.scalars(select(model))
            if r.company_id in ids and r.source_id in sources
        ]

    # Optional local analyst review, never generated from observation counts or exposed as request overrides.
    path = os.environ.get("ANALYSIS_REVIEW_FILE")
    try:
        reviews = json.loads(Path(path).read_text()) if path else {}
        selected_reviews = reviews.get("synthetic" if f.synthetic else "real", {})
        selected_reviews = {
            key: CompanyReview.model_validate(value).model_dump(mode="json", exclude_none=True)
            for key, value in selected_reviews.items()
        }
    except (OSError, ValueError, TypeError, AttributeError, ValidationError):
        raise HTTPException(503, "Analysis review file cannot be read; no verification inferred") from None
    return (
        companies,
        rows(StockPrice),
        [e for e in rows(CarbonEmission) if f.methodology is None or e["methodology"] == f.methodology],
        selected_reviews,
    )


def calculation(data, f):
    pairs, excluded = build_pairs(
        *data,
        start_year=f.start_year,
        end_year=f.end_year,
        mode=f.mode,
        alignment=f.alignment,
        metric=f.metric,
        basis=f.basis,
        min_daily_returns=f.min_daily_returns,
    )
    result = correlate(
        pairs, mode=f.mode, min_pairs=f.min_pairs, min_companies=f.min_companies, min_panel_years=f.min_panel_years
    )
    result["exclusions"].update(excluded)
    if f.alignment == "descriptive":
        result["warnings"].append("Retrospective reporting-year association: potential look-ahead bias")
    return dict(
        **result,
        message=MESSAGE if result["status"] == "insufficient" else None,
        alignment=f.alignment,
        mode=f.mode,
        synthetic=f.synthetic,
        thresholds={k: getattr(f, k) for k in DEFAULTS},
    )


@router.get("/correlations", response_model=CorrelationOut)
def correlations(f: Filters = Query(), db=Depends(get_db)):
    return calculation(load(db, f), f)


@router.get("/readiness", response_model=ReadinessOut)
def readiness(f: Filters = Query(), db=Depends(get_db)):
    data = load(db, f)
    companies, prices, emissions, _ = data
    result = calculation(data, f)
    inventory_blockers = []
    if len(companies) < f.min_companies:
        inventory_blockers.append(f"Only {len(companies)} companies; threshold {f.min_companies}")
    if not any(p["adjusted_close"] is not None for p in prices):
        inventory_blockers.append("No adjusted prices: no verified comparable total-return series")
    if len({e["year"] for e in emissions}) < f.min_panel_years and f.mode == "panel":
        inventory_blockers.append("Too few annual disclosure years for panel analysis")
    return dict(
        status=result["status"],
        message=result["message"],
        company_count=len(companies),
        price_count=len(prices),
        adjusted_price_count=sum(p["adjusted_close"] is not None for p in prices),
        emission_count=len(emissions),
        missing_disclosure_dates=sum(not e["disclosure_date"] for e in emissions),
        available_years=sorted({e["year"] for e in emissions}),
        sector_company_counts={s: sum(c["sector"] == s for c in companies) for s in SECTORS},
        blockers=inventory_blockers + list(result["exclusions"]) + result["warnings"],
        correlation=result,
    )


@router.get("/returns", response_model=ReturnsOut)
def returns(f: Filters = Query(), db=Depends(get_db)):
    companies, prices, emissions, reviews = load(db, f)
    series = []
    for c in companies:
        rows = [p for p in prices if p["company_id"] == c["id"] and f.start_year <= p["date"].year <= f.end_year]
        # Whole selection uses a separately reviewed calendar; annual correlation reviews are window-specific.
        review = reviews.get(str(c["id"]), {}).get("display", {})
        calendar = [date.fromisoformat(d) for d in review["expected_dates"]] if review.get("expected_dates") else None
        result = financial(
            rows,
            expected_dates=calendar,
            adjustment_verified=review.get("adjustment_verified", False),
            min_daily_returns=f.min_daily_returns,
        )
        series.append(dict(company_id=c["id"], company=c["name"], **result))
    carbon = []
    for e in emissions:
        if f.start_year <= e["year"] <= f.end_year:
            value, issue = carbon_value(e, f.metric, f.basis)
            carbon.append(dict(**e, value=value, issue=issue))
    return dict(synthetic=f.synthetic, series=series, carbon=carbon)


@router.get("/sectors", response_model=dict[str, CorrelationOut])
def sectors(f: Filters = Query(), db=Depends(get_db)):
    return {
        s: calculation(load(db, f.model_copy(update={"sector": s})), f.model_copy(update={"sector": s}))
        for s in SECTORS
        if f.sector is None or f.sector == s
    }
