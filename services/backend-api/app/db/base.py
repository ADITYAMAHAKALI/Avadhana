"""Declarative base shared by every ORM model.

Kept in its own module (rather than defined inline in `app/models/*.py`)
so Alembic's `env.py` can import a single `Base.metadata` without also
importing model modules directly (avoids circular imports once models
start referencing each other via relationships).
"""

from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


@event.listens_for(Base, "init", propagate=True)
def _apply_python_side_defaults_eagerly(target, args, kwargs) -> None:
    """Populates every column with a Python-side `default=` (id, status,
    reputation, started_at, lock_expires_at, created_at, ...)
    immediately at object construction, not deferred until the ORM
    flushes the object to a session.

    Why this matters: SQLAlchemy's Python-side `default=` only fires at
    INSERT time. That's fine for request handlers (which always commit
    through a real Session), but `app/services/*` construct these model
    objects and hand them straight to repo ports — and the FAKE repo
    implementations used in unit tests (`tests/unit/fakes.py`) are plain
    dicts/lists with no session/flush step to ever trigger the default.
    Without this, every fake-backed unit test would see
    `commitment.id is None` (colliding every commitment under one dict
    key) and `user.reputation is None` (crashing on `+=`). Eagerly
    applying defaults here (via SQLAlchemy's `init` mapper event, which
    fires after the instrumented `__init__` sets attributes from
    `kwargs` but doesn't touch unset columns) keeps model construction
    behavior identical whether or not a session is involved — exactly
    what makes the interface/impl split testable against fakes.
    """
    for column in target.__table__.columns:
        if column.name in kwargs:
            continue
        if getattr(target, column.name, None) is not None:
            continue
        default = column.default
        if default is None:
            continue
        if default.is_callable:
            # SQLAlchemy wraps callables to accept an ExecutionContext
            # arg; None is safe here since none of this service's
            # defaults (uuid4, utcnow, literal status strings) use it.
            value = default.arg(None)
        elif default.is_scalar:
            value = default.arg
        else:
            continue
        setattr(target, column.name, value)
