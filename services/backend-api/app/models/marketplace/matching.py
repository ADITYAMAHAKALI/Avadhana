"""MatchRun + SolutionMatch ORM models (GitHub issue #68, "Matching
engine: rank fusion (RRF)"). See CLAUDE.md "Solution Marketplace
Architecture" -> "Matching engine: multi-attribute, multi-embedding RRF
fusion" and -> "Domain model" (`MatchRun`, `SolutionMatch`).

`MatchRun` — one row per matching computation for an RFP. **This is the
one deliberate exception to this codebase's "insert-only" rule for
Marketplace/audit-style tables** (`CommitmentCheckpoint`,
`ModerationOverrideEvent`, `EmbeddingVector`, `BillingEvent` are all
strictly insert-only — see those modules' docstrings): a `MatchRun` row
IS mutated in place as its own lifecycle progresses
(`pending -> running -> completed|failed`, with `completed_at` filled in
once it leaves the running state). That's necessary because a single
matching computation is a single logical unit of work with a real
before/during/after — same shape as any other long-running-job status
row. What stays immutable is the *set of MatchRun rows*: nothing here
ever UPDATEs `rfp_id`/`triggered_by`/`started_at`/`model_versions_used`
after creation, no row is ever deleted, and a re-run (re-publish, manual
re-trigger) always INSERTs a brand new `MatchRun` row rather than
resetting an old one back to `pending`. So the audit trail itself (every
run that ever happened, and what it was) is exactly as immutable as
every other table in this codebase — only a single row's own terminal
status fields transition once, from pending to a final state, while it's
in flight.

`SolutionMatch` — the ranked output of a completed `MatchRun`. Strictly
insert-only like the rest: written once, in one batch, when the owning
run completes; never updated or deleted. A later re-run producing a
different ranking creates an entirely new `MatchRun` + its own new
`SolutionMatch` rows, leaving the prior run's rows untouched — this is
what makes historical match explanations reproducible (CLAUDE.md
`EmbeddingVector` docstring makes the same "reproducible after content
changes" argument; `SolutionMatch` inherits it one level up).

`signal_scores`/`signal_ranks` are JSON breakdowns keyed by signal name
(e.g. `"attribute_match"`, `"summary"`, `"technical_spec"` — the
embedding-space names double as signal names for the embedding
component of the fusion) so a buyer can see *why* a match happened per
CLAUDE.md's explainability note — mirrors the "why did this match"
transparency goal already served by `AttributeMatchResult.
matched_requirement_ids` in `app/services/marketplace_matching.py`
(issue #66), just carried through to the fused, persisted result.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.time import utcnow
from app.db.base import Base


class MatchRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rfp_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfps.id"), nullable=False, index=True
    )

    # User id, or the literal string "system" for scheduled/automatic
    # triggers (e.g. auto-run on RFP publish/re-publish) that have no
    # human caller — mirrors AIInvocation's "triggered_by" shape
    # (CLAUDE.md "Domain model": "MatchRun: ... (triggered_by, ...) —
    # immutable audit trail, same pattern as AIInvocation").
    triggered_by: Mapped[str] = mapped_column(String(36), nullable=False)

    # Which embedding model/version and attribute-scoring logic version
    # ran, e.g. {"embeddings_model": "text-embedding-3-small",
    # "attribute_match_version": "v1"} — lets a later calibration pass
    # correlate match quality with which model versions produced it.
    model_versions_used: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MatchRunStatus.PENDING.value
    )

    # Failure detail when status == "failed" — the exception message,
    # not a full traceback (avoid leaking internals into what may
    # eventually be buyer-visible audit data).
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    # Nullable until the run leaves "running" (completed or failed) —
    # see module docstring on why this row is the one mutable exception.
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolutionMatch(Base):
    __tablename__ = "solution_matches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    match_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("match_runs.id"), nullable=False, index=True
    )
    solution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("solutions.id"), nullable=False, index=True
    )

    final_rrf_score: Mapped[float] = mapped_column(Float, nullable=False)
    # 1-indexed position within this MatchRun's results, best match first.
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    # Per-signal breakdown, e.g. {"attribute_match": 0.73, "summary": 0.61}
    # and {"attribute_match": 1, "summary": 3} respectively — see
    # app/services/marketplace_matching.py's `fuse_rrf` for how these are
    # computed. A signal absent from a dict means that Solution didn't
    # participate in that signal (e.g. no embedding for that space).
    signal_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    signal_ranks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
