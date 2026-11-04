"""Walk-forward comparison: shared immutable plans, separate self-financing books."""

from collections import Counter

import numpy as np

from app.services.backtest_accounting import Book
from app.services.backtest_data import at_decision, inventory
from app.services.backtest_execution import construct, holding_returns
from app.services.backtest_metrics import carbon_metrics, financial_metrics
from app.services.backtest_schedule import windows
from app.services.portfolio import PortfolioError

ASSUMPTIONS = [
    "Initial reference equity 1; signed adjusted-price units held fixed between rebalance closes; weights drift.",
    "Decision uses prices strictly before decision date; execution at that date's close is an idealized zero-slippage assumption.",
    "Self-financing cash residual includes short proceeds/collateral; cash interest, financing, borrow fees and trading costs are zero.",
    "Rebalance caps/gross/net apply to target weights only; interim exposures drift and no margin calls are modeled.",
    "Turnover is full L1 traded notional / pretrade equity, including initial establishment, excluding terminal liquidation.",
]
WARNINGS = [
    "Subsequent historical P&L is conditional on idealized execution/financing, not a promise of realizable returns or forecasts.",
    "Rank carbon scores are contemporaneous long-book proxies, not financed/avoided emissions or real decarbonization.",
    "Cross-date scores can change with universe/rank changes; simultaneous baseline comparisons use identical scores.",
    "Sensitivity is descriptive; no penalty is selected or tuned on this evaluation period.",
    "Estimation, survivorship/selection, vintage, missing-disclosure and parameter-overfitting risks remain.",
]


def plan_history(data, config):
    ready = inventory(data, config)
    if ready["blockers"]:
        return None, ready
    plans = []
    counts = Counter()
    try:
        schedule = windows(data["calendar"], config)
        for window in schedule:
            plan = at_decision(data, config, window)
            counts.update(plan["exclusions"].values())
            plans.append(plan)
        if len({p["currency"] for p in plans}) > 1:
            raise PortfolioError(
                "Reference currency changes across rebalances; FX accounting is unsupported", "insufficient"
            )
        # This is an all-or-nothing retrospective data audit, never an eligibility filter.
        for plan in plans:
            plan["holding_returns"] = holding_returns(data, plan)
    except PortfolioError as exc:
        ready.update(
            status=exc.status,
            blockers=[str(exc)],
            scheduled_periods=len(plans),
            decision_dates=[p["window"]["decision_date"] for p in plans],
            exclusions=dict(counts),
        )
        return None, ready
    ready.update(
        status="ready",
        scheduled_periods=len(plans),
        decision_dates=[p["window"]["decision_date"] for p in plans],
        exclusions=dict(counts),
    )
    return plans, ready


def evaluate_strategy(plans, config, penalty):
    book = Book()
    daily = []
    steps = []
    for plan in plans:
        target = construct(plan, penalty)
        weights = {p["company_id"]: p["weight"] for p in target["positions"]}
        pretrade, changes, turnover = book.rebalance(weights)
        period_start = book.equity
        sectors = {}
        for asset in plan["prepared"]["estimates"]["assets"]:
            s = sectors.setdefault(asset["sector"], dict(long=0.0, short=0.0, net=0.0))
            w = weights[asset["company_id"]]
            s["long"] += max(0, w)
            s["short"] += min(0, w)
            s["net"] += w
        for d, returns in sorted(plan["holding_returns"].items()):
            daily.append(book.advance(returns, d))
        steps.append(
            dict(
                decision_date=plan["window"]["decision_date"],
                training_start=plan["window"]["training_start"],
                training_end=plan["window"]["training_end"],
                holding_end=plan["window"]["holding_end"],
                eligible_ids=plan["prepared"]["ids"],
                exclusions=plan["exclusions"],
                in_sample=plan["prepared"]["estimates"],
                target_portfolio=target,
                pretrade_weights=pretrade,
                weight_changes=changes,
                turnover_l1=turnover,
                sector_allocations=sectors,
                realized_period_return=book.equity / period_start - 1,
            )
        )
    metrics = financial_metrics(
        daily, steps, min_annual_observations=config.min_annual_observations, risk_free_rate=config.risk_free_rate
    )
    if not all(v is None or np.isfinite(v) for v in metrics.values() if not isinstance(v, str)):
        raise PortfolioError("Nonfinite evaluation metrics; no result accepted", "accounting_error")
    return dict(
        carbon_penalty=penalty,
        initial_date=plans[0]["window"]["decision_date"],
        daily=daily,
        rebalances=steps,
        financial=metrics,
        carbon=carbon_metrics(steps),
    )


def experiment(data, config, operation="compare", *, plans_and_readiness=None):
    plans, ready = plans_and_readiness or plan_history(data, config)
    response = dict(
        status=ready["status"],
        message="Historical evaluation unavailable: insufficient verified point-in-time inputs.",
        configuration=config,
        readiness=ready,
        strategies=[],
        assumptions=list(ASSUMPTIONS),
        warnings=list(WARNINGS),
    )
    response["assumptions"].append(
        f"Effective annual risk-free rate assumption: {config.risk_free_rate!r}; None disables Sharpe."
    )
    if data["synthetic"]:
        response["warnings"].insert(
            0, "SYNTHETIC demonstration: simulated histories and subsequent P&L, not empirical corporate performance."
        )
    if plans is None:
        return response
    response["reference_currency"] = plans[0]["currency"]
    response["assumptions"].append(f"Reference capital/cash currency: {plans[0]['currency']}; no FX conversion.")
    penalties = (
        [config.carbon_penalty] if operation == "run" else sorted(set([0, config.carbon_penalty, *config.penalties]))
    )
    try:
        strategies = [evaluate_strategy(plans, config, p) for p in penalties]
        baseline = next((s for s in strategies if s["carbon_penalty"] == 0), None)
        for strategy in strategies:
            if baseline:
                difference = np.mean(
                    [
                        a["target_portfolio"]["carbon_exposure_score"] - b["target_portfolio"]["carbon_exposure_score"]
                        for a, b in zip(strategy["rebalances"], baseline["rebalances"], strict=True)
                    ]
                )
                strategy["carbon"]["average_paired_difference_from_baseline"] = float(difference)
    except PortfolioError as exc:
        response.update(status=exc.status, message=str(exc))
        return response
    response.update(
        status="success",
        message="SYNTHETIC walk-forward demonstration"
        if data["synthetic"]
        else "Historical zero-cost signed P&L under documented assumptions",
        strategies=strategies,
    )
    return response
