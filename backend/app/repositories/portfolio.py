"""Observation retrieval only; no estimation or optimization in this module."""

import json
import os
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select

from app.models.entities import CarbonEmission, Company, Source, StockPrice
from app.schemas.portfolio import PortfolioReview
from app.services.portfolio import PortfolioError
from app.services.synthetic_portfolio import dataset


def load_dataset(db, mode):
    if mode == "synthetic":
        return dataset()
    sources = {s.id: s for s in db.scalars(select(Source).where(Source.synthetic.is_(False)))}
    companies = [
        dict(id=c.id, name=c.name, sector=c.sector) for c in db.scalars(select(Company)) if c.source_id in sources
    ]
    ids = {c["id"] for c in companies}

    def rows(model):
        return [
            {**{col.name: getattr(r, col.name) for col in model.__table__.columns}, "synthetic": False}
            for r in db.scalars(select(model))
            if r.company_id in ids and r.source_id in sources
        ]

    path = os.environ.get("PORTFOLIO_REVIEW_FILE")
    try:
        raw = json.loads(Path(path).read_text()).get("real", {}) if path else {}
        reviews = {key: PortfolioReview.model_validate(value).model_dump(mode="json") for key, value in raw.items()}
    except (OSError, ValueError, TypeError, AttributeError, ValidationError) as exc:
        raise PortfolioError("Portfolio review file invalid or unreadable; verification refused") from exc
    return dict(
        companies=companies,
        prices=rows(StockPrice),
        emissions=rows(CarbonEmission),
        reviews=reviews,
        synthetic=False,
        sources={str(k): f"{v.name} | {v.reference}" for k, v in sources.items()},
        provenance="Real source-labelled observations; local analyst review required; not independently certified",
    )
