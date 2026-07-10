"""SQLAlchemy Core table definitions for the handful of Marketplace
tables the RRF matching job (GitHub issue #68) needs to read from and
write to.

**Why Core, not the ORM classes from `services/backend-api/app/models/
marketplace/*.py`**: this service and `backend-api` are two
independently-deployable services (see CLAUDE.md "Service boundaries
(solo-dev pragmatism)") with no shared Python package between them —
there is no existing precedent anywhere in this codebase for one service
importing another service's source tree, and doing so here would create
a hard coupling that breaks the "can be extracted/deployed independently"
promise CLAUDE.md makes for both Moderation and the Marketplace. Copying
`backend-api`'s full declarative ORM model classes into this service
instead would avoid the coupling but create a *drift* risk: two
independently-maintained copies of the same table definitions that have
to be kept in sync by hand on every schema change, with nothing enforcing
that they actually stay in sync.

SQLAlchemy Core (`sqlalchemy.Table` with explicit columns, executed via
plain `Connection.execute()`) is the middle path: it needs the same
column names/types kept in sync as a full ORM copy would, but it's a
fraction of the code (a `Table(...)` call per table vs. a full
declarative class with relationships, defaults, and mapper events), and
nothing here pretends to be a general-purpose data-access layer for this
service — it's five read queries and two inserts, scoped tightly to what
`impl/marketplace_matching_job.py` actually needs. If this job's DB
footprint grows significantly, revisit whether a shared internal package
(published/vendored, not a live source-tree import) is worth the
overhead; not needed at this scale.

Column definitions here are intentionally a SUBSET of each real table's
full schema (see `services/backend-api/app/models/marketplace/*.py` for
the authoritative definitions) — only the columns this job actually
reads or writes. `metadata` is never used to `create_all()` against a
real deployment; migrations remain solely `backend-api`'s
responsibility (CLAUDE.md: "schema authority stays in
services/backend-api"). Tests in this service use
`metadata.create_all()` against an in-memory SQLite engine purely as a
lightweight fake DB — see `tests/test_marketplace_matching_job.py`.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
)
from sqlalchemy.types import JSON

metadata = MetaData()

rfps = Table(
    "rfps",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("organization_id", String(36), nullable=False),
    Column("title", String(300), nullable=False),
    Column("description", String(5000), nullable=False),
)

rfp_requirements = Table(
    "rfp_requirements",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("rfp_id", String(36), ForeignKey("rfps.id"), nullable=False),
    Column("attribute_key", String(200), nullable=False),
    Column("attribute_value", String(1000), nullable=False),
    Column("weight", Float, nullable=False),
    Column("is_hard_constraint", Boolean, nullable=False),
)

solutions = Table(
    "solutions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("organization_id", String(36), nullable=False),
    Column("title", String(300), nullable=False),
    Column("description", String(5000), nullable=False),
    Column("status", String(20), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

solution_attributes = Table(
    "solution_attributes",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("solution_id", String(36), ForeignKey("solutions.id"), nullable=False),
    Column("attribute_key", String(200), nullable=False),
    Column("attribute_value", String(1000), nullable=False),
)

# `vector` deliberately omitted — this job only needs `owner_id`/
# `embedding_space`/`generated_at` to pick the most-recent row per
# owner+space, and the raw vector for cosine similarity. Stored as JSON
# here (not pgvector's native type) since this job never needs a
# database-side vector index or distance operator — it fetches the raw
# floats and computes cosine similarity in Python (see
# app/services/marketplace_matching.py's `cosine_similarity` in
# backend-api, reimplemented here — see that module's own docstring on
# why reimplementing the small pure function is preferred over a
# cross-service import). On real Postgres, `pgvector`'s column still
# round-trips as a plain Python list through psycopg, so JSON-typing it
# here for read purposes works against both SQLite (tests) and Postgres
# (prod) identically.
embedding_vectors = Table(
    "embedding_vectors",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("owner_type", String(20), nullable=False),
    Column("owner_id", String(36), nullable=False),
    Column("embedding_space", String(100), nullable=False),
    Column("vector", JSON, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
)

match_runs = Table(
    "match_runs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("rfp_id", String(36), ForeignKey("rfps.id"), nullable=False),
    Column("triggered_by", String(36), nullable=False),
    Column("model_versions_used", JSON, nullable=False),
    Column("status", String(20), nullable=False),
    Column("error_message", String(2000), nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
)

solution_matches = Table(
    "solution_matches",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("match_run_id", String(36), ForeignKey("match_runs.id"), nullable=False),
    Column("solution_id", String(36), ForeignKey("solutions.id"), nullable=False),
    Column("final_rrf_score", Float, nullable=False),
    Column("rank", Integer, nullable=False),
    Column("signal_scores", JSON, nullable=False),
    Column("signal_ranks", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
