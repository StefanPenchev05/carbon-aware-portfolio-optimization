"""Prepare a single immutable estimation universe for every comparison penalty."""

import numpy as np

from app.services.analysis import carbon_value, financial
from app.services.portfolio import PortfolioError, candidates, carbon_scores, estimate
from app.services.preparation import align_emissions, day


def prepare(dataset, config):
    available = dataset["companies"]
    selected_ids = set(config.company_ids) if config.company_ids else {c["id"] for c in available}
    companies = sorted([c for c in available if c["id"] in selected_ids], key=lambda c: c["id"])
    blockers = []
    if selected_ids - {c["id"] for c in companies}:
        blockers.append("Selected security IDs are unavailable in the chosen dataset mode")
    if len(companies) < config.min_assets:
        blockers.append(f"Need {config.min_assets} distinct securities; have {len(companies)}")
    if len(companies) > 40:
        blockers.append("Prototype supports at most 40 selected securities")
    prices = [dict(p, date=day(p["date"])) for p in dataset["prices"] if p["company_id"] in selected_ids]
    emissions = [e for e in dataset["emissions"] if e["company_id"] in selected_ids]
    readiness = dict(
        status="insufficient",
        data_mode=config.data_mode,
        synthetic=dataset["synthetic"],
        provenance=dataset["provenance"],
        blockers=blockers,
        available_companies=available,
        selected_count=len(companies),
        eligible_count=0,
        price_count=len(prices),
        adjusted_price_count=sum(p.get("adjusted_close") is not None for p in prices),
        emission_count=len(emissions),
        aligned_observations=0,
        long_ids=[],
        short_ids=[],
    )
    records, assets, currencies, groups = [], [], set(), set()
    for c in companies:
        cid = c["id"]
        label = c["name"]
        all_rows = [p for p in prices if p["company_id"] == cid]
        if not any(p.get("adjusted_close") is not None for p in all_rows):
            blockers.append(f"{label}: no consistently adjusted daily prices")
        spec = dataset["reviews"].get(str(cid))
        if not spec:
            blockers.append(f"{label}: reviewed calendar, adjustments and carbon boundaries unavailable")
            continue
        try:
            calendar = [day(d) for d in spec["expected_dates"]]
            if calendar != sorted(set(calendar)):
                raise ValueError("Reviewed calendar must be ordered and unique")
            calendar = [d for d in calendar if config.start_date <= d <= config.end_date]
            if not calendar or calendar[0] != config.start_date or calendar[-1] != config.end_date:
                raise ValueError("Window endpoints must be covered reviewed trading sessions (start is price baseline)")
            rows = [
                p
                for p in all_rows
                if p["source_id"] == spec["price_source_id"] and config.start_date <= p["date"] <= config.end_date
            ]
            fin = financial(
                rows,
                expected_dates=calendar,
                adjustment_verified=spec["adjustment_verified"],
                min_daily_returns=config.min_observations,
            )
            if fin["status"] != "computable":
                raise ValueError("Insufficient verified daily history: " + "; ".join(fin["blockers"]))
            if not spec.get("carbon_period_verified") or not spec.get("comparability_group"):
                raise ValueError("Compatible reporting periods/methods/organizational boundaries not reviewed")
            stream = [
                e
                for e in emissions
                if e["company_id"] == cid
                and e["source_id"] == spec["emission_source_id"]
                and e["methodology"] == spec["methodology"]
                and e.get("scope2_basis") == "market-based"
            ]
            anchor = dict(company_id=cid, synthetic=dataset["synthetic"], date=config.as_of)
            e = align_emissions([anchor], stream, mode="point-in-time")[0]["emission"]
            if e is None:
                raise ValueError("No disclosure with known availability strictly before formation date")
            if any(e.get(s + "_status") != "reported" for s in ("scope1", "scope2")):
                raise ValueError(
                    "Both selected carbon scopes must have reported provenance (not unknown/provider estimates)"
                )
            amount, issue = carbon_value(e, "scope1+2", "market-based")
            if issue or amount is None or not np.isfinite(amount):
                raise ValueError(issue or "Invalid Scope 1+2 measurement")
            returns = {
                (r["previous_date"], r["date"]): r["simple_return"]
                for r in fin["daily"]
                if r["simple_return"] is not None
            }
            records.append(returns)
            currencies.update(r["currency"] for r in rows)
            groups.add(spec["comparability_group"])
            # Original source values remain distinct from derived tCO2e and relative scores.
            original = {k: v for k, v in e.items() if not k.startswith("normaliz")}
            assets.append(
                dict(
                    company_id=cid,
                    name=label,
                    sector=c["sector"],
                    emissions_tco2e=amount,
                    original_emission=original,
                    disclosure_date=day(e["disclosure_date"]),
                    disclosure_year=e["year"],
                    price_source=dataset["sources"][str(spec["price_source_id"])],
                    emission_source=dataset["sources"][str(spec["emission_source_id"])],
                )
            )
        except (ValueError, KeyError, TypeError) as exc:
            blockers.append(f"{label}: {exc}")
    readiness["eligible_count"] = len(assets)
    if len(currencies) > 1:
        blockers.append("Mixed-currency return perspectives: select a single common-currency universe")
    if len(groups) > 1:
        blockers.append("Incompatible carbon comparability groups across selected securities")
    if blockers:
        return None, readiness
    intervals = sorted(set.intersection(*(set(r) for r in records))) if records else []
    readiness["aligned_observations"] = len(intervals)
    if len(intervals) < max(config.min_observations, len(assets) + 1):
        blockers.append(
            f"Need at least max({config.min_observations}, N+1) common daily return intervals; have {len(intervals)}"
        )
        return None, readiness
    matrix = np.array([[r[d] for r in records] for d in intervals])
    try:
        mu, covariance, repair = estimate(matrix, config.shrinkage)
        scores = carbon_scores([a["emissions_tco2e"] for a in assets])
        ids = [a["company_id"] for a in assets]
        longs, shorts, method = candidates(ids, mu, config)
    except PortfolioError as exc:
        readiness["status"] = exc.status
        blockers.append(str(exc))
        return None, readiness
    for i, a in enumerate(assets):
        a.update(
            expected_return_annual=float(mu[i]),
            carbon_score=float(scores[i]),
            dropped_return_intervals=len(records[i]) - len(intervals),
        )
    readiness.update(status="ready", long_ids=[ids[i] for i in longs], short_ids=[ids[i] for i in shorts])
    estimates = dict(
        start_date=config.start_date,
        end_date=config.end_date,
        as_of=config.as_of,
        observations=len(intervals),
        interval_start=intervals[0][0],
        interval_end=intervals[-1][1],
        assets=assets,
        covariance_annual=covariance.tolist(),
        shrinkage=config.shrinkage,
        covariance_repair=repair,
        selection_method=method,
    )
    return dict(
        mu=mu,
        covariance=covariance,
        scores=scores,
        ids=ids,
        names=[a["name"] for a in assets],
        longs=longs,
        shorts=shorts,
        estimates=estimates,
    ), readiness
