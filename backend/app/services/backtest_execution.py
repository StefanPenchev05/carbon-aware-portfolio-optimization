"""Reuse Task 05 construction; obtain holding returns only after past-only eligibility."""

from app.services.portfolio import PortfolioError
from app.services.portfolio_experiment import execute
from app.services.preparation import day, prepare_returns


def construct(plan, penalty):
    cfg = plan["configuration"].model_copy(update={"carbon_penalty": penalty})
    response = execute(plan["prepared"], plan["readiness"], cfg, "optimize")
    if response["status"] != "success":
        raise PortfolioError(response["message"], response["status"])
    return response["portfolio"]


def holding_returns(data, plan):
    window = plan["window"]
    calendar = window["holding_dates"]
    output = {d: {} for d in calendar[1:]}
    for cid in plan["prepared"]["ids"]:
        spec = plan["reviews"][str(cid)]
        reviewed = [day(d) for d in spec["expected_dates"] if calendar[0] <= day(d) <= calendar[-1]]
        if reviewed != calendar:
            raise PortfolioError(
                f"{window['decision_date']}: holding calendar is not common/verified for {cid}", "insufficient"
            )
        rows = [
            dict(p, date=day(p["date"]))
            for p in data["prices"]
            if p["company_id"] == cid
            and p["source_id"] == spec["price_source_id"]
            and calendar[0] <= day(p["date"]) <= calendar[-1]
        ]
        if sorted(p["date"] for p in rows) != calendar:
            raise PortfolioError(
                f"Missing/duplicate holding prices for already selected asset {cid}; no survivor filtering",
                "insufficient",
            )
        try:
            prepared = prepare_returns(rows, expected_dates=calendar)
        except ValueError as exc:
            raise PortfolioError(f"Invalid holding series for {cid}: {exc}", "insufficient") from exc
        training = [
            p
            for p in data["prices"]
            if p["company_id"] == cid
            and p["source_id"] == spec["price_source_id"]
            and day(p["date"]) == window["training_end"]
        ]
        if len(training) != 1 or any(
            (p["currency"], p["adjustment_method"]) != (training[0]["currency"], training[0]["adjustment_method"])
            for p in rows
        ):
            raise PortfolioError(
                "Price currency/adjustment regime changed between training and holding", "insufficient"
            )
        for r in prepared[1:]:
            if r["simple_return"] is None:
                raise PortfolioError(f"Unusable holding return for {cid}: {r['return_issue']}", "insufficient")
            output[r["date"]][cid] = r["simple_return"]
    return output
