"""Environment-driven configuration.

Values come from process environment variables only — never hardcoded
connection strings or secrets in source. Locally these env vars are
populated by k8s Secrets/ConfigMaps sourced from an uncommitted `.env`
(see repo-root `.env.example` and CLAUDE.md "Local Development
Environment" / "Security & Solo-Dev Architecture"). In CI, tests override
`DATABASE_URL` directly (see tests/integration/conftest.py) so no live
Postgres is required.
"""

import os


class Settings:
    """Thin wrapper over os.environ — no external config library needed
    for the handful of values this service currently reads. Re-reads
    lazily via properties rather than caching at import time, which
    matters for tests that monkeypatch `os.environ` before constructing
    a fresh `Settings()`.
    """

    @property
    def database_url(self) -> str:
        # No default: a missing DATABASE_URL should fail loudly at
        # startup, not silently fall back to some local sqlite file that
        # masks a misconfigured deployment.
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. See .env.example at the repo root."
            )
        # .env.example (and the k8s Secret sourced from it) uses the
        # plain `postgresql://` scheme, which SQLAlchemy defaults to the
        # psycopg2 dialect. This service standardizes on psycopg (v3)
        # instead (see pyproject.toml), so normalize the scheme here
        # rather than requiring every environment to know about the
        # `+psycopg` suffix.
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def jwt_secret(self) -> str:
        secret = os.environ.get("JWT_SECRET")
        if not secret:
            raise RuntimeError(
                "JWT_SECRET is not set. See .env.example at the repo root."
            )
        return secret

    @property
    def jwt_algorithm(self) -> str:
        return "HS256"

    @property
    def jwt_expires_minutes(self) -> int:
        # Long enough to not force re-login constantly during dev/beta;
        # short enough to bound the blast radius of a leaked token.
        # Revisit alongside CLAUDE.md's "rotated on privilege change" note
        # (issue #8 / Security epic) once refresh tokens exist.
        return 60 * 24 * 7  # 7 days


settings = Settings()
