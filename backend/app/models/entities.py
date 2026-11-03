from datetime import UTC, date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    reference: Mapped[str] = mapped_column(String(1000))
    synthetic: Mapped[bool] = mapped_column(Boolean)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    license_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ImportRun(Base):
    __tablename__ = "import_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(200))
    synthetic: Mapped[bool] = mapped_column(Boolean)
    kind: Mapped[str] = mapped_column(String(30))
    file_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))
    inserted: Mapped[int] = mapped_column(default=0)
    skipped: Mapped[int] = mapped_column(default=0)
    rejected: Mapped[int] = mapped_column(default=0)
    detail: Mapped[str] = mapped_column(String(4000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (CheckConstraint("length(isin) = 12"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    isin: Mapped[str] = mapped_column(String(12), unique=True)
    original_sector: Mapped[str | None] = mapped_column(String(200), nullable=True)
    classification_system: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sector_mapping_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    ticker: Mapped[str] = mapped_column(String(30))
    exchange: Mapped[str] = mapped_column(String(50))
    sector: Mapped[str] = mapped_column(String(50), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))


class StockPrice(Base):
    __tablename__ = "stock_prices"
    __table_args__ = (
        UniqueConstraint("company_id", "date", "source_id"),
        CheckConstraint("close > 0"),
        CheckConstraint("adjusted_close IS NULL OR adjusted_close > 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    close: Mapped[float] = mapped_column(Float)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjustment_method: Mapped[str] = mapped_column(String(200), default="unknown", server_default="unknown")
    currency: Mapped[str] = mapped_column(String(3))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))


class CarbonEmission(Base):
    __tablename__ = "carbon_emissions"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "year", "source_id", "methodology", "units", "scope2_basis", name="uq_emission_disclosure"
        ),
        CheckConstraint("year >= 1900 AND year <= 2200"),
        CheckConstraint("scope1 IS NULL OR scope1 >= 0"),
        CheckConstraint("scope2 IS NULL OR scope2 >= 0"),
        CheckConstraint("scope3 IS NULL OR scope3 >= 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    scope1: Mapped[float | None] = mapped_column(Float, nullable=True)
    scope2: Mapped[float | None] = mapped_column(Float, nullable=True)
    scope3: Mapped[float | None] = mapped_column(Float, nullable=True)
    scope1_status: Mapped[str] = mapped_column(String(20), default="unknown", server_default="unknown")
    scope2_status: Mapped[str] = mapped_column(String(20), default="unknown", server_default="unknown")
    scope3_status: Mapped[str] = mapped_column(String(20), default="unknown", server_default="unknown")
    scope2_basis: Mapped[str] = mapped_column(String(20), default="unknown", server_default="unknown")
    disclosure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disclosure_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    units: Mapped[str] = mapped_column(String(50))
    methodology: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))


class IndexMembership(Base):
    __tablename__ = "index_memberships"
    __table_args__ = (UniqueConstraint("company_id", "index_name", "as_of", "source_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    index_name: Mapped[str] = mapped_column(String(100))
    as_of: Mapped[date] = mapped_column(Date)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))


class FXRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("date", "base_currency", "quote_currency", "source_id"),
        CheckConstraint("rate > 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    base_currency: Mapped[str] = mapped_column(String(3))
    quote_currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[float] = mapped_column(Float)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
