"""Alembic environment script.

Reads `DATABASE_URL` from the process environment (never from
alembic.ini) so the exact same env var that configures the running app
(see app.core.config.Settings.database_url) also configures migrations
— one source of truth, consistent with the "no hardcoded connection
strings" rule in CLAUDE.md's Security section. This also means
`alembic upgrade head` naturally targets whatever Postgres the current
shell/k8s pod is pointed at, without needing a separate migrations-only
config file.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `app.*` importable when Alembic is invoked from the
# services/backend-api/ directory (the expected working directory for
# `alembic upgrade head` per this service's README).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402  (import after sys.path fix-up)
from app.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    # Reuses app.core.config.Settings so migrations resolve DATABASE_URL
    # (including the postgresql -> postgresql+psycopg scheme
    # normalization) identically to the running app — one source of
    # truth, no drift between "how the app connects" and "how migrations
    # connect".
    return settings.database_url


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection (`alembic upgrade
    head --sql`). Not the primary path for this project (we always have
    a reachable Postgres in dev/CI) but kept for completeness/parity with
    Alembic's standard template."""
    context.configure(
        url=_get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()
    connectable = engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
