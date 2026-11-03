import json
import math
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.models.entities import ImportRun
from app.services.ecb import parse_ecb
from app.services.ingest import ImportError, import_csv
from app.services.preparation import align_emissions, convert_to_eur, normalize_emissions, prepare_returns
from app.services.provenance import load_manifest, sha256, valid_isin
from app.services.quality import data_quality


@pytest.fixture
def real(db, tmp_path):
    path = tmp_path / "companies.csv"
    # Genuine ISIN identifier used only as a software fixture; values below are NOT acquired real observations.
    path.write_text(
        "name,isin,ticker,exchange,sector,currency,original_sector,classification_system,sector_mapping_notes\nFixture,GB00BP6MXD84,FIX,XTEST,Energy,EUR,Test Oil,Test taxonomy,Test-only mapping\n"
    )
    metadata = dict(
        source_name="Real-flagged unit-test fixture",
        reference="Test only",
        synthetic=False,
        provenance=dict(
            retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            license_reference="test fixture permission",
            manifest_sha256="a" * 64,
        ),
    )
    import_csv(db, "companies", path, **metadata)
    return db, metadata


def test_identifiers():
    assert valid_isin("GB00BP6MXD84")
    assert not valid_isin("GB00BP6MXD85")
    assert not valid_isin("SHELL")


def test_real_requires_manifest(db, tmp_path):
    path = tmp_path / "fx.csv"
    path.write_text("date,base_currency,quote_currency,rate\n2025-01-02,EUR,GBP,0.8\n")
    with pytest.raises(ImportError, match="manifest"):
        import_csv(db, "fx", path, source_name="test", reference="test", synthetic=False)


def test_real_isin_currency_and_separation(real, tmp_path):
    db, metadata = real
    path = tmp_path / "prices.csv"
    path.write_text("isin,date,close,currency\nGB00BP6MXD84,2025-01-02,100,USD\n")
    with pytest.raises(ImportError, match="currency"):
        import_csv(db, "prices", path, **metadata)
    path.write_text("isin,date,close,currency\nGB00BP6MXD84,2025-01-02,100,EUR\n")
    with pytest.raises(ImportError, match="mix real and synthetic"):
        import_csv(db, "prices", path, source_name="synthetic", reference="test", synthetic=True)
    assert import_csv(db, "prices", path, **metadata)["inserted"] == 1
    assert import_csv(db, "prices", path, **metadata)["skipped"] == 1


def test_scope2_basis_and_quality(real, tmp_path):
    db, metadata = real
    path = tmp_path / "emissions.csv"
    path.write_text(
        "isin,year,scope1,scope2,units,methodology,scope1_status,scope2_status,scope2_basis,disclosure_date,disclosure_reference\nGB00BP6MXD84,2024,100,200,kgCO2e,test,reported,estimated,market-based,2025-01-02,test report page 1\nGB00BP6MXD84,2024,100,300,kgCO2e,test,reported,reported,location-based,,test report page 2\n"
    )
    assert import_csv(db, "emissions", path, **metadata)["inserted"] == 2
    assert import_csv(db, "emissions", path, **metadata)["skipped"] == 2
    report = data_quality(db)
    assert report["company_count"] == 1 and report["estimated_percent"] == 25
    assert report["missing_publication_dates"] == 1
    assert report["companies"][0]["missing_scope_values"]["scope3"] == 2
    assert data_quality(db, True)["company_count"] == 0


def test_missing_scope_status_rejected(real, tmp_path):
    db, metadata = real
    path = tmp_path / "bad.csv"
    path.write_text("isin,year,scope1,units,methodology,disclosure_reference\nGB00BP6MXD84,2024,10,tCO2e,test,report\n")
    with pytest.raises(ImportError, match="status"):
        import_csv(db, "emissions", path, **metadata)


def test_manifest_hashes(tmp_path):
    path = tmp_path / "fx.csv"
    path.write_text("sample test-only content")
    raw = tmp_path / "raw.txt"
    raw.write_text("raw fixture")
    manifest = dict(
        source_name="test",
        reference="test",
        retrieved_at="2026-01-01T00:00:00Z",
        license_reference="test",
        usage_permission="test only",
        synthetic=False,
        files={path.name: sha256(path)},
        raw_files={raw.name: sha256(raw)},
    )
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest))
    assert load_manifest(mp, path)[0].synthetic is False
    raw.write_text("changed")
    with pytest.raises(ValueError, match="snapshot"):
        load_manifest(mp, path)
    raw.write_text("raw fixture")
    path.write_text("changed CSV")
    with pytest.raises(ValueError, match="SHA-256"):
        load_manifest(mp, path)


@pytest.mark.parametrize("unit,value", [("kgCO2e", 0.001), ("tCO2e", 1), ("MtCO2e", 1_000_000)])
def test_normalization(unit, value):
    row = normalize_emissions(dict(units=unit, scope1=1, scope2=None, scope3=0))
    assert row["scope1"] == 1 and row["units"] == unit
    assert row["normalized_scopes"] == dict(scope1=value, scope2=None, scope3=0)


def test_unknown_unit():
    assert normalize_emissions(dict(units="tonnes CO2", scope1=1))["normalized_scopes"]["scope1"] is None


def prices():
    return [
        dict(
            company_id=1,
            synthetic=False,
            source_id=1,
            date=d,
            close=p,
            adjusted_close=p,
            currency="EUR",
            adjustment_method="fixture adjusted",
        )
        for d, p in (("2025-01-03", 100), ("2025-01-06", 110), ("2025-01-08", 121))
    ]


def emission(**extra):
    return dict(
        company_id=1,
        synthetic=False,
        source_id=2,
        year=2024,
        scope1=10,
        scope1_status="reported",
        scope2=None,
        scope2_status="unknown",
        scope3=None,
        scope3_status="unknown",
        units="tCO2e",
        methodology="fixture",
        scope2_basis="location-based",
        disclosure_date="2025-01-06",
        **extra,
    )


def test_returns_and_calendar():
    result = prepare_returns(list(reversed(prices())))
    assert result[0]["simple_return"] is None
    assert result[1]["simple_return"] == pytest.approx(0.1)
    assert result[1]["log_return"] == pytest.approx(math.log(1.1))
    assert result[2]["simple_return"] is None
    assert result[2]["missing_expected_dates"] == [date(2025, 1, 7)]
    calendar = [r["date"] for r in prices()]  # Explicit test calendar treats Jan 7 as closed.
    assert prepare_returns(prices(), expected_dates=calendar)[2]["simple_return"] == pytest.approx(0.1)


@pytest.mark.parametrize(
    "change,error",
    [
        (dict(currency="USD"), "currency"),
        (dict(source_id=99), "source"),
        (dict(adjustment_method="different"), "adjustment"),
    ],
)
def test_returns_ambiguous(change, error):
    rows = prices()
    rows[1].update(change)
    with pytest.raises(ValueError, match=error):
        prepare_returns(rows)


def test_duplicate_prices():
    with pytest.raises(ValueError, match="Duplicate"):
        prepare_returns(prices() + [prices()[0]])


@pytest.mark.parametrize("price", [-1, 0, float("nan"), float("inf")])
def test_invalid_prices(price):
    rows = prices()
    rows[0]["adjusted_close"] = price
    with pytest.raises(ValueError, match="positive"):
        prepare_returns(rows)


def test_missing_prices_and_adjustment():
    rows = prices()
    rows[0]["adjusted_close"] = None
    assert prepare_returns(rows)[1]["simple_return"] is None
    for row in rows:
        row["adjustment_method"] = "unknown"
    assert all(r["simple_return"] is None for r in prepare_returns(rows))


def test_pit_no_lookahead_or_synthetic_leakage():
    result = align_emissions(prices(), [emission()])
    assert result[0]["emission"] is None and result[1]["emission"] is None
    assert result[2]["emission"]["year"] == 2024
    unknown = emission()
    unknown["disclosure_date"] = None
    assert all(r["emission"] is None for r in align_emissions(prices(), [unknown]))
    synthetic = emission()
    synthetic["synthetic"] = True
    assert all(r["emission"] is None for r in align_emissions(prices(), [synthetic]))


def test_descriptive_warning_and_ambiguity():
    e = emission()
    e["year"] = 2025
    e["disclosure_date"] = "2026-03-01"
    result = align_emissions(prices(), [e], mode="descriptive")
    assert result[0]["emission"] and result[0]["alignment_warning"]
    assert not result[0]["temporally_verified"]
    other = emission()
    other["scope2_basis"] = "market-based"
    with pytest.raises(ValueError, match="single"):
        align_emissions(prices(), [emission(), other])
    with pytest.raises(ValueError, match="vintage"):
        align_emissions(prices(), [emission(), emission()])


def test_fx_conversion():
    fx = dict(date="2025-01-03", base_currency="EUR", quote_currency="GBP", rate=0.8)
    assert convert_to_eur(80, "GBP", fx, "2025-01-03") == 100
    assert convert_to_eur(80, "EUR", None, "2025-01-03") == 80
    with pytest.raises(ValueError):
        convert_to_eur(80, "USD", fx, "2025-01-03")
    with pytest.raises(ValueError):
        convert_to_eur(80, "GBP", fx, "2025-01-06")


def test_ecb_adapter():
    xml = b'<Envelope><Cube><Cube time="2025-01-02"><Cube currency="GBP" rate="0.8"/></Cube></Cube></Envelope>'
    rows = parse_ecb(xml, date(2025, 1, 1), date(2025, 1, 3), ["GBP"])
    assert rows[0]["base_currency"] == "EUR" and rows[0]["rate"] == 0.8
    with pytest.raises(ValueError, match="Missing"):
        parse_ecb(xml, date(2025, 1, 1), date(2025, 1, 3), ["CHF"])


def test_quality_endpoint_and_rejections(client, seeded):
    seeded.add(
        ImportRun(
            source_name="fixture", synthetic=False, kind="prices", file_sha256="a" * 64, status="rejected", rejected=4
        )
    )
    seeded.flush()
    real = client.get("/api/data/quality").json()
    assert real["company_count"] == 0 and real["rejected_import_rows"] == 4
    assert client.get("/api/data/quality?synthetic=true").json()["company_count"] == 3
    coverage = client.get("/api/data/coverage").json()
    assert coverage[0]["quality"]["synthetic"]
    assert client.get("/api/companies/1/emissions").json()[0]["scope2_basis"] == "unknown"


def test_quality_usable_pair(real, tmp_path):
    db, metadata = real
    path = tmp_path / "prices.csv"
    path.write_text(
        "isin,date,close,adjusted_close,currency,adjustment_method\nGB00BP6MXD84,2025-01-03,100,100,EUR,fixture adjusted\nGB00BP6MXD84,2025-01-06,110,110,EUR,fixture adjusted\n"
    )
    import_csv(db, "prices", path, **metadata)
    path = tmp_path / "emissions.csv"
    path.write_text(
        "isin,year,scope1,units,methodology,scope1_status,disclosure_date,disclosure_reference\nGB00BP6MXD84,2024,100,kgCO2e,test,reported,2025-01-02,fixture report\n"
    )
    import_csv(db, "emissions", path, **metadata)
    report = data_quality(db)
    assert report["usable_matched_observations"] == 1
    assert report["currency_distribution"] == {"EUR": 2}
    assert report["reported_percent"] == 100


def test_cli_rejection_audit(seeded, tmp_path, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from app.models.entities import StockPrice
    from app.services import ingest

    path = tmp_path / "prices.csv"
    path.write_text("isin,date,close,currency\nZZ0000000001,2025-02-03,100,EUR\nUNKNOWN,2025-02-03,100,EUR\n")
    monkeypatch.setattr(ingest, "SessionLocal", sessionmaker(seeded.bind))
    monkeypatch.setattr(
        "sys.argv",
        ["ingest", "prices", str(path), "--source", "Synthetic fixture", "--reference", "local samples", "--synthetic"],
    )
    with pytest.raises(SystemExit) as error:
        ingest.main()
    assert error.value.code == 1
    run = seeded.scalar(select(ImportRun))
    assert run.status == "rejected" and run.rejected == 2
    assert "unknown ISIN" in run.detail
    assert not seeded.scalars(select(StockPrice).where(StockPrice.date == date(2025, 2, 3))).all()


def test_duplicate_in_same_file(real, tmp_path):
    db, metadata = real
    path = tmp_path / "prices.csv"
    path.write_text("isin,date,close,currency\nGB00BP6MXD84,2025-01-03,100,EUR\nGB00BP6MXD84,2025-01-03,100,EUR\n")
    assert import_csv(db, "prices", path, **metadata) == {"inserted": 1, "skipped": 1}


def test_bad_real_isin_and_adjustment(real, tmp_path):
    db, metadata = real
    path = tmp_path / "prices.csv"
    path.write_text("isin,date,close,currency\nGB00BP6MXD85,2025-01-03,100,EUR\n")
    with pytest.raises(ImportError, match="checksum"):
        import_csv(db, "prices", path, **metadata)
    path.write_text("isin,date,close,adjusted_close,currency\nGB00BP6MXD84,2025-01-03,100,100,EUR\n")
    with pytest.raises(ImportError, match="adjustment"):
        import_csv(db, "prices", path, **metadata)


def test_manifest_cli_is_immutable(tmp_path, monkeypatch):
    from app.services import provenance

    csv_path = tmp_path / "prices.csv"
    csv_path.write_text("Header-only test fixture\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "provenance",
            str(tmp_path),
            "--source",
            "fixture",
            "--reference",
            "fixture export",
            "--retrieved-at",
            "2026-01-01T00:00:00Z",
            "--license-reference",
            "fixture only",
            "--permission",
            "self-authored software test fixture",
            "--files",
            "prices.csv",
        ],
    )
    provenance.main()
    assert load_manifest(tmp_path / "manifest.json", csv_path)[0].source_name == "fixture"
    with pytest.raises(FileExistsError):
        provenance.main()
