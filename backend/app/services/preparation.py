"""Pure preparation functions. No imputation, FX conversion or statistical inference."""

import math
from collections import defaultdict
from datetime import date

UNIT_FACTORS = {
    "kgCO2e": 0.001,
    "kgCO₂e": 0.001,
    "tCO2e": 1.0,
    "tCO₂e": 1.0,
    "tonnes CO2e": 1.0,
    "ktCO2e": 1000.0,
    "MtCO2e": 1_000_000.0,
}
SCOPES = ("scope1", "scope2", "scope3")


def normalize_emissions(row):
    """Retain originals; unknown/CO2-only units cannot become CO2-equivalent."""
    factor = UNIT_FACTORS.get(row["units"])
    return {
        **row,
        "normalized_units": "tCO2e" if factor is not None else None,
        "normalized_scopes": {
            scope: None if factor is None or row.get(scope) is None else row[scope] * factor for scope in SCOPES
        },
        "normalization_issue": None if factor is not None else "Unsupported or ambiguous emissions unit",
    }


def day(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def prepare_returns(rows, *, price_field="adjusted_close", expected_dates=None):
    """Require one source/currency/adjustment regime per company and dataset.

    Missing prices break the chain. With no exchange calendar, weekdays are only
    provisional expected sessions. Gaps never become mislabeled daily returns.
    """
    if price_field not in ("close", "adjusted_close"):
        raise ValueError("Choose close or adjusted_close explicitly")
    groups = defaultdict(list)
    for row in rows:
        groups[(row["company_id"], row["synthetic"])].append(dict(row, date=day(row["date"])))
    output = []
    for records in groups.values():
        regimes = {(r["source_id"], r["currency"], r.get("adjustment_method", "unknown")) for r in records}
        if len(regimes) > 1:
            raise ValueError("Ambiguous source, currency or adjustment regime; select one series first")
        records.sort(key=lambda r: r["date"])
        dates = [r["date"] for r in records]
        if len(dates) != len(set(dates)):
            raise ValueError("Duplicate price date")
        calendar = sorted({day(d) for d in expected_dates}) if expected_dates is not None else None
        previous = None
        for row in records:
            current = row.get(price_field)
            if current is not None and (not math.isfinite(current) or current <= 0):
                raise ValueError("Prices must be finite and positive")
            if row["date"].weekday() >= 5:
                raise ValueError("Weekend date requires a market-specific adapter")
            if calendar is not None and row["date"] not in calendar:
                raise ValueError("Price date is not in supplied exchange calendar")
            issue = "first observation"
            simple = logarithmic = None
            missing = []
            if previous:
                prev_date = previous["date"]
                if calendar is not None:
                    missing = [d for d in calendar if prev_date < d < row["date"]]
                else:
                    from datetime import timedelta

                    d = prev_date + timedelta(days=1)
                    while d < row["date"]:
                        if d.weekday() < 5:
                            missing.append(d)
                        d += timedelta(days=1)
                prev_price = previous.get(price_field)
                if missing:
                    issue = "missing expected session(s); return excluded"
                elif current is None or prev_price is None:
                    issue = "missing price; return excluded"
                elif price_field == "adjusted_close" and row.get("adjustment_method", "unknown") == "unknown":
                    issue = "unknown price-adjustment methodology; return excluded"
                else:
                    ratio = current / prev_price
                    if math.isfinite(ratio) and ratio > 0:
                        simple = ratio - 1
                        logarithmic = math.log(ratio)
                        issue = None
                    else:
                        issue = "numerically invalid price ratio; return excluded"
            output.append(
                {
                    **row,
                    "simple_return": simple,
                    "log_return": logarithmic,
                    "return_price_field": price_field,
                    "previous_date": previous["date"] if previous else None,
                    "missing_expected_dates": missing,
                    "return_issue": issue,
                    "calendar_verified": calendar is not None,
                }
            )
            previous = row
    return sorted(output, key=lambda r: (r["date"], r["company_id"], r["synthetic"]))


def align_emissions(prices, emissions, *, mode="point-in-time"):
    """Select one disclosure stream per company/dataset before calling.

    Date-only disclosures become usable the following day, because release time
    and exchange close are unknown. Descriptive mode is explicitly not PIT-safe.
    """
    if mode not in ("point-in-time", "descriptive"):
        raise ValueError("Unknown alignment mode")
    streams = defaultdict(set)
    for e in emissions:
        streams[(e["company_id"], e["synthetic"])].add(
            (e["source_id"], e.get("scope2_basis", "unknown"), e["methodology"])
        )
    if any(len(values) > 1 for values in streams.values()):
        raise ValueError("Select a single emissions source, Scope 2 basis and methodology first")
    output = []
    for price in prices:
        trade_date = day(price["date"])
        candidates = []
        for e in emissions:
            if (e["company_id"], e["synthetic"]) != (price["company_id"], price["synthetic"]):
                continue
            published = day(e["disclosure_date"]) if e.get("disclosure_date") else None
            if mode == "descriptive" and e["year"] == trade_date.year:
                candidates.append(e)
            elif mode == "point-in-time" and published and published < trade_date:
                candidates.append(e)
        chosen = None
        if candidates:

            def order(e):
                return (e["year"], day(e["disclosure_date"]) if e.get("disclosure_date") else date.min)

            candidates.sort(key=order)
            if len(candidates) > 1 and order(candidates[-1]) == order(candidates[-2]):
                raise ValueError("Ambiguous disclosure vintage")
            chosen = normalize_emissions(candidates[-1])
        output.append(
            {
                **price,
                "emission": chosen,
                "alignment_mode": mode,
                "temporally_verified": mode == "point-in-time" and chosen is not None,
                "alignment_warning": "Reporting-year association can look ahead; not valid for time-dependent inference"
                if mode == "descriptive"
                else (None if chosen else "No disclosure with known prior availability"),
            }
        )
    return output


def convert_to_eur(value, currency, fx_row, observation_date):
    """Explicit exact-date conversion only. ECB quote = foreign units per EUR."""
    if currency == "EUR":
        return value
    if (
        not fx_row
        or fx_row["base_currency"] != "EUR"
        or fx_row["quote_currency"] != currency
        or day(fx_row["date"]) != day(observation_date)
    ):
        raise ValueError("An exact-date EUR-based FX quote for the observation currency is required")
    if not math.isfinite(fx_row["rate"]) or fx_row["rate"] <= 0:
        raise ValueError("Invalid FX rate")
    return value / fx_row["rate"]
