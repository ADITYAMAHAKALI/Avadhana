"""SQLAlchemy engine/session wiring.

One module-level engine per process, built lazily from `DATABASE_URL` so
importing this module doesn't require the env var to be set (useful for
tooling that imports `app.models` without connecting, e.g. Alembic
autogenerate against a throwaway URL). `get_session()` is the FastAPI
dependency; it's a generator so FastAPI closes the session after the
request regardless of success/failure.

Tests never import `engine` from here directly — `tests/integration/
conftest.py` builds its own SQLite in-memory engine and overrides the
`get_session` dependency, so this module's Postgres-flavored engine is
never touched in CI.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _build_engine():
    return create_engine(settings.database_url, pool_pre_ping=True)


# Created lazily on first use via a simple module-level cache rather than
# at import time, so `DATABASE_URL` is only required once the app actually
# starts serving requests (or a migration runs) — not merely on import.
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_sessionmaker() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False)
    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a request-scoped SQLAlchemy session."""
    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
