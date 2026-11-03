"""Synthetic test fixtures for the sparse issuer-observation edge cases."""

from app.services.preparation import align_emissions, normalize_emissions, prepare_returns


def test_original_kilotonne_values_remain_separate_from_tonnes():
    original = dict(units="ktCO2e", scope1=2.5, scope2=0, scope3=None)
    normalized = normalize_emissions(original)
    assert original["scope1"] == normalized["scope1"] == 2.5
    assert normalized["normalized_scopes"] == dict(scope1=2500, scope2=0, scope3=None)


def test_sparse_unadjusted_prices_are_not_daily_returns():
    prices = [
        dict(
            company_id=1,
            source_id=1,
            synthetic=False,
            currency="EUR",
            adjustment_method="sparse unadjusted",
            date=d,
            close=10,
            adjusted_close=None,
        )
        for d in ("2024-02-08", "2024-09-30", "2025-02-13")
    ]
    emission = dict(
        company_id=1,
        source_id=1,
        synthetic=False,
        year=2024,
        units="ktCO2e",
        methodology="fixture",
        scope2_basis="market-based",
        scope1=1,
        scope2=2,
        disclosure_date="2024-12-05",
    )
    assert all(r["simple_return"] is None for r in prepare_returns(prices))
    assert all(r["simple_return"] is None for r in prepare_returns(prices, price_field="close"))
    matched = align_emissions(prices, [emission])
    assert [r["emission"] is not None for r in matched] == [False, False, True]
