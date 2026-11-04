"""Stateless historical evaluation; no data acquisition or experiment persistence."""

from fastapi import APIRouter, Depends, Query

from app.api.portfolio import PortfolioRoute
from app.core.database import get_db
from app.repositories.backtest import load_history
from app.schemas.backtest import BacktestReadiness, BacktestRequest, BacktestResponse
from app.services.backtest_engine import experiment, plan_history
from app.services.portfolio import PortfolioError

router = APIRouter(prefix="/api/backtest", tags=["historical evaluation"], route_class=PortfolioRoute)


def inputs(db, config):
    try:
        data = load_history(db, config.data_mode)
        return data, plan_history(data, config)
    except PortfolioError as exc:
        ready = dict(
            status=exc.status,
            synthetic=config.data_mode == "synthetic",
            provenance="No historical verification inferred",
            blockers=[str(exc)],
            company_count=0,
            price_count=0,
            adjusted_price_count=0,
            scheduled_periods=0,
            decision_dates=[],
            exclusions={},
        )
        return dict(synthetic=config.data_mode == "synthetic"), (None, ready)


@router.get("/readiness", response_model=BacktestReadiness)
def readiness(config: BacktestRequest = Query(), db=Depends(get_db)):
    return inputs(db, config)[1][1]


@router.post("/run", response_model=BacktestResponse)
def run(config: BacktestRequest, db=Depends(get_db)):
    data, plans = inputs(db, config)
    return experiment(data, config, "run", plans_and_readiness=plans)


@router.post("/compare", response_model=BacktestResponse)
def compare(config: BacktestRequest, db=Depends(get_db)):
    data, plans = inputs(db, config)
    return experiment(data, config, "compare", plans_and_readiness=plans)
