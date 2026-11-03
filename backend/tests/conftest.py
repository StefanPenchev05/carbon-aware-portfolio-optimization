from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.services.ingest import import_csv

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"
META = dict(source_name="Synthetic fixture", reference="local samples", synthetic=True)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def seeded(db):
    for kind in ("companies", "prices", "emissions"):
        import_csv(db, kind, SAMPLES / f"synthetic_{kind}.csv", **META)
    db.commit()
    return db


@pytest.fixture
def client(seeded):
    app.dependency_overrides[get_db] = lambda: seeded
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
