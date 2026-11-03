import pytest
from conftest import META, SAMPLES
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.entities import CarbonEmission, Company
from app.schemas.data import PriceCSV
from app.services.ingest import ImportError, import_csv, read_rows


def test_idempotency(seeded):
    for kind, count in (("companies", 3), ("prices", 7), ("emissions", 3)):
        assert import_csv(seeded, kind, SAMPLES / f"synthetic_{kind}.csv", **META) == {"inserted": 0, "skipped": count}


def test_missing_scope(seeded):
    row = seeded.scalar(select(CarbonEmission).where(CarbonEmission.year == 2023))
    assert row.scope3 is None


def test_isin_unique_but_ticker_not(seeded):
    row = seeded.get(Company, 1)
    seeded.add(
        Company(
            name="Another",
            isin="ZZ0000000004",
            ticker=row.ticker,
            exchange="OTHER",
            sector="Energy",
            currency="EUR",
            source_id=row.source_id,
        )
    )
    seeded.flush()
    seeded.add(
        Company(
            name="Duplicate",
            isin=row.isin,
            ticker="OTHER",
            exchange="OTHER",
            sector="Energy",
            currency="EUR",
            source_id=row.source_id,
        )
    )
    with pytest.raises(IntegrityError):
        seeded.flush()


@pytest.mark.parametrize("date", ["2025-02-30", "02/03/2025", "2025-01-02T12:00:00"])
def test_invalid_dates(date):
    with pytest.raises(ValueError):
        PriceCSV(isin="ZZ0000000001", date=date, close=1, currency="EUR")


@pytest.mark.parametrize("close", ["NaN", "inf", "-1", "0"])
def test_invalid_prices(close):
    with pytest.raises(ValueError):
        PriceCSV(isin="ZZ0000000001", date="2025-01-02", close=close, currency="EUR")


def test_headers_and_row_errors(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("date,close\n2025-01-02,1\n")
    with pytest.raises(ImportError, match="headers"):
        read_rows(path, PriceCSV)
    path.write_text("isin,date,close,currency\nZZ0000000001,bad,1,EUR\n")
    with pytest.raises(ImportError, match="row 2"):
        read_rows(path, PriceCSV)


def test_conflicting_duplicate(seeded, tmp_path):
    path = tmp_path / "conflict.csv"
    path.write_text("isin,date,close,adjusted_close,currency\nZZ0000000001,2025-01-02,999,100,EUR\n")
    with pytest.raises(ImportError, match="conflicting duplicate"):
        import_csv(seeded, "prices", path, **META)


def test_unknown_company_and_rollback(db, tmp_path):
    path = tmp_path / "unknown.csv"
    path.write_text("isin,date,close,currency\nZZ0000000001,2025-01-02,100,EUR\n")
    with pytest.raises(ImportError, match="unknown ISIN"), db.begin():
        import_csv(db, "prices", path, **META)
    from app.models.entities import Source

    assert db.scalar(select(Source)) is None


def test_api(client):
    assert client.get("/api/health").json()["status"] == "ok"
    rows = client.get("/api/companies?sector=Energy").json()
    assert len(rows) == 1 and rows[0]["source"]["synthetic"]
    assert client.get("/api/companies/1").status_code == 200
    assert len(client.get("/api/companies/1/prices?start=2025-01-03&end=2025-01-03").json()) == 1
    assert client.get("/api/companies/1/emissions?start_year=2024").json()[0]["year"] == 2024
    assert client.get("/api/companies/3/emissions").json() == []
    assert client.get("/api/data/coverage").json()[2]["emission_count"] == 0


@pytest.mark.parametrize(
    "path,status",
    [
        ("/api/companies/999", 404),
        ("/api/companies/999/prices", 404),
        ("/api/companies/1/prices?start=no", 422),
        ("/api/companies/1/prices?start=2026-01-01&end=2025-01-01", 422),
        ("/api/companies/1/emissions?start_year=2025&end_year=2020", 422),
    ],
)
def test_api_errors(client, path, status):
    assert client.get(path).status_code == status
