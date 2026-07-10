"""Resolve this service's database connection.

Mirrors `sarvam_config.py`'s "kept separate from worker.py so this is
independently testable without touching env vars or constructing a real
engine" reasoning, applied to the Marketplace matching job's DB
dependency (issue #68) — this service's first-ever DB connection (see
`impl/marketplace_db.py` module docstring for the full "why Core, not
ORM" story).

`infra/k8s/ai-coordinator-worker/configmap.yaml` and
`docker-compose.prod.yml` already wire a `DATABASE_URL` env var into
this service's deployment config (previously unused) — so this reads
the exact same var `backend-api`'s `app.core.config.Settings.
database_url` does, including the same `postgresql://` ->
`postgresql+psycopg://` scheme normalization (this service also
standardizes on psycopg v3, matching backend-api's pyproject.toml pin),
for one source of truth on how either service connects to the same
Postgres instance.
"""

from __future__ import annotations

import os


def resolve_database_url(env: dict[str, str] | None = None) -> str:
    """Raises `ValueError` if `DATABASE_URL` is unset — a missing DB URL
    should fail loudly when the matching job actually runs, not silently
    fall back to some default that masks a misconfigured deployment
    (same reasoning as backend-api's `Settings.database_url`)."""
    source = env if env is not None else os.environ
    url = source.get("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL is not set. See .env.example at the repo root."
        )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url
