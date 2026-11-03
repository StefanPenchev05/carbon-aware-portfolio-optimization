"""Coverage metrics describe records, not statistical readiness or assurance."""

import argparse
import json
from collections import Counter

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import CarbonEmission, Company, FXRate, ImportRun, IndexMembership, Source, StockPrice
from app.services.preparation import SCOPES, align_emissions, normalize_emissions, prepare_returns


def data_quality(db, synthetic=False):
    sources = {s.id: s for s in db.scalars(select(Source)).all()}
    companies = [c for c in db.scalars(select(Company)).all() if sources[c.source_id].synthetic == synthetic]
    result = []
    for company in companies:
        prices = [
            p
            for p in db.scalars(select(StockPrice).where(StockPrice.company_id == company.id)).all()
            if sources[p.source_id].synthetic == synthetic
        ]
        emissions = [
            e
            for e in db.scalars(select(CarbonEmission).where(CarbonEmission.company_id == company.id)).all()
            if sources[e.source_id].synthetic == synthetic
        ]
        values = [dict((col.name, getattr(e, col.name)) for col in CarbonEmission.__table__.columns) for e in emissions]
        missing = {s: sum(getattr(e, s) is None for e in emissions) for s in SCOPES}
        statuses = Counter(
            getattr(e, scope + "_status") for e in emissions for scope in SCOPES if getattr(e, scope) is not None
        )
        total = sum(statuses.values())
        usable_dates = set()
        return_issues = Counter()
        regimes = {(p.source_id, p.currency, p.adjustment_method) for p in prices}
        for source_id, currency, adjustment in regimes:
            selected = [
                dict(
                    company_id=company.id,
                    synthetic=synthetic,
                    source_id=p.source_id,
                    date=p.date,
                    close=p.close,
                    adjusted_close=p.adjusted_close,
                    currency=p.currency,
                    adjustment_method=p.adjustment_method,
                )
                for p in prices
                if (p.source_id, p.currency, p.adjustment_method) == (source_id, currency, adjustment)
            ]
            try:
                prepared = prepare_returns(selected)
            except ValueError as exc:
                return_issues[f"invalid price series: {exc}"] += len(selected)
                continue
            return_issues.update(r["return_issue"] for r in prepared if r["return_issue"])
            streams = {(e.source_id, e.scope2_basis, e.methodology) for e in emissions}
            for esource, basis, method in streams:
                stream = [
                    dict(e, synthetic=synthetic)
                    for e in values
                    if (e["source_id"], e["scope2_basis"], e["methodology"]) == (esource, basis, method)
                ]
                try:
                    for aligned in align_emissions(prepared, stream):
                        e = aligned["emission"]
                        if (
                            aligned["simple_return"] is not None
                            and e
                            and any(
                                e["normalized_scopes"][s] is not None and e[s + "_status"] == "reported" for s in SCOPES
                            )
                        ):
                            usable_dates.add((source_id, aligned["date"]))
                except ValueError:
                    return_issues["ambiguous disclosure vintage"] += 1
        result.append(
            dict(
                company_id=company.id,
                sector=company.sector,
                synthetic=synthetic,
                price_count=len(prices),
                emission_count=len(emissions),
                years=sorted({e.year for e in emissions}),
                price_start=min((p.date for p in prices), default=None),
                price_end=max((p.date for p in prices), default=None),
                missing_scope_values=missing,
                available_scopes=[s for s in SCOPES if any(getattr(e, s) is not None for e in emissions)],
                status_counts=dict(statuses),
                estimated_percent=100 * statuses["estimated"] / total if total else None,
                reported_percent=100 * statuses["reported"] / total if total else None,
                missing_publication_dates=sum(e.disclosure_date is None for e in emissions),
                unsupported_unit_records=sum(normalize_emissions(e)["normalization_issue"] is not None for e in values),
                currency_distribution=dict(Counter(p.currency for p in prices)),
                usable_matched_observations=len(usable_dates),
                return_exclusions=dict(return_issues),
                membership_snapshots=sum(
                    sources[m.source_id].synthetic == synthetic
                    for m in db.scalars(select(IndexMembership).where(IndexMembership.company_id == company.id)).all()
                ),
            )
        )
    runs = [r for r in db.scalars(select(ImportRun)).all() if r.synthetic == synthetic]
    fx = [f for f in db.scalars(select(FXRate)).all() if sources[f.source_id].synthetic == synthetic]
    statuses = Counter()
    for row in result:
        statuses.update(row["status_counts"])
    total = sum(statuses.values())
    currencies = Counter()
    missing = Counter()
    for row in result:
        currencies.update(row["currency_distribution"])
        missing.update(row["missing_scope_values"])
    return dict(
        synthetic=synthetic,
        company_count=len(companies),
        companies_by_sector={
            sector: sum(c.sector == sector for c in companies)
            for sector in ("Energy", "Industrials", "Pharmaceuticals")
        },
        companies_with_prices=sum(r["price_count"] > 0 for r in result),
        companies_with_emissions=sum(r["emission_count"] > 0 for r in result),
        price_observations=sum(r["price_count"] for r in result),
        emission_observations=sum(r["emission_count"] for r in result),
        currency_distribution=dict(currencies),
        missing_scope_values=dict(missing),
        available_scopes=sorted({s for r in result for s in r["available_scopes"]}),
        reporting_years=sorted({year for r in result for year in r["years"]}),
        scope_status_counts=dict(statuses),
        estimated_percent=100 * statuses["estimated"] / total if total else None,
        reported_percent=100 * statuses["reported"] / total if total else None,
        missing_publication_dates=sum(r["missing_publication_dates"] for r in result),
        usable_matched_observations=sum(r["usable_matched_observations"] for r in result),
        rejected_import_rows=sum(r.rejected for r in runs),
        rejected_import_attempts=sum(r.status == "rejected" for r in runs),
        fx_observations=len(fx),
        fx_currency_distribution=dict(Counter(f.quote_currency for f in fx)),
        fx_start=min((f.date for f in fx), default=None),
        fx_end=max((f.date for f in fx), default=None),
        companies=result,
        notes=[
            "Status percentages count non-null scope cells, not companies; repeated Scope 2-basis disclosures can repeat Scope 1.",
            "Matched counts are candidate return/disclosure pairs with any reported normalized scope; no claim of statistical readiness.",
            "Without an exchange calendar, weekday sessions are provisional. Historical membership is not an eligibility filter yet.",
            "Rejected rows count whole rolled-back CLI batches and repeat attempts; legacy imports have no audit records.",
        ],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps(data_quality(db, args.synthetic), default=str, indent=2))


if __name__ == "__main__":
    main()
