# Backend API

Avadhana's core Backend API service (FastAPI, Python 3.12, SQLAlchemy
2.0 + Alembic on Postgres via psycopg v3). Implements the SLC v1
commitment/problem/feed API: auth, focus slots, the 3-slot system, the
90-day commitment lock, commitment-gated voice, and a minimal
problem-specific feed (posts/comments/likes). See `/CLAUDE.md` at the
repo root for the product philosophy behind these constraints — they are
enforced in `app/services/commitment_service.py`,
`app/services/checkpoint_service.py`, and
`app/services/commitment_gate.py` respectively, and covered by the test
suite (see "Tests" below).

Out of scope for SLC v1 (deferred, see `/TODO.md`): tier reclassification,
problem split/merge/hierarchy beyond a hardcoded-null
`parentProblemTitle`, polls, task board, asset uploads, donations,
badges, AI coordination/SARVAM integration, moderation/off-topic
detection.

## Build

```
podman build -t avadhana/backend-api -f services/backend-api/Containerfile services/backend-api
```

## Run locally

```
podman run --rm -p 8000:8000 --env-file .env avadhana/backend-api
curl localhost:8000/healthz
```

Or without a container, from this directory:

```
pip install -e ".[dev]"
export DATABASE_URL=postgresql://avadhana:changeme@localhost:5432/avadhana  # or your local Postgres
export JWT_SECRET=changeme  # match whatever is in your .env
alembic upgrade head
uvicorn app.main:app --reload
```

`DATABASE_URL` and `JWT_SECRET` are required — the app raises at startup
if either is missing (see `app/core/config.py`). Locally these come from
the k8s Secret sourced from the repo-root `.env` (see
`infra/k8s/scripts/create-secrets.sh`); when running outside the cluster
(e.g. `uvicorn --reload` against a port-forwarded or locally-installed
Postgres), export them directly as shown above.

## Database & migrations

Schema lives in `app/models/` (SQLAlchemy 2.0 declarative models);
migrations live in `migrations/versions/` (Alembic). `migrations/env.py`
reads `DATABASE_URL` from the environment — never hardcode a connection
string in `alembic.ini`.

Set up a fresh database:

```
export DATABASE_URL=postgresql://avadhana:changeme@localhost:5432/avadhana
alembic upgrade head
```

After changing a model, generate a new migration and review it before
committing (autogenerate is a starting point, not gospel):

```
alembic revision --autogenerate -m "describe the change"
```

New models must be imported in `app/models/__init__.py` or Alembic's
autogenerate won't see their tables (see that file's docstring).

## Tests

```
pip install -e ".[dev]"
pytest -q
```

No live Postgres required: `DATABASE_URL`/`JWT_SECRET` just need to be
set to *something* (Settings raises if unset, but nothing actually
connects during the unit suite) — CI sets them to placeholder values,
see `.github/workflows/ci.yaml`.

- `tests/unit/` — business logic (slot limits, 90-day lock, checkpoint
  transitions, commitment-gated repo lookups, presentation helpers)
  tested against in-memory fakes (`tests/unit/fakes.py`) implementing
  the `Protocol` ports in `app/interfaces/repositories.py`. No database,
  no HTTP — these run in milliseconds.
- `tests/integration/` — the real SQLAlchemy models and the full FastAPI
  app, exercised via `TestClient` against an in-memory SQLite engine
  (see `tests/integration/conftest.py`). Proves the ORM layer and the
  routers/dependency-injection wiring work end-to-end without requiring
  a live Postgres anywhere (CI has no Postgres service container).

## Architecture / dependency injection convention

This service follows an interface/impl/service layering — apply it to
every future endpoint:

- `app/interfaces/` — abstract ports, defined as `typing.Protocol`
  (structural typing, PEP 544) rather than `abc.ABC` (no inheritance
  boilerplate, implementations stay decoupled). `health.py`/
  `service_info.py` are one-per-file (original convention); the six
  repository ports live together in `repositories.py` since they're
  small, numerous, and used together constantly by the service layer
  (see that file's docstring for the full rationale).
- `app/impl/` — concrete SQLAlchemy-backed implementations of the repo
  ports (`repositories.py`), plus the original `health.py`/
  `service_info.py`. Never imported directly into route handler bodies.
- `app/services/` — business logic (3-slot enforcement, 90-day lock,
  commitment-gated-voice, reputation deltas, presentation/derived-field
  computation). Takes repo *ports* as parameters, never concrete
  SQLAlchemy classes or a `Session` — this is what makes
  `commitment_service.py`/`checkpoint_service.py`/etc. unit-testable
  against the in-memory fakes in `tests/unit/fakes.py` with zero
  database involved.
- `app/routers/` — FastAPI routers grouped by resource (`auth.py`,
  `users.py`, `problems.py`, `commitments.py`, `feed.py`). Thin: resolve
  request-scoped dependencies (session, current user), call into
  `app/services/`, translate domain exceptions (`app/services/errors.py`)
  into the exact HTTP status/body the API contract specifies. No
  business rules here.
- `app/main.py` is the **composition root**: constructs the `FastAPI`
  app and calls `include_router(...)` for each resource router. The
  original health/service-info provider-function wiring stays inline
  here since it's tiny.
- `app/core/` — cross-cutting utilities with no business rules of their
  own: `config.py` (env-driven settings), `security.py` (bcrypt + JWT),
  `auth_dependencies.py` (`get_current_user`), `time.py`/
  `presentation.py` (initials/avatarColor/timeAgo helpers).

When adding a real endpoint, define its repo port in
`interfaces/repositories.py` (or a new file if it doesn't fit there),
implement it in `impl/`, write the business rule as a plain function in
`app/services/` that takes the port as a parameter, and wire the router
to call that function — don't write business logic straight into the
route handler, and don't let a router import SQLAlchemy models directly
for anything beyond passing them through to a presenter.

### Commitment-gated authorization (issue #8)

`app/services/commitment_gate.py`'s `require_committed_member` is the
single reusable FastAPI dependency for "only committed members can do
this" (CLAUDE.md's commitment-gated-voice constraint). It's used on
every write endpoint in `app/routers/feed.py` (posts, comments, likes)
and is designed to be trivially reusable by future feed/task/poll
endpoints — depend on it the same way, no new gating logic needed.
