"""Seeded artificial observations, never corporate evidence; no database writes."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261103


def dataset():
    calendar = [d.date() for d in pd.bdate_range("2024-01-02", "2024-12-31")]
    rng = np.random.default_rng(SEED)
    common = rng.normal(size=len(calendar) - 1)
    annual_means = [0.22, 0.18, 0.14, 0.10, 0.02, -0.02, -0.06, -0.10]
    annual_vols = [0.24, 0.20, 0.18, 0.16, 0.18, 0.22, 0.26, 0.30]
    carbon = [900000, 600000, 180000, 40000, 700000, 120000, 350000, 80000]
    companies, prices, emissions, reviews = [], [], [], {}
    for i in range(8):
        cid = 10001 + i
        companies.append(
            dict(
                id=cid, name=f"SYNTHETIC Company {i + 1:02}", sector=("Energy", "Industrials", "Pharmaceuticals")[i % 3]
            )
        )
        noise = 0.35 * common + np.sqrt(1 - 0.35**2) * rng.normal(size=len(calendar) - 1)
        noise = (noise - noise.mean()) / noise.std(ddof=1)
        returns = noise * annual_vols[i] / np.sqrt(252) + annual_means[i] / 252
        levels = np.r_[100, 100 * np.cumprod(1 + returns)]
        for d, level in zip(calendar, levels, strict=True):
            prices.append(
                dict(
                    company_id=cid,
                    source_id=1,
                    synthetic=True,
                    date=d.isoformat(),
                    close=float(level),
                    adjusted_close=float(level),
                    currency="EUR",
                    adjustment_method="SYNTHETIC total-return price",
                )
            )
        emissions.append(
            dict(
                company_id=cid,
                source_id=1,
                synthetic=True,
                year=2023,
                scope1=carbon[i] * 0.7,
                scope2=carbon[i] * 0.3,
                scope3=None,
                units="tCO2e",
                scope1_status="reported",
                scope2_status="reported",
                scope3_status="unknown",
                scope2_basis="market-based",
                methodology="SYNTHETIC consistent group boundary v1",
                disclosure_date="2024-09-01",
                disclosure_reference="SYNTHETIC disclosure; no real issuer",
                notes="Simulated observations; reported is a test field, not a real disclosure claim",
            )
        )
        reviews[str(cid)] = dict(
            expected_dates=[d.isoformat() for d in calendar],
            price_source_id=1,
            emission_source_id=1,
            methodology="SYNTHETIC consistent group boundary v1",
            adjustment_verified=True,
            carbon_period_verified=True,
            comparability_group="SYNTHETIC comparable consolidated calendar-year boundary",
        )
    return dict(
        companies=companies,
        prices=prices,
        emissions=emissions,
        reviews=reviews,
        sources={"1": f"SYNTHETIC portfolio v1; NumPy seed {SEED}"},
        synthetic=True,
        provenance=f"SYNTHETIC portfolio v1 seed {SEED}; artificial weekday calendar, not an exchange history",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset(), separators=(",", ":")) + "\n")
    print(f"Wrote explicitly SYNTHETIC portfolio fixture to {args.output}")
