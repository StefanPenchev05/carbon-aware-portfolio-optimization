"""Run fair in-sample experiments using one prepared dataset and fixed sleeves."""

import numpy as np

from app.services.portfolio import TOLERANCE, PortfolioError, compare_results, solve

WARNINGS = [
    "In-sample historical sample means are uncertain estimates, not forecasts or realized/backtested returns.",
    "Long-book rank-carbon exposure is a relative research proxy, not intensity, financed/avoided emissions or decarbonization.",
    "Short carbon measurements are context only; shorts never cancel long-book carbon exposure.",
    "Equal long/short gross allocations imply dollar neutrality, not market-beta neutrality.",
    "No transaction costs, borrow fees, execution, out-of-sample validation or historical constituent reconstruction.",
]


def execute(prepared, readiness, config, operation):
    response = dict(
        status="insufficient",
        message="Real portfolio optimization unavailable: insufficient verified inputs."
        if config.data_mode == "real"
        else "Insufficient synthetic inputs for this configuration.",
        configuration=config,
        readiness=readiness,
        warnings=list(WARNINGS),
    )
    if config.data_mode == "synthetic":
        response["warnings"].insert(
            0, "SYNTHETIC demonstration only: every company, price, disclosure and result is artificial."
        )
    if prepared is None:
        response["status"] = readiness["status"]
        return response
    response["estimates"] = prepared["estimates"]
    raw_cache = {}

    def run(penalty):
        if penalty not in raw_cache:
            raw_cache[penalty] = solve(
                prepared["mu"],
                prepared["covariance"],
                prepared["scores"],
                prepared["ids"],
                prepared["names"],
                prepared["longs"],
                prepared["shorts"],
                config,
                penalty,
            )
        return raw_cache[penalty]

    def payload(raw):
        positions = []
        for i, a in enumerate(prepared["estimates"]["assets"]):
            positions.append(
                dict(
                    company_id=a["company_id"],
                    name=a["name"],
                    weight=raw["weights"][i],
                    sleeve="long" if i in prepared["longs"] else "short",
                    carbon_score=a["carbon_score"],
                    emissions_tco2e=a["emissions_tco2e"],
                )
            )
        return {**{k: v for k, v in raw.items() if k != "weights"}, "positions": positions}

    try:
        if operation == "optimize":
            response["portfolio"] = payload(run(config.carbon_penalty))
        elif operation == "compare":
            traditional, aware = run(0), run(config.carbon_penalty)
            response["comparison"] = dict(
                traditional=payload(traditional),
                carbon_aware=payload(aware),
                difference=compare_results(traditional, aware, prepared["ids"]),
            )
        elif operation == "sensitivity":
            results = [run(p) for p in sorted(set([0, *config.penalties]))]
            exposure = [r["carbon_exposure_score"] for r in results]
            response["sensitivity"] = dict(
                portfolios=[payload(r) for r in results],
                carbon_nonincreasing=bool(np.all(np.diff(exposure) <= TOLERANCE)),
                carbon_reduced=exposure[-1] < exposure[0] - TOLERANCE,
                tolerance=TOLERANCE,
            )
        else:
            raise PortfolioError("Unknown portfolio operation")
    except PortfolioError as exc:
        # All-or-nothing: never show a partially successful experiment as a full comparison.
        response.update(status=exc.status, message=str(exc))
        for key in ("portfolio", "comparison", "sensitivity"):
            response.pop(key, None)
        return response
    response.update(
        status="success",
        message="SYNTHETIC in-sample optimization"
        if config.data_mode == "synthetic"
        else "Exploratory real-data in-sample optimization; no realized performance claim",
    )
    return response
