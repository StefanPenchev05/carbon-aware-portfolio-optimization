"""Transactional CSV adapter. Conflicting observations are errors, never silent overwrites."""

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.models.entities import CarbonEmission, Company, FXRate, ImportRun, IndexMembership, Source, StockPrice
from app.schemas.data import FXCSV, CompanyCSV, EmissionCSV, MembershipCSV, PriceCSV

FORMATS = {
    "companies": (CompanyCSV, Company),
    "prices": (PriceCSV, StockPrice),
    "emissions": (EmissionCSV, CarbonEmission),
    "memberships": (MembershipCSV, IndexMembership),
    "fx": (FXCSV, FXRate),
}


class ImportError(ValueError):
    pass


def read_rows(path, schema):
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {name for name, field in schema.model_fields.items() if field.is_required()}
    if not required.issubset(frame.columns) or set(frame.columns) - set(schema.model_fields):
        raise ImportError(f"{path}: invalid headers; required {sorted(required)}")
    rows = []
    for number, row in enumerate(frame.to_dict("records"), 2):
        try:
            cleaned = {
                key: (
                    None
                    if value.strip() == ""
                    and key
                    in {
                        "adjusted_close",
                        "scope1",
                        "scope2",
                        "scope3",
                        "disclosure_date",
                        "disclosure_reference",
                        "original_sector",
                        "classification_system",
                        "sector_mapping_notes",
                    }
                    else value.strip()
                )
                for key, value in row.items()
            }
            rows.append(schema.model_validate(cleaned).model_dump())
        except ValueError as exc:
            raise ImportError(f"{path}, row {number}: {exc}") from exc
    return rows


def import_csv(db, kind, path, *, source_name, reference, synthetic, notes="", provenance=None):
    schema, model = FORMATS[kind]
    rows = read_rows(path, schema)
    if not synthetic and not provenance:
        raise ImportError("Real imports require a verified manifest")
    source_metadata = provenance or {}

    source = db.scalar(select(Source).where(Source.name == source_name))
    if source and (source.reference != reference or source.synthetic != synthetic or source.notes != notes):
        raise ImportError("Source metadata conflicts with existing source")
    if source and any(getattr(source, key) != value for key, value in source_metadata.items() if key != "retrieved_at"):
        raise ImportError("Immutable source manifest conflicts; create a new source version")
    if source is None:
        source = Source(name=source_name, reference=reference, synthetic=synthetic, notes=notes, **source_metadata)
        db.add(source)
        db.flush()
    inserted = skipped = 0
    for number, row in enumerate(rows, 2):
        row = dict(row)
        isin = row.pop("isin", None)
        if not synthetic and isin:
            from app.services.provenance import valid_isin

            if not valid_isin(isin):
                raise ImportError(f"{path}, row {number}: invalid ISIN checksum")
        if kind == "companies":
            row["isin"] = isin
            key = {"isin": isin}
            if not synthetic and not all(
                row[k] for k in ("original_sector", "classification_system", "sector_mapping_notes")
            ):
                raise ImportError("Real company needs source classification and justified research-sector mapping")
        elif kind == "fx":
            key = {k: row[k] for k in ("date", "base_currency", "quote_currency")}
            key["source_id"] = source.id
        else:
            company = db.scalar(select(Company).where(Company.isin == isin))
            if company is None:
                raise ImportError(f"{path}, row {number}: unknown ISIN {isin}; import companies first")
            if db.get(Source, company.source_id).synthetic != synthetic:
                raise ImportError("Cannot mix real and synthetic company/observation sources")
            if kind == "emissions" and not synthetic:
                if not row["disclosure_reference"]:
                    raise ImportError("Real emissions require an original disclosure reference")
                for scope in ("scope1", "scope2", "scope3"):
                    if row[scope] is not None and row[scope + "_status"] == "unknown":
                        raise ImportError(f"Real {scope} value requires reported/estimated status")
            if (
                kind == "prices"
                and not synthetic
                and row["adjusted_close"] is not None
                and row["adjustment_method"] == "unknown"
            ):
                raise ImportError("Adjusted price requires adjustment metadata")
            if kind == "prices" and row["currency"] != company.currency:
                raise ImportError(
                    "Price currency differs from selected company listing; verify listing or explicit conversion"
                )
            if kind == "prices" and row["date"].weekday() >= 5:
                raise ImportError("Weekend price date requires a separately validated market-calendar adapter")
            row["company_id"] = company.id
            key = {"company_id": company.id, "source_id": source.id}
            fields = {
                "prices": ["date"],
                "emissions": ["year", "methodology", "units", "scope2_basis"],
                "memberships": ["index_name", "as_of"],
            }
            key.update({k: row[k] for k in fields[kind]})
        row["source_id"] = source.id
        existing = db.scalar(select(model).filter_by(**key))
        if existing:
            if any(getattr(existing, k) != v for k, v in row.items()):
                raise ImportError(f"{path}, row {number}: conflicting duplicate {key}")
            skipped += 1
        else:
            db.add(model(**row))
            db.flush()
            inserted += 1
    return {"inserted": inserted, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=FORMATS)
    parser.add_argument("path", type=Path)
    parser.add_argument("--source")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--reference")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--synthetic", action="store_true")
    group.add_argument("--real", action="store_true")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    from app.services.provenance import load_manifest, sha256

    provenance = None
    try:
        if args.manifest:
            manifest, digest = load_manifest(args.manifest, args.path)
            if manifest.synthetic != args.synthetic:
                raise ValueError("Manifest and dataset flag disagree")
            if (
                args.source
                and args.source != manifest.source_name
                or args.reference
                and args.reference != manifest.reference
            ):
                raise ValueError("CLI and manifest provenance disagree")
            args.source, args.reference, args.notes = manifest.source_name, manifest.reference, manifest.notes
            provenance = dict(
                retrieved_at=manifest.retrieved_at, license_reference=manifest.license_reference, manifest_sha256=digest
            )
        if not args.source or not args.reference:
            raise ValueError("Provide source/reference or a manifest")
        with SessionLocal.begin() as db:
            result = import_csv(
                db,
                args.kind,
                args.path,
                source_name=args.source,
                reference=args.reference,
                synthetic=args.synthetic,
                notes=args.notes,
                provenance=provenance,
            )
            db.add(
                ImportRun(
                    source_name=args.source,
                    synthetic=args.synthetic,
                    kind=args.kind,
                    file_sha256=sha256(args.path),
                    status="success",
                    **result,
                )
            )
        print(result)
    except SQLAlchemyError:
        parser.exit(
            1,
            "Import failed: database operation failed; transaction rolled back. Check connectivity and constraints.\n",
        )
    except (ValueError, OSError) as exc:
        try:
            count = len(pd.read_csv(args.path))
            with SessionLocal.begin() as db:
                db.add(
                    ImportRun(
                        source_name=args.source or "unresolved",
                        synthetic=args.synthetic,
                        kind=args.kind,
                        file_sha256=sha256(args.path),
                        status="rejected",
                        rejected=count,
                        detail=str(exc)[:4000],
                    )
                )
        except (SQLAlchemyError, ValueError, OSError):
            pass
        parser.exit(1, f"Import failed: {exc}\n")


if __name__ == "__main__":
    main()
