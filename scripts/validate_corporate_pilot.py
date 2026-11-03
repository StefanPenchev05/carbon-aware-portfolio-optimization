"""Read-only verification of a local permitted corporate bundle against the live API.

Run using backend/.venv/bin/python; original values stay in the private bundle.
"""

import argparse
import csv
import json
from pathlib import Path
from urllib.request import urlopen

from app.services.preparation import align_emissions, prepare_returns
from app.services.provenance import load_manifest


def get(base, path):
    with urlopen(base + "/api" + path, timeout=15) as response:
        return json.load(response)


def validate(bundle, base="http://localhost:8000"):
    bundle = Path(bundle)
    records = {}
    digests = set()
    for kind in ("companies", "memberships", "prices", "emissions"):
        manifest, digest = load_manifest(bundle / "manifest.json", bundle / f"{kind}.csv")
        assert not manifest.synthetic
        digests.add(digest)
        with (bundle / f"{kind}.csv").open() as stream:
            records[kind] = list(csv.DictReader(stream))
    assert len(digests) == 1
    assert len(records["companies"]) == 1, "Validate the initial single-company workflow first"
    local = records["companies"][0]
    companies = get(base, "/companies")
    matches = [c for c in companies if c["isin"] == local["isin"]]
    assert len(matches) == 1 and not matches[0]["source"]["synthetic"]
    company = matches[0]
    assert company["source"]["manifest_sha256"] in digests
    for key in ("name", "ticker", "exchange", "currency", "sector", "original_sector"):
        assert company[key] == local[key]
    company_id = company["id"]
    prices = get(base, f"/companies/{company_id}/prices")
    emissions = get(base, f"/companies/{company_id}/emissions")
    assert len(prices) == len(records["prices"])
    assert len(emissions) == len(records["emissions"])
    expected_prices = {p["date"]: p for p in records["prices"]}
    for price in prices:
        expected = expected_prices[price["date"]]
        assert not price["source"]["synthetic"]
        assert price["close"] == float(expected["close"])
        assert price["currency"] == expected["currency"]
        assert price["adjusted_close"] is None, "Sparse issuer closes must not pretend to be adjusted"
        assert "sparse" in price["adjustment_method"]
    expected_emissions = {(int(e["year"]), e["scope2_basis"]): e for e in records["emissions"]}
    for emission in emissions:
        expected = expected_emissions[(emission["year"], emission["scope2_basis"])]
        assert not emission["source"]["synthetic"]
        assert emission["disclosure_date"] == expected["disclosure_date"]
        assert emission["disclosure_reference"] == expected["disclosure_reference"]
        for scope in ("scope1", "scope2", "scope3"):
            assert emission[scope] == (float(expected[scope]) if expected[scope] else None)
            assert emission[scope + "_status"] == expected[scope + "_status"]
        assert emission["units"] == "ktCO2e"
        for scope in ("scope1", "scope2"):
            assert emission["normalized_scopes"][scope] == emission[scope] * 1000
    internal_prices = [dict(p, company_id=company_id, source_id=p["source"]["id"], synthetic=False) for p in prices]
    internal_emissions = [
        dict(e, company_id=company_id, source_id=e["source"]["id"], synthetic=False) for e in emissions
    ]
    descriptive = align_emissions(internal_prices, internal_emissions, mode="descriptive")
    pit = align_emissions(internal_prices, internal_emissions, mode="point-in-time")
    returns = prepare_returns(internal_prices)
    assert not any(r["simple_return"] is not None for r in returns)
    quality = get(base, "/data/quality")
    own = next(c for c in quality["companies"] if c["company_id"] == company_id)
    assert own["membership_snapshots"] == len(records["memberships"])
    assert own["price_count"] == len(prices) and own["emission_count"] == len(emissions)
    assert own["usable_matched_observations"] == 0
    assert own["missing_publication_dates"] == 0
    return dict(
        company=company["name"],
        isin=company["isin"],
        synthetic=False,
        verified_membership_records=own["membership_snapshots"],
        membership_as_of=records["memberships"][0]["as_of"],
        price_observations=len(prices),
        adjusted_price_observations=0,
        price_years=sorted({p["date"][:4] for p in prices}),
        emission_observations=len(emissions),
        scope_cells=sum(e[s] is not None for e in emissions for s in ("scope1", "scope2", "scope3")),
        emission_years=own["years"],
        available_scopes=own["available_scopes"],
        missing_publication_dates=own["missing_publication_dates"],
        descriptive_price_emission_label_matches=sum(r["emission"] is not None for r in descriptive),
        point_in_time_price_level_matches=sum(r["emission"] is not None for r in pit),
        descriptive_unmatched_prices=sum(r["emission"] is None for r in descriptive),
        point_in_time_unmatched_prices=sum(r["emission"] is None for r in pit),
        daily_return_observations=0,
        usable_matched_return_observations=own["usable_matched_observations"],
        data_quality=own,
        notes=[
            "Price-level timing matches are not eligible daily return pairs or evidence of statistical adequacy.",
            "Descriptive reporting-year labels are not a fiscal-interval join; Siemens fiscal years end September 30.",
            "Reported means issuer-disclosed; the issuer permits estimations/extrapolation in its environmental totals.",
            "Membership verified only at the stated snapshot, not retrospectively for price years.",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    print(json.dumps(validate(args.bundle, args.base), default=str, indent=2))


if __name__ == "__main__":
    main()
