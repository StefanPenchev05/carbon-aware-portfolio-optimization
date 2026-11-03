"""Derived exploratory statistics. Input observations are never modified."""

import math
from collections import Counter
from datetime import date

import numpy as np
import pandas as pd
from scipy import stats

from app.services.preparation import align_emissions, normalize_emissions, prepare_returns

MESSAGE = "Insufficient verified corporate observations for statistical analysis."
DEFAULTS = {"min_pairs": 5, "min_companies": 5, "min_daily_returns": 60, "min_panel_years": 3}
SECTORS = ("Energy", "Industrials", "Pharmaceuticals")


def financial(rows, *, expected_dates=None, adjustment_verified=False, min_daily_returns=60):
    """Calendar must enumerate every session of the requested measurement window."""
    warnings = []
    try:
        if len({(r["company_id"], r["synthetic"]) for r in rows}) > 1:
            raise ValueError("Financial summary requires one company and dataset")
        if expected_dates is not None and expected_dates != sorted(set(expected_dates)):
            raise ValueError("Reviewed calendar must have unique ordered sessions")
        daily = prepare_returns(rows, expected_dates=expected_dates)
    except ValueError as exc:
        return dict(
            status="insufficient",
            blockers=[str(exc)],
            daily=[],
            periods=[],
            cumulative_return=None,
            annualized_volatility=None,
            valid_returns=0,
            price_count=len(rows),
            completeness=None,
        )
    if expected_dates is None:
        warnings.append("No reviewed exchange calendar; weekday adjacency is provisional")
    if not adjustment_verified:
        warnings.append("Dividend and corporate-action adjustment semantics have not been verified")
    valid = [r["simple_return"] for r in daily if r["simple_return"] is not None]
    complete = bool(daily) and expected_dates is not None and {r["date"] for r in daily} == set(expected_dates)
    usable = complete and adjustment_verified and len(valid) == max(0, len(daily) - 1) and len(valid) > 0
    if not complete:
        warnings.append("Incomplete or unverified measurement-window coverage")
    if len(valid) < min_daily_returns:
        warnings.append(f"At least {min_daily_returns} valid daily returns required for volatility")
    cumulative = volatility = None
    if usable:
        with np.errstate(over="ignore", invalid="ignore"):
            cumulative = float(np.prod(1 + np.array(valid)) - 1)
            if len(valid) >= max(2, min_daily_returns):
                volatility = float(np.std(valid, ddof=1) * np.sqrt(252))
        if not math.isfinite(cumulative) or (volatility is not None and not math.isfinite(volatility)):
            warnings.append("Numerically unstable aggregate; summary excluded")
            usable = False
            cumulative = volatility = None
    periods = []
    if daily:
        frame = pd.DataFrame(daily)
        frame["period_date"] = pd.to_datetime(frame["date"])
        for frequency in ("M", "Y"):
            for label, group in frame.groupby(frame["period_date"].dt.to_period(frequency)):
                values = group["simple_return"].dropna()
                # A bucket is descriptive observed-window performance, never a claimed full month/year.
                periods.append(
                    {
                        "period": str(label),
                        "frequency": frequency,
                        "return_count": len(values),
                        "simple_return": float(np.prod(1 + values.to_numpy()) - 1) if usable and len(values) else None,
                        "coverage": "observed window only; may be partial month/year",
                    }
                )
    return dict(
        status="computable"
        if usable and len(valid) >= min_daily_returns
        else ("exploratory" if usable else "insufficient"),
        blockers=warnings,
        daily=daily,
        periods=periods,
        cumulative_return=cumulative,
        annualized_volatility=volatility,
        valid_returns=len(valid),
        price_count=len(rows),
        completeness=len(daily) / len(expected_dates) if expected_dates else None,
    )


def carbon_value(row, metric, basis):
    scopes = ("scope1", "scope2") if metric == "scope1+2" else (metric,)
    if "scope2" in scopes and (basis == "unknown" or row.get("scope2_basis") != basis):
        return None, "Scope 2 basis missing or incompatible"
    normalized = normalize_emissions(row)
    values = [normalized["normalized_scopes"].get(s) for s in scopes]
    if any(v is None or not math.isfinite(v) or v < 0 for v in values):
        return None, "Missing or unsupported carbon scope/unit"
    if any(row.get(f"{s}_status", "unknown") == "unknown" for s in scopes):
        return None, "Unknown scope provenance"
    return sum(values), None


def correlate(
    pairs,
    *,
    mode="cross-section",
    min_pairs=5,
    min_companies=5,
    min_panel_years=3,
    independent_sampling_verified=False,
    bivariate_normality_justified=False,
):
    """One pair per company/window; panel coefficients have no iid significance test."""
    valid = []
    excluded = Counter()
    for p in pairs:
        if any(p.get(k) is None or not math.isfinite(p[k]) for k in ("x", "y")):
            excluded["missing/nonfinite pair"] += 1
        else:
            valid.append(p)
    keys = [(p["company_id"], p["period"]) for p in valid]
    companies = len({p["company_id"] for p in valid})
    periods = sorted({p["period"] for p in valid})
    warnings = []
    if len(keys) != len(set(keys)):
        warnings.append("Duplicate company-period pairs: potential pseudoreplication")
    if mode == "cross-section" and (len(periods) > 1 or companies != len(valid)):
        warnings.append("Cross-section requires exactly one pair per company in one period")
    if len(valid) < min_pairs:
        warnings.append(f"At least {min_pairs} valid pairs required")
    if companies < min_companies:
        warnings.append(f"At least {min_companies} distinct companies required")
    if mode == "panel" and len(periods) < min_panel_years:
        warnings.append(f"At least {min_panel_years} panel years required")
    if valid and (np.ptp([p["x"] for p in valid]) == 0 or np.ptp([p["y"] for p in valid]) == 0):
        warnings.append("Zero variance in carbon or financial metric")
    for key in ("x", "y"):
        array = np.array([p[key] for p in valid], dtype=float)
        if len(array) and np.linalg.norm(array - array.mean()) < 1e-13 * abs(array.mean()):
            warnings.append(f"Near-constant {key}; coefficient precision is unreliable")
    result = dict(
        status="insufficient" if warnings else "exploratory",
        coefficient_pearson=None,
        coefficient_spearman=None,
        p_value_pearson=None,
        p_value_spearman=None,
        valid_pairs=len(valid),
        distinct_companies=companies,
        periods=periods,
        exclusions=dict(excluded),
        warnings=warnings,
        points=valid,
    )
    if not warnings:
        x, y = np.array([p["x"] for p in valid]), np.array([p["y"] for p in valid])
        result.update(
            coefficient_pearson=float(stats.pearsonr(x, y).statistic),
            coefficient_spearman=float(stats.spearmanr(x, y).statistic),
        )
    if not warnings and mode == "cross-section" and independent_sampling_verified:
        if bivariate_normality_justified:
            result["p_value_pearson"] = float(stats.pearsonr(x, y).pvalue)
        if len(valid) > 500:
            result["p_value_spearman"] = float(stats.spearmanr(x, y).pvalue)
    result["warnings"].append("Exploratory association; no causal interpretation or investment conclusion")
    result["warnings"].append(
        "P-values require reviewed independent sampling; Pearson also requires bivariate normality; "
        "Spearman asymptotic significance is restricted to n > 500"
        if mode == "cross-section"
        else "Panel dependence: coefficients are descriptive; naive iid p-values are invalid"
    )
    return result


def build_pairs(
    companies, prices, emissions, reviews, *, start_year, end_year, mode, alignment, metric, basis, min_daily_returns=60
):
    """Annual Jan–Dec financial windows; carbon availability measured at window start.

    Reviews are analyst-controlled evidence, never request flags. No automatic
    fiscal/calendar equivalence or boundary compatibility is inferred.
    """
    pairs, exclusions = [], Counter()
    for company in companies:
        cid = company["id"]
        review = reviews.get(str(cid), {})
        for year in range(start_year, end_year + 1):
            spec = review.get("years", {}).get(str(year))
            if not spec:
                exclusions["No reviewed calendar, adjustment and carbon-boundary specification"] += 1
                continue
            selected = [
                p
                for p in prices
                if p["company_id"] == cid
                and p["source_id"] == spec["price_source_id"]
                and date(year - 1, 12, 1) <= p["date"] <= date(year, 12, 31)
            ]
            calendar = [date.fromisoformat(d) for d in spec["expected_dates"]]
            if (
                len(calendar) < 2
                or calendar != sorted(set(calendar))
                or calendar[0].year != year - 1
                or calendar[0].month != 12
                or calendar[-1].month != 12
                or any(d.year != year for d in calendar[1:])
            ):
                exclusions["Invalid annual calendar: needs previous December close and all current-year sessions"] += 1
                continue
            selected = [p for p in selected if calendar[0] <= p["date"] <= calendar[-1]]
            fin = financial(
                selected,
                expected_dates=calendar,
                adjustment_verified=spec.get("adjustment_verified", False),
                min_daily_returns=min_daily_returns,
            )
            if fin["status"] != "computable":
                exclusions["Incomplete verified annual return series"] += 1
                continue
            stream = [
                e
                for e in emissions
                if e["company_id"] == cid
                and e["source_id"] == spec["emission_source_id"]
                and e["scope2_basis"] == basis
                and e["methodology"] == spec["methodology"]
            ]
            anchor = {"company_id": cid, "synthetic": company["synthetic"], "date": date(year, 1, 1)}
            try:
                match = align_emissions([anchor], stream, mode=alignment)[0]["emission"]
            except ValueError:
                exclusions["Ambiguous disclosure stream/vintage"] += 1
                continue
            if match is None:
                exclusions["No eligible disclosure at measurement-window start"] += 1
                continue
            # Compatibility includes organizational boundary, selected scopes and reporting-period interpretation.
            if not spec.get("comparability_group") or not spec.get("carbon_period_verified"):
                exclusions["Carbon boundary/reporting-period review missing"] += 1
                continue
            value, issue = carbon_value(match, metric, basis)
            if issue:
                exclusions[issue] += 1
                continue
            pairs.append(
                dict(
                    company_id=cid,
                    company=company["name"],
                    sector=company["sector"],
                    period=year,
                    x=value,
                    y=fin["cumulative_return"],
                    currency=selected[0]["currency"],
                    comparability_group=spec["comparability_group"],
                    disclosure_year=match["year"],
                    disclosure_date=match.get("disclosure_date"),
                )
            )
    if len({p["comparability_group"] for p in pairs}) > 1:
        exclusions["Incompatible carbon boundaries/methodologies across companies"] += len(pairs)
        pairs = []
    if len({p["currency"] for p in pairs}) > 1:
        exclusions["Mixed native-currency return perspectives; choose a common reviewed currency universe"] += len(
            pairs
        )
        pairs = []
    return pairs, dict(exclusions)
