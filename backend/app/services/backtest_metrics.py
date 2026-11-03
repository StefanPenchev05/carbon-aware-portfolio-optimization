"""Subsequent realized P&L metrics; never feed these back into selection or tuning."""
import numpy as np


def financial_metrics(daily, steps, *, min_annual_observations=252, risk_free_rate=0, regular=True):
    r=np.array([d["realized_return"] for d in daily])
    equity=np.r_[1.0,[d["equity"] for d in daily]]
    eligible=regular and len(r)>=min_annual_observations
    reason=None if eligible else "Annualization withheld: insufficient or irregular verified daily observations"
    volatility=float(np.std(r,ddof=1)*np.sqrt(252)) if eligible else None
    sharpe=None
    if eligible and risk_free_rate is not None and volatility is not None and volatility>1e-14:
        rf_daily=(1+risk_free_rate)**(1/252)-1
        sharpe=float((np.mean(r)-rf_daily)*252/volatility)
    return dict(cumulative_return=float(equity[-1]-1),annualized_return=float(equity[-1]**(252/len(r))-1) if eligible else None,
                annualized_volatility=volatility,sharpe_ratio=sharpe,maximum_drawdown=float(np.max(1-equity/np.maximum.accumulate(equity))),
                daily_observations=len(r),evaluation_periods=len(steps),annualization_reason=reason,
                turnover_l1_total=sum(s["turnover_l1"] for s in steps),
                turnover_l1_average=float(np.mean([s["turnover_l1"] for s in steps])),
                **{f"average_{field}":float(np.mean([d[field] for d in daily])) for field in
                   ("gross_exposure","net_exposure","long_positions","short_positions")})


def carbon_metrics(steps):
    groups=[tuple(s["eligible_ids"]) for s in steps]
    ranks=[tuple(a["carbon_score"] for a in s["in_sample"]["assets"]) for s in steps]
    return dict(average_rebalance_score=float(np.mean([s["target_portfolio"]["carbon_exposure_score"] for s in steps])),
                score_definition_changed=len(set(zip(groups,ranks,strict=True)))>1,
                average_paired_difference_from_baseline=None)
