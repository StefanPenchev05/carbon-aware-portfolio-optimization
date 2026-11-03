"""Typed, stateless research endpoints. No portfolio or observation persistence."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from app.core.database import get_db
from app.repositories.portfolio import load_dataset
from app.schemas.portfolio import PortfolioRequest, PortfolioResponse, Readiness
from app.services.portfolio import PortfolioError
from app.services.portfolio_data import prepare
from app.services.portfolio_experiment import execute


class PortfolioRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def validated(request):
            try:
                return await original(request)
            except RequestValidationError as exc:
                # JSON parsers may accept NaN/Infinity. Do not echo nonfinite input
                # into JSONResponse, which would turn a proper rejection into 500.
                detail = [{k: error[k] for k in ("loc", "msg", "type")} for error in exc.errors()]
                raise HTTPException(status_code=422, detail=detail) from exc

        return validated


router = APIRouter(prefix="/api/portfolio", tags=["portfolio"], route_class=PortfolioRoute)


def inputs(db, config):
    try:
        return prepare(load_dataset(db, config.data_mode), config)
    except PortfolioError as exc:
        return None, dict(
            status=exc.status,
            data_mode=config.data_mode,
            synthetic=config.data_mode == "synthetic",
            provenance="No verification inferred",
            blockers=[str(exc)],
            available_companies=[],
            selected_count=0,
            eligible_count=0,
            price_count=0,
            adjusted_price_count=0,
            emission_count=0,
            aligned_observations=0,
        )


@router.get("/readiness", response_model=Readiness)
def readiness(config: PortfolioRequest = Query(), db=Depends(get_db)):
    return inputs(db, config)[1]


@router.post("/optimize", response_model=PortfolioResponse)
def optimize(config: PortfolioRequest, db=Depends(get_db)):
    prepared, ready = inputs(db, config)
    return execute(prepared, ready, config, "optimize")


@router.post("/compare", response_model=PortfolioResponse)
def compare(config: PortfolioRequest, db=Depends(get_db)):
    prepared, ready = inputs(db, config)
    return execute(prepared, ready, config, "compare")


@router.post("/sensitivity", response_model=PortfolioResponse)
def sensitivity(config: PortfolioRequest, db=Depends(get_db)):
    prepared, ready = inputs(db, config)
    return execute(prepared, ready, config, "sensitivity")
