from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.models.entities import CarbonEmission, StockPrice
from app.repositories import catalog
from app.schemas.data import CompanyOut, CoverageOut, EmissionOut, PriceOut

router = APIRouter(prefix="/api")


@router.get("/health")
def health(db=Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable") from None
    return {"status": "ok", "database": "connected"}


@router.get("/companies", response_model=list[CompanyOut])
def companies(sector: str | None = None, db=Depends(get_db)):
    return [catalog.serialize(db, c) for c in catalog.companies(db, sector)]


def require_company(db, company_id):
    item = catalog.company(db, company_id)
    if item is None:
        raise HTTPException(404, "Company not found")
    return item


@router.get("/companies/{company_id}", response_model=CompanyOut)
def company(company_id: int, db=Depends(get_db)):
    return catalog.serialize(db, require_company(db, company_id))


@router.get("/companies/{company_id}/prices", response_model=list[PriceOut])
def prices(company_id: int, start: date | None = None, end: date | None = None, db=Depends(get_db)):
    require_company(db, company_id)
    if start and end and start > end:
        raise HTTPException(422, "start must not be after end")
    return [catalog.serialize(db, p) for p in catalog.observations(db, StockPrice, company_id, start, end)]


@router.get("/companies/{company_id}/emissions", response_model=list[EmissionOut])
def emissions(
    company_id: int,
    start_year: int | None = Query(None, ge=1900, le=2200),
    end_year: int | None = Query(None, ge=1900, le=2200),
    db=Depends(get_db),
):
    require_company(db, company_id)
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(422, "start_year must not be after end_year")
    return [
        catalog.serialize(db, p) for p in catalog.observations(db, CarbonEmission, company_id, start_year, end_year)
    ]


@router.get("/data/coverage", response_model=list[CoverageOut])
def coverage(db=Depends(get_db)):
    return catalog.coverage(db)
