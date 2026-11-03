"""Transactional CSV adapter. Conflicting observations are errors, never silent overwrites."""

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.models.entities import CarbonEmission, Company, IndexMembership, Source, StockPrice
from app.schemas.data import CompanyCSV, EmissionCSV, MembershipCSV, PriceCSV

FORMATS = {
    "companies": (CompanyCSV, Company),
    "prices": (PriceCSV, StockPrice),
    "emissions": (EmissionCSV, CarbonEmission),
    "memberships": (MembershipCSV, IndexMembership),
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
                    if value.strip() == "" and key in {"adjusted_close", "scope1", "scope2", "scope3"}
                    else value.strip()
                )
                for key, value in row.items()
            }
            rows.append(schema.model_validate(cleaned).model_dump())
        except ValueError as exc:
            raise ImportError(f"{path}, row {number}: {exc}") from exc
    return rows


def import_csv(db, kind, path, *, source_name, reference, synthetic, notes=""):
    schema, model = FORMATS[kind]
    rows = read_rows(path, schema)
    source = db.scalar(select(Source).where(Source.name == source_name))
    if source and (source.reference != reference or source.synthetic != synthetic or source.notes != notes):
        raise ImportError("Source metadata conflicts with existing source")
    if source is None:
        source = Source(name=source_name, reference=reference, synthetic=synthetic, notes=notes)
        db.add(source)
        db.flush()
    inserted = skipped = 0
    for number, row in enumerate(rows, 2):
        row = dict(row)
        isin = row.pop("isin")
        if kind == "companies":
            row["isin"] = isin
            key = {"isin": isin}
        else:
            company = db.scalar(select(Company).where(Company.isin == isin))
            if company is None:
                raise ImportError(f"{path}, row {number}: unknown ISIN {isin}; import companies first")
            row["company_id"] = company.id
            key = {"company_id": company.id, "source_id": source.id}
            fields = {
                "prices": ["date"],
                "emissions": ["year", "methodology", "units"],
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
    parser.add_argument("--source", required=True)
    parser.add_argument("--reference", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--synthetic", action="store_true")
    group.add_argument("--real", action="store_true")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    try:
        with SessionLocal.begin() as db:
            result = import_csv(
                db,
                args.kind,
                args.path,
                source_name=args.source,
                reference=args.reference,
                synthetic=args.synthetic,
                notes=args.notes,
            )
        print(result)
    except SQLAlchemyError:
        parser.exit(
            1,
            "Import failed: database operation failed; transaction rolled back. Check connectivity and constraints.\n",
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Import failed: {exc}\n")


if __name__ == "__main__":
    main()
