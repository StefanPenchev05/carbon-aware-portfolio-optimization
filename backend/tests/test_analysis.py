"""All observations in this module are deterministic SYNTHETIC test fixtures."""

import math
from datetime import date, timedelta

import pytest

from app.services.analysis import build_pairs, carbon_value, correlate, financial


def prices(values=(100, 110, 99), cid=1):
    return [
        dict(
            company_id=cid,
            synthetic=True,
            source_id=1,
            date=date(2024, 1, 2) + timedelta(days=i),
            close=v,
            adjusted_close=v,
            currency="EUR",
            adjustment_method="synthetic total-return adjustment",
        )
        for i, v in enumerate(values)
    ]


def pairs(ys):
    return [dict(company_id=i, period=2024, x=float(i), y=y) for i, y in enumerate(ys)]


@pytest.mark.parametrize("ys,expected", [(list(range(5)), 1), (list(range(4, -1, -1)), -1), ([1, -2, 2, -2, 1], 0)])
def test_known_correlations(ys, expected):
    result = correlate(pairs(ys))
    assert result["coefficient_pearson"] == pytest.approx(expected, abs=1e-14)
    if expected:
        assert result["coefficient_spearman"] == pytest.approx(expected)
    assert result["p_value_pearson"] is None


def test_constant_missing_sparse_and_duplicate_exclusions():
    assert correlate(pairs([1] * 5))["coefficient_pearson"] is None
    result = correlate(pairs([None, 1, 2, 3, 4]))
    assert result["valid_pairs"] == 4
    assert result["exclusions"]["missing/nonfinite pair"] == 1
    repeated = pairs(range(5)) * 2
    assert correlate(repeated)["status"] == "insufficient"
    assert any("pseudoreplication" in w for w in correlate(repeated)["warnings"])
    assert correlate(pairs(range(3)))["coefficient_spearman"] is None


def test_panel_has_no_naive_significance():
    observations = [
        dict(company_id=i, period=y, x=i + y / 100, y=i - y / 100) for i in range(5) for y in (2022, 2023, 2024)
    ]
    result = correlate(observations, mode="panel")
    assert result["distinct_companies"] == 5
    assert result["valid_pairs"] == 15
    assert result["coefficient_pearson"] is not None
    assert result["p_value_spearman"] is None
    assert correlate(observations)["status"] == "insufficient"


def test_returns_numeric_and_input_immutable():
    rows = prices()
    result = financial(rows, expected_dates=[p["date"] for p in rows], adjustment_verified=True, min_daily_returns=2)
    assert result["daily"][1]["simple_return"] == pytest.approx(0.1)
    assert result["daily"][2]["simple_return"] == pytest.approx(-0.1)
    assert result["daily"][1]["log_return"] == pytest.approx(math.log(1.1))
    assert result["cumulative_return"] == pytest.approx(-0.01)
    assert result["annualized_volatility"] == pytest.approx(math.sqrt(0.02) * math.sqrt(252))
    assert result["periods"][0]["simple_return"] == pytest.approx(-0.01)
    assert "simple_return" not in rows[0]
    assert financial(rows)["annualized_volatility"] is None


def test_gap_missing_adjustments_and_currency_exclude():
    rows = prices()
    rows[-1]["date"] = date(2024, 1, 8)
    result = financial(rows, adjustment_verified=True)
    assert result["cumulative_return"] is None
    assert result["daily"][-1]["simple_return"] is None
    rows = prices()
    rows[1]["adjusted_close"] = None
    assert financial(rows)["valid_returns"] == 0
    rows[1]["currency"] = "CHF"
    assert financial(rows)["status"] == "insufficient"


def emission(**updates):
    return dict(
        company_id=1,
        synthetic=True,
        source_id=2,
        year=2024,
        scope1=2,
        scope2=3,
        scope3=None,
        scope1_status="reported",
        scope2_status="estimated",
        scope3_status="unknown",
        units="ktCO2e",
        scope2_basis="market-based",
        methodology="synthetic boundary",
        disclosure_date=date(2025, 1, 1),
        **updates,
    )


def test_carbon_no_scope_substitution_or_unit_mutation():
    e = emission()
    assert carbon_value(e, "scope1+2", "market-based") == (5000, None)
    assert carbon_value(e, "scope2", "location-based")[0] is None
    assert carbon_value(e, "scope3", "market-based")[0] is None
    assert e["scope1"] == 2


def annual_fixture():
    rows = prices()
    rows[0]["date"] = date(2023, 12, 29)
    rows[1]["date"] = date(2024, 1, 2)
    rows[2]["date"] = date(2024, 12, 31)
    reviews = {
        "1": {
            "years": {
                "2024": {
                    "expected_dates": [r["date"].isoformat() for r in rows],
                    "price_source_id": 1,
                    "emission_source_id": 2,
                    "methodology": "synthetic boundary",
                    "adjustment_verified": True,
                    "comparability_group": "synthetic compatible",
                    "carbon_period_verified": True,
                }
            }
        }
    }
    return [dict(id=1, name="SYNTHETIC fixture", sector="Energy", synthetic=True)], rows, [emission()], reviews


def test_pit_rejects_future_and_unknown_disclosure_not_retroactive():
    data = annual_fixture()
    kwargs = dict(
        start_year=2024,
        end_year=2024,
        mode="cross-section",
        metric="scope1+2",
        basis="market-based",
        min_daily_returns=2,
    )
    for published in (None, date(2024, 1, 1), date(2025, 1, 1)):
        data[2][0]["disclosure_date"] = published
        result, excluded = build_pairs(*data, alignment="point-in-time", **kwargs)
        assert result == []
        assert excluded["No eligible disclosure at measurement-window start"] == 1
    data[2][0]["disclosure_date"] = date(2023, 12, 31)
    result, _ = build_pairs(*data, alignment="point-in-time", **kwargs)
    assert len(result) == 1  # annual emissions never duplicated across the two daily returns
    assert result[0]["y"] == pytest.approx(-0.01)
    data[2][0]["disclosure_date"] = date(2025, 1, 1)
    assert len(build_pairs(*data, alignment="descriptive", **kwargs)[0]) == 1


def test_api_structured_insufficiency_and_dataset_isolation(client):
    for endpoint in ("readiness", "correlations", "returns", "sectors"):
        response = client.get(f"/api/analysis/{endpoint}")
        assert response.status_code == 200, response.text
    readiness = client.get("/api/analysis/readiness").json()
    assert readiness["company_count"] == 0  # synthetic sample excluded by default
    assert readiness["correlation"]["coefficient_pearson"] is None
    assert readiness["message"] == "Insufficient verified corporate observations for statistical analysis."
    synthetic = client.get("/api/analysis/readiness?synthetic=true").json()
    assert synthetic["company_count"] == 3
    assert synthetic["correlation"]["valid_pairs"] == 0
    sectors = client.get("/api/analysis/sectors?synthetic=true").json()
    assert set(sectors) == {"Energy", "Industrials", "Pharmaceuticals"}
    assert all(s["coefficient_pearson"] is None for s in sectors.values())


@pytest.mark.parametrize(
    "query",
    [
        "min_pairs=2",
        "metric=bad",
        "sector=unknown",
        "alignment=bad",
        "start_year=2022&end_year=2024",
        "start_year=2025&end_year=2024",
    ],
)
def test_invalid_analysis_queries(client, query):
    assert client.get(f"/api/analysis/correlations?{query}").status_code == 422


def test_justified_pearson_significance_is_opt_in():
    result = correlate(pairs(range(5)), independent_sampling_verified=True, bivariate_normality_justified=True)
    assert result["p_value_pearson"] == pytest.approx(0)
    assert result["p_value_spearman"] is None  # small-sample asymptotic significance suppressed
    panel = correlate(
        pairs(range(5)),
        mode="panel",
        min_panel_years=1,
        independent_sampling_verified=True,
        bivariate_normality_justified=True,
    )
    assert panel["p_value_pearson"] is None


def test_review_file_fails_closed(client, tmp_path, monkeypatch):
    path = tmp_path / "invalid-review.json"
    path.write_text('{"real":{"1":{"years":{"2024":{}}}}}')
    monkeypatch.setenv("ANALYSIS_REVIEW_FILE", str(path))
    assert client.get("/api/analysis/readiness").status_code == 503


def test_sector_subsets_and_incompatible_groups():
    observations = [dict(**p, sector="Energy" if p["company_id"] < 5 else "Industrials") for p in pairs(range(10))]
    energy = correlate([p for p in observations if p["sector"] == "Energy"])
    industrials = correlate([p for p in observations if p["sector"] == "Industrials"])
    assert energy["valid_pairs"] == industrials["valid_pairs"] == 5
    assert energy["coefficient_spearman"] == industrials["coefficient_spearman"] == pytest.approx(1)


def test_reviewed_synthetic_end_to_end_and_sector_filter(client, seeded, tmp_path, monkeypatch):
    import json

    import pandas as pd

    from app.models.entities import CarbonEmission, Company, Source, StockPrice

    source = Source(name="SYNTHETIC analytical fixture only", reference="deterministic unit test", synthetic=True)
    seeded.add(source)
    seeded.flush()
    calendar = [date(2023, 12, 29)] + [d.date() for d in pd.bdate_range("2024-01-01", "2024-12-31")]
    reviews = {}
    for i in range(5):
        c = Company(
            name=f"SYNTHETIC analysis {i}",
            isin=f"ZZ{i + 10:010d}",
            ticker=f"TEST{i}",
            exchange="SYNTHETIC",
            sector="Energy" if i < 3 else "Industrials",
            currency="EUR",
            source_id=source.id,
        )
        seeded.add(c)
        seeded.flush()
        for j, d in enumerate(calendar):
            price = 100 * (1 + (i + 1) / 10) ** (j / (len(calendar) - 1))
            seeded.add(
                StockPrice(
                    company_id=c.id,
                    source_id=source.id,
                    date=d,
                    close=price,
                    adjusted_close=price,
                    currency="EUR",
                    adjustment_method="SYNTHETIC adjusted",
                )
            )
        e = emission()
        e.update(company_id=c.id, source_id=source.id, year=2023, scope1=i + 1, disclosure_date=date(2023, 12, 31))
        e.pop("synthetic")
        seeded.add(CarbonEmission(**e))
        reviews[str(c.id)] = {
            "years": {
                "2024": {
                    "expected_dates": [d.isoformat() for d in calendar],
                    "price_source_id": source.id,
                    "emission_source_id": source.id,
                    "methodology": "synthetic boundary",
                    "adjustment_verified": True,
                    "carbon_period_verified": True,
                    "comparability_group": "SYNTHETIC compatible",
                }
            }
        }
    seeded.commit()
    review_path = tmp_path / "synthetic-review.json"
    review_path.write_text(json.dumps({"synthetic": reviews}))
    monkeypatch.setenv("ANALYSIS_REVIEW_FILE", str(review_path))
    query = "synthetic=true&start_year=2024&end_year=2024"
    result = client.get(f"/api/analysis/correlations?{query}")
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["valid_pairs"] == result["distinct_companies"] == 5
    assert result["coefficient_pearson"] == pytest.approx(1)
    assert result["coefficient_spearman"] == pytest.approx(1)
    assert result["p_value_pearson"] is None
    assert result["status"] == "exploratory"
    sectors = client.get(f"/api/analysis/sectors?{query}").json()
    assert sectors["Energy"]["valid_pairs"] == 3
    assert sectors["Industrials"]["valid_pairs"] == 2
    assert sectors["Pharmaceuticals"]["valid_pairs"] == 0
    assert all(s["coefficient_pearson"] is None for s in sectors.values())
    assert client.get("/api/analysis/correlations?start_year=2024&end_year=2024").json()["valid_pairs"] == 0


def test_numerically_unstable_aggregate_and_near_constant_fail_closed():
    rows = prices((1e-300, 1e-100, 1e100))
    result = financial(rows, expected_dates=[r["date"] for r in rows], adjustment_verified=True, min_daily_returns=2)
    assert result["status"] == "insufficient"
    assert result["cumulative_return"] is None
    assert result["annualized_volatility"] is None
    observations = pairs(range(5))
    for i, p in enumerate(observations):
        p["x"] = 1 + i * 1e-15
    assert correlate(observations)["coefficient_pearson"] is None


def test_financial_summary_rejects_mixed_companies_and_duplicate_calendars():
    assert financial(prices() + prices(cid=2))["status"] == "insufficient"
    rows = prices()
    calendar = [r["date"] for r in rows]
    assert financial(rows, expected_dates=calendar + calendar)["status"] == "insufficient"
