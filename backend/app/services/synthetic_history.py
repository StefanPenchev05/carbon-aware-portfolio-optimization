"""Artificial market/universe/disclosure histories. No future-centered calibration."""

import numpy as np
import pandas as pd

SEED = 20261106


def dataset():
    calendar = [d.date().isoformat() for d in pd.bdate_range("2022-01-03", "2025-12-31")]
    rng = np.random.default_rng(SEED)
    factors = rng.normal(size=len(calendar) - 1)
    companies = []
    prices = []
    emissions = []
    reviews = {}
    events = []
    for i in range(8):
        cid = 20001 + i
        companies.append(
            dict(
                id=cid, name=f"SYNTHETIC History {i + 1:02}", sector=("Energy", "Industrials", "Pharmaceuticals")[i % 3]
            )
        )
        noise = rng.normal(size=len(calendar) - 1)
        level = 100.0
        for j, d in enumerate(calendar):
            if j:
                regime = 0 if d < "2024-01-01" else (1 if d < "2024-09-01" else 2)
                rho = (0.2, 0.75, -0.3 if i % 2 else 0.3)[regime]
                market = (0.0002, -0.0009, 0.0006)[regime]
                drift = (0.18 - 0.045 * i) / 252 + market
                sigma = (0.16 + 0.018 * i) * (1.4 if regime == 1 else 1) / np.sqrt(252)
                ret = drift + sigma * (rho * factors[j - 1] + np.sqrt(1 - rho * rho) * noise[j - 1])
                level *= 1 + ret
            prices.append(
                dict(
                    company_id=cid,
                    source_id=1,
                    synthetic=True,
                    date=d,
                    close=level,
                    adjusted_close=level,
                    currency="EUR",
                    adjustment_method="SYNTHETIC adjusted total-return unit",
                )
            )
        base = [900000, 600000, 180000, 40000, 700000, 120000, 350000, 80000][i]
        for year, published, mult in (
            (2021, "2022-03-01", 1.1),
            (2022, "2023-04-03", 1.0),
            (2023, "2024-07-15", 0.75 + 0.06 * i),
            (2024, "2025-08-15", 0.65 + 0.05 * i),
        ):
            emissions.append(
                dict(
                    company_id=cid,
                    source_id=1,
                    synthetic=True,
                    year=year,
                    scope1=base * mult * 0.7,
                    scope2=base * mult * 0.3,
                    scope3=None,
                    units="tCO2e",
                    scope1_status="reported",
                    scope2_status="reported",
                    scope3_status="unknown",
                    scope2_basis="market-based",
                    methodology="SYNTHETIC historical common boundary",
                    disclosure_date=published,
                    disclosure_reference="SYNTHETIC simulated publication",
                    notes="Artificial values; not actual issuer disclosures",
                )
            )
        reviews[str(cid)] = [
            dict(
                expected_dates=calendar,
                price_source_id=1,
                emission_source_id=1,
                methodology="SYNTHETIC historical common boundary",
                adjustment_verified=True,
                carbon_period_verified=True,
                comparability_group="SYNTHETIC comparable group",
                known_from="2021-12-01",
                historical_price_vintage_verified=True,
                evidence="SYNTHETIC no revisions/corporate-action surprises",
            )
        ]
        events.append(
            dict(
                company_id=cid,
                effective="2022-01-03" if i != 7 else "2024-07-01",
                published="2021-12-01" if i != 7 else "2024-06-15",
                active=True,
            )
        )
        if i == 6:
            events.append(dict(company_id=cid, effective="2025-07-01", published="2025-06-15", active=False))
    return dict(
        companies=companies,
        prices=prices,
        emissions=emissions,
        reviews=reviews,
        calendar=calendar,
        synthetic=True,
        sources={"1": f"SYNTHETIC historical scenario v1 seed {SEED}"},
        coverage_start=calendar[0],
        coverage_end=calendar[-1],
        membership_history_verified=True,
        historical_classification_verified=True,
        membership_events=events,
        universe_kind="documented-research-universe",
        universe_reference="SYNTHETIC predeclared research universe and dated entry/exit events; not STOXX",
        provenance=f"SYNTHETIC history v1 seed {SEED}; simulated weekdays, regime changes and dated disclosures",
    )
