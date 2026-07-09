"""Integration test fixtures: a real SQLAlchemy engine/session against an
in-memory SQLite database (not Postgres — CI has no Postgres service
container, per the build brief), plus a FastAPI TestClient with
`get_session` overridden to use that engine.

This proves the ORM layer itself works (models, relationships, unique
constraints) without requiring a live Postgres anywhere. Production/dev
still run on Postgres (see app/db/session.py) — this is a test-only
substitution via FastAPI's dependency_overrides, never touching
`DATABASE_URL` or the real engine module.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Must be set before any app module reads Settings (e.g. via import
# chains that construct `settings.jwt_secret`), since app.core.config
# raises if these env vars are missing. Set at collection time so every
# test module in this package gets a working environment even if it
# imports `app.main` at module scope.
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@localhost/unused")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")

from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture()
def engine():
    # StaticPool + check_same_thread=False: keeps a single SQLite
    # connection alive for the lifetime of the engine so all sessions in
    # a test see the same in-memory database (plain in-memory SQLite is
    # otherwise per-connection and would look empty across sessions).
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine):
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def _get_session_override():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _get_session_override
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
