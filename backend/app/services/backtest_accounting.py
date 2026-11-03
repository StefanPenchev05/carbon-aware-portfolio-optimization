"""Zero-cost self-financing signed notional book. No optimizer or database logic."""
from dataclasses import dataclass, field

import numpy as np

from app.services.portfolio import PortfolioError


@dataclass
class Book:
    cash: float = 1.0
    notionals: dict[int,float] = field(default_factory=dict)

    @property
    def equity(self):
        return self.cash + sum(self.notionals.values())

    def rebalance(self, weights):
        wealth=self.equity
        if wealth <= 0 or not np.isfinite(wealth):
            raise PortfolioError("Nonpositive/nonfinite capital; experiment stopped", "accounting_error")
        if not all(np.isfinite(v) for v in weights.values()):
            raise PortfolioError("Nonfinite rebalance weights", "accounting_error")
        old={i:n/wealth for i,n in self.notionals.items()}
        changes={i:weights.get(i,0)-old.get(i,0) for i in sorted(set(old)|set(weights))}
        new={i:w*wealth for i,w in weights.items()}
        self.cash -= sum(new.values())-sum(self.notionals.values())
        self.notionals=new
        return old,changes,sum(abs(v) for v in changes.values())

    def advance(self, returns, date):
        before=self.equity
        if set(self.notionals)-set(returns):
            raise PortfolioError("Missing holding return for an established position", "insufficient")
        if not all(np.isfinite(v) and v > -1 for v in returns.values()):
            raise PortfolioError("Invalid holding return", "accounting_error")
        for i in self.notionals:
            self.notionals[i] *= 1+returns[i]
        wealth=self.equity
        if not np.isfinite(wealth) or wealth <= 0 or before<=0:
            raise PortfolioError("Capital exhausted/nonfinite under signed P&L; no annual metrics accepted", "accounting_error")
        weights={i:n/wealth for i,n in self.notionals.items()}
        return dict(date=date,realized_return=wealth/before-1,equity=wealth,cumulative_return=wealth-1,
                    gross_exposure=sum(abs(w) for w in weights.values()),net_exposure=sum(weights.values()),
                    long_positions=sum(w>1e-7 for w in weights.values()),short_positions=sum(w < -1e-7 for w in weights.values()))
