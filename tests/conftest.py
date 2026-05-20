from collections.abc import Generator
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import database
import main
from database import Base, get_db

ORIGINAL_ENGINE = database.engine
ORIGINAL_SESSION_LOCAL = database.SessionLocal


@pytest.fixture()
def test_engine() -> Generator:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.engine = engine
    main.engine = engine
    database.SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    database.engine = ORIGINAL_ENGINE
    database.SessionLocal = ORIGINAL_SESSION_LOCAL
    main.engine = ORIGINAL_ENGINE


@pytest.fixture()
def db_session_factory(test_engine):
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        expire_on_commit=False,
    )


@pytest.fixture()
def app(db_session_factory):
    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    yield main.app
    main.app.dependency_overrides.clear()