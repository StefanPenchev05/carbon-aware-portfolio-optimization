import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceOut(ORM):
    id: int
    name: str
    reference: str
    synthetic: bool
    imported_at: datetime
    notes: str


class CompanyCSV(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    isin: Annotated[str, Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]
    ticker: Annotated[str, Field(min_length=1, max_length=30)]
    exchange: Annotated[str, Field(min_length=1, max_length=50)]
    sector: Literal["Energy", "Industrials", "Pharmaceuticals"]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class PriceCSV(BaseModel):
    isin: str
    date: date
    close: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    adjusted_close: Annotated[float | None, Field(gt=0, allow_inf_nan=False)] = None
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]

    @field_validator("date", mode="before")
    @classmethod
    def iso_date(cls, value):
        if isinstance(value, str):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("Use YYYY-MM-DD dates")
            return date.fromisoformat(value)
        return value


class EmissionCSV(BaseModel):
    isin: str
    year: Annotated[int, Field(ge=1900, le=2200)]
    scope1: Annotated[float | None, Field(ge=0, allow_inf_nan=False)] = None
    scope2: Annotated[float | None, Field(ge=0, allow_inf_nan=False)] = None
    scope3: Annotated[float | None, Field(ge=0, allow_inf_nan=False)] = None
    units: Annotated[str, Field(min_length=1, max_length=50)]
    methodology: Annotated[str, Field(min_length=1, max_length=200)]
    notes: str = ""


class CompanyOut(CompanyCSV, ORM):
    id: int
    source: SourceOut


class PriceOut(ORM):
    date: date
    close: float
    adjusted_close: float | None
    currency: str
    source: SourceOut


class EmissionOut(ORM):
    year: int
    scope1: float | None
    scope2: float | None
    scope3: float | None
    units: str
    methodology: str
    notes: str
    source: SourceOut


class CoverageOut(BaseModel):
    company_id: int
    name: str
    price_count: int
    emission_count: int
    has_reported_scopes: bool


class MembershipCSV(BaseModel):
    isin: str
    index_name: Annotated[str, Field(min_length=1, max_length=100)]
    as_of: date

    @field_validator("as_of", mode="before")
    @classmethod
    def iso_date(cls, value):
        return PriceCSV.iso_date(value)
