"""Calendar-only scheduling; never inspect realized asset returns."""

import pandas as pd

from app.services.portfolio import PortfolioError
from app.services.preparation import day


def windows(calendar, config):
    dates = [day(d) for d in calendar]
    if dates != sorted(set(dates)) or not dates:
        raise PortfolioError("Historical session calendar must be nonempty, ordered and unique")
    if config.start_date not in dates or config.end_date not in dates:
        raise PortfolioError("Evaluation endpoints must be covered reviewed trading sessions", "insufficient")
    selected = [i for i, d in enumerate(dates) if config.start_date <= d <= config.end_date]
    decisions = []
    previous = None
    for i in selected[:-1]:
        period = pd.Period(dates[i], freq="M" if config.frequency == "monthly" else "Q")
        if period != previous:
            decisions.append(i)
            previous = period
    if not decisions or decisions[0] - 1 - config.training_sessions < 0:
        raise PortfolioError("Insufficient strictly prior training sessions", "insufficient")
    if len(decisions) > 36:
        raise PortfolioError("Prototype supports at most 36 rebalance decisions")
    anchor = decisions[0] - 1 - config.training_sessions
    result = []
    for j, i in enumerate(decisions):
        train_end = i - 1
        train_start = anchor if config.window == "expanding" else train_end - config.training_sessions
        end = decisions[j + 1] if j + 1 < len(decisions) else selected[-1]
        result.append(
            dict(
                decision_date=dates[i],
                training_start=dates[train_start],
                training_end=dates[train_end],
                holding_dates=dates[i : end + 1],
                holding_end=dates[end],
            )
        )
    return result
