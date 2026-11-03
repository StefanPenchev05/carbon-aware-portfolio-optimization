from sqlalchemy import select

from app.models.entities import CarbonEmission, Company, Source, StockPrice


def companies(db, sector=None):
    query = select(Company).order_by(Company.name)
    if sector:
        query = query.where(Company.sector == sector)
    return db.scalars(query).all()


def company(db, company_id):
    return db.get(Company, company_id)


def serialize(db, record):
    data = {column.name: getattr(record, column.name) for column in record.__table__.columns}
    data["source"] = db.get(Source, record.source_id)
    if isinstance(record, CarbonEmission):
        from app.services.preparation import normalize_emissions

        data = normalize_emissions(data)
    return data


def observations(db, model, company_id, start=None, end=None):
    period = model.date if model is StockPrice else model.year
    query = select(model).where(model.company_id == company_id)
    if start is not None:
        query = query.where(period >= start)
    if end is not None:
        query = query.where(period <= end)
    return db.scalars(query.order_by(period, model.source_id)).all()


def coverage(db):
    from app.services.quality import data_quality

    quality = {r["company_id"]: r for flag in (False, True) for r in data_quality(db, flag)["companies"]}
    result = []
    for item in companies(db):
        prices = observations(db, StockPrice, item.id)
        emissions = observations(db, CarbonEmission, item.id)
        result.append(
            dict(
                quality=quality[item.id],
                company_id=item.id,
                name=item.name,
                price_count=len(prices),
                emission_count=len(emissions),
                has_reported_scopes=any(
                    any(getattr(e, s) is not None for s in ("scope1", "scope2", "scope3")) for e in emissions
                ),
            )
        )
    return result
