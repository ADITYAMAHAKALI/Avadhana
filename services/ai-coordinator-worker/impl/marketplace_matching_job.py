"""RQ job handler for the Marketplace's RRF rank-fusion matching engine
(GitHub issue #68). Listens on the `marketplace-matching` queue (see
`worker.py`'s `main()`), enqueued by `backend-api`'s
`POST /marketplace/rfps/{rfp_id}/matches/trigger` (see that service's
`app/services/marketplace_service.trigger_match_run` and
`app/interfaces/job_enqueuer.py` for the producer side).

CLAUDE.md "Solution Marketplace Architecture" -> "Matching engine:
multi-attribute, multi-embedding RRF fusion", all 5 steps, run here:

1. Hard-constraint filtering (`filter_hard_constraints`).
2. Per-signal scoring: attribute-match (`score_attribute_match`) plus
   cosine similarity per embedding space (`cosine_similarity`).
3. Rank each signal (`rank_signal`).
4. Fuse via weighted RRF (`fuse_rrf`).
5. Persist the ranked `SolutionMatch` rows; step 5's "surface to the
   buyer" is `backend-api`'s `GET /marketplace/rfps/{rfp_id}/matches`
   read endpoint, not this job's job.

**Why the pure computation functions below (hard-constraint filter,
attribute-match score, cosine similarity, rank, RRF fuse) are
REIMPLEMENTED here rather than imported from `services/backend-api/app/
services/marketplace_matching.py`, where the identical logic already
lives** (issue #66/#68 landed there first): this service and
`backend-api` are two independently-deployable services with no shared
Python package between them and no existing precedent in this codebase
for one service importing another's source tree (see
`impl/marketplace_db.py`'s module docstring for the identical reasoning
applied to the ORM-vs-Core question). Each of these functions is short
(~10-30 lines), has zero external dependencies of its own, and is
exhaustively unit-tested in both places — the duplication is a
deliberate, documented tradeoff (explicit "no cross-service Python
imports" boundary) rather than an oversight. If this duplication becomes
a maintenance burden as the matching logic grows more complex, the right
fix is a small vendored/published shared package for just this pure
computation layer — not a live source-tree import between two
independently-deployed services. Not needed at this scale (issue #68's
scope).

Read-side (fetching candidates, embeddings) and write-side (MatchRun/
SolutionMatch persistence) both go through `impl/marketplace_db.py`'s
SQLAlchemy Core `Table` objects via a plain `Connection` — no ORM
session, no repo-port abstraction (this job has exactly one caller,
RQ, and one execution path; the port/fake-testability pattern
`backend-api`'s service layer uses exists for a different problem, many
callers through FastAPI DI, that doesn't apply to a single RQ job
handler function).
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Connection, Engine

from db_config import resolve_database_url
from impl.marketplace_db import (
    embedding_vectors,
    match_runs,
    rfp_requirements,
    rfps,
    solution_attributes,
    solution_matches,
    solutions,
)

DEFAULT_RRF_K = 60
ATTRIBUTE_MATCH_SIGNAL = "attribute_match"

MATCH_RUN_STATUS_RUNNING = "running"
MATCH_RUN_STATUS_COMPLETED = "completed"
MATCH_RUN_STATUS_FAILED = "failed"

SOLUTION_STATUS_PUBLISHED = "published"

# Bumped when this job's scoring/fusion logic changes in a way that
# would make old MatchRun.model_versions_used comparisons meaningless —
# recorded on every run for the same "which model versions produced
# this" traceability CLAUDE.md calls out for MatchRun.
ATTRIBUTE_MATCH_LOGIC_VERSION = "v1"


# --- Pure computation (reimplemented from backend-api's
# app/services/marketplace_matching.py — see module docstring) ---------


def solution_satisfies_hard_constraints(
    solution_attribute_rows: list[dict], requirement_rows: list[dict]
) -> bool:
    hard_requirements = [r for r in requirement_rows if r["is_hard_constraint"]]
    if not hard_requirements:
        return True
    attr_pairs = {(a["attribute_key"], a["attribute_value"]) for a in solution_attribute_rows}
    return all(
        (r["attribute_key"], r["attribute_value"]) in attr_pairs for r in hard_requirements
    )


def filter_hard_constraints(
    candidates: list[tuple[dict, list[dict]]], requirement_rows: list[dict]
) -> list[tuple[dict, list[dict]]]:
    return [
        (solution, attrs)
        for solution, attrs in candidates
        if solution_satisfies_hard_constraints(attrs, requirement_rows)
    ]


def score_attribute_match(
    solution_attribute_rows: list[dict], requirement_rows: list[dict]
) -> float:
    """Same "matched weight / total requirement weight" formula as
    backend-api's `score_attribute_match` — see that function's
    docstring for the full reasoning. Returns just the score (not the
    matched-ids list) since this job only needs the numeric signal for
    RRF fusion, not the requirement-id explainability breakdown that
    #66's synchronous endpoint separately returns."""
    total_weight = sum(r["weight"] for r in requirement_rows)
    if total_weight <= 0:
        return 0.0
    attr_pairs = {(a["attribute_key"], a["attribute_value"]) for a in solution_attribute_rows}
    raw_score = sum(
        r["weight"]
        for r in requirement_rows
        if (r["attribute_key"], r["attribute_value"]) in attr_pairs
    )
    return raw_score / total_weight


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Identical contract to backend-api's `cosine_similarity` — see
    that function's docstring. Plain Python, no numpy (this service has
    no numpy dependency either; same "not worth it at this scale"
    reasoning)."""
    if len(vector_a) != len(vector_b) or not vector_a:
        return 0.0
    dot = mag_a = mag_b = 0.0
    for a, b in zip(vector_a, vector_b):
        dot += a * b
        mag_a += a * a
        mag_b += b * b
    if mag_a <= 0.0 or mag_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(mag_a) * math.sqrt(mag_b))


def most_recent_vector_by_owner_and_space(
    embedding_rows: list[dict],
) -> dict[tuple[str, str], list[float]]:
    """Identical contract to backend-api's function of the same name —
    "most-recent generated_at wins" per `EmbeddingVector`'s insert-only
    contract."""
    latest: dict[tuple[str, str], tuple] = {}
    for row in embedding_rows:
        key = (row["owner_id"], row["embedding_space"])
        current = latest.get(key)
        if current is None or row["generated_at"] > current[0]:
            latest[key] = (row["generated_at"], row["vector"])
    return {key: vector for key, (_, vector) in latest.items()}


def rank_signal(scores: dict[str, float]) -> dict[str, int]:
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return {solution_id: rank for rank, (solution_id, _) in enumerate(ordered, start=1)}


@dataclass(frozen=True)
class FusedMatchResult:
    solution_id: str
    final_rrf_score: float
    rank: int
    signal_scores: dict[str, float]
    signal_ranks: dict[str, int]


def default_signal_weights(signal_names: list[str]) -> dict[str, float]:
    """Provisional equal-weighting default — identical reasoning to
    backend-api's function of the same name (CLAUDE.md: "initial
    per-signal weights will be a guess")."""
    if not signal_names:
        return {}
    weight = 1.0 / len(signal_names)
    return {name: weight for name in signal_names}


def fuse_rrf(
    *,
    signal_scores_by_solution: dict[str, dict[str, float]],
    weights: dict[str, float] | None = None,
    k: int = DEFAULT_RRF_K,
) -> list[FusedMatchResult]:
    """Identical algorithm/contract to backend-api's `fuse_rrf` — see
    that function's docstring for the full explanation of the formula,
    missing-signal handling, and tiebreak rules."""
    all_signal_names: set[str] = set()
    for scores in signal_scores_by_solution.values():
        all_signal_names.update(scores.keys())

    resolved_weights = (
        default_signal_weights(sorted(all_signal_names)) if weights is None else weights
    )

    ranks_by_signal: dict[str, dict[str, int]] = {}
    for signal_name in all_signal_names:
        scores_for_signal = {
            solution_id: scores[signal_name]
            for solution_id, scores in signal_scores_by_solution.items()
            if signal_name in scores
        }
        ranks_by_signal[signal_name] = rank_signal(scores_for_signal)

    results: list[FusedMatchResult] = []
    for solution_id, scores in signal_scores_by_solution.items():
        signal_ranks = {
            signal_name: ranks_by_signal[signal_name][solution_id]
            for signal_name in scores
            if solution_id in ranks_by_signal[signal_name]
        }
        fused_score = sum(
            resolved_weights.get(signal_name, 0.0) * (1.0 / (k + rank))
            for signal_name, rank in signal_ranks.items()
        )
        results.append(
            FusedMatchResult(
                solution_id=solution_id,
                final_rrf_score=fused_score,
                rank=0,
                signal_scores=dict(scores),
                signal_ranks=signal_ranks,
            )
        )

    results.sort(key=lambda r: (-r.final_rrf_score, r.solution_id))
    return [
        FusedMatchResult(
            solution_id=r.solution_id,
            final_rrf_score=r.final_rrf_score,
            rank=i,
            signal_scores=r.signal_scores,
            signal_ranks=r.signal_ranks,
        )
        for i, r in enumerate(results, start=1)
    ]


# --- Data access (SQLAlchemy Core) --------------------------------------


def _fetch_rfp(conn: Connection, rfp_id: str) -> dict | None:
    row = conn.execute(select(rfps).where(rfps.c.id == rfp_id)).mappings().first()
    return dict(row) if row is not None else None


def _fetch_requirements(conn: Connection, rfp_id: str) -> list[dict]:
    rows = conn.execute(
        select(rfp_requirements).where(rfp_requirements.c.rfp_id == rfp_id)
    ).mappings()
    return [dict(r) for r in rows]


def _fetch_published_solutions_with_attributes(conn: Connection) -> list[tuple[dict, list[dict]]]:
    solution_rows = conn.execute(
        select(solutions).where(solutions.c.status == SOLUTION_STATUS_PUBLISHED)
    ).mappings()
    solution_dicts = [dict(r) for r in solution_rows]

    attr_rows = conn.execute(select(solution_attributes)).mappings()
    attrs_by_solution: dict[str, list[dict]] = {}
    for row in attr_rows:
        attrs_by_solution.setdefault(row["solution_id"], []).append(dict(row))

    return [(s, attrs_by_solution.get(s["id"], [])) for s in solution_dicts]


def _fetch_embeddings_for_owners(conn: Connection, owner_ids: list[str]) -> list[dict]:
    if not owner_ids:
        return []
    rows = conn.execute(
        select(embedding_vectors).where(embedding_vectors.c.owner_id.in_(owner_ids))
    ).mappings()
    return [dict(r) for r in rows]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Job entry point -----------------------------------------------------


def _get_engine(engine: Engine | None) -> Engine:
    if engine is not None:
        return engine
    return create_engine(resolve_database_url())


def run_matching_job(
    rfp_id: str,
    triggered_by: str,
    match_run_id: str,
    *,
    engine: Engine | None = None,
) -> None:
    """The RQ job handler. `match_run_id` is the `MatchRun` row
    `backend-api`'s trigger endpoint already created (status=pending) —
    this job transitions it to `running`, then to `completed`/`failed`
    on exit, rather than creating its own run row. This split (HTTP
    layer creates the row synchronously so the trigger response can
    return its id immediately; the job only transitions it) mirrors how
    `services/backend-api/app/services/marketplace_service.
    trigger_match_run`'s docstring frames the responsibility split.

    `engine` is an optional override for tests (an in-memory SQLite
    engine backed by `impl/marketplace_db.py`'s `metadata`) — production
    use (via `worker.py`) always calls this with `engine=None`, which
    lazily constructs a real engine from `DATABASE_URL` on first use
    inside the job (not at module import time, so `import
    impl.marketplace_matching_job` stays side-effect-free without a
    reachable database, same rule `worker.py` already follows for
    Redis/SARVAM).

    On any exception, the `MatchRun` is marked `failed` with the
    exception message recorded (`error_message`) and the exception is
    re-raised — RQ's own retry/failure-queue handling still applies;
    this job doesn't swallow errors, it just makes sure the audit row
    reflects what happened before RQ sees the failure.
    """
    resolved_engine = _get_engine(engine)
    with resolved_engine.connect() as conn:
        conn.execute(
            match_runs.update()
            .where(match_runs.c.id == match_run_id)
            .values(status=MATCH_RUN_STATUS_RUNNING)
        )
        conn.commit()

        try:
            rfp = _fetch_rfp(conn, rfp_id)
            if rfp is None:
                raise ValueError(f"RFP {rfp_id} not found.")

            requirement_rows = _fetch_requirements(conn, rfp_id)
            candidates = _fetch_published_solutions_with_attributes(conn)
            survivors = filter_hard_constraints(candidates, requirement_rows)

            owner_ids = [rfp_id] + [s["id"] for s, _ in survivors]
            embedding_rows = _fetch_embeddings_for_owners(conn, owner_ids)
            vectors_by_owner_space = most_recent_vector_by_owner_and_space(embedding_rows)

            rfp_spaces = {
                space for (owner_id, space) in vectors_by_owner_space if owner_id == rfp_id
            }

            signal_scores_by_solution: dict[str, dict[str, float]] = {}
            for solution, attrs in survivors:
                solution_id = solution["id"]
                scores: dict[str, float] = {
                    ATTRIBUTE_MATCH_SIGNAL: score_attribute_match(attrs, requirement_rows)
                }
                for space in rfp_spaces:
                    rfp_vector = vectors_by_owner_space.get((rfp_id, space))
                    solution_vector = vectors_by_owner_space.get((solution_id, space))
                    if rfp_vector is not None and solution_vector is not None:
                        scores[space] = cosine_similarity(rfp_vector, solution_vector)
                signal_scores_by_solution[solution_id] = scores

            fused_results = fuse_rrf(signal_scores_by_solution=signal_scores_by_solution)

            now = _utcnow()
            if fused_results:
                conn.execute(
                    solution_matches.insert(),
                    [
                        {
                            "id": str(uuid.uuid4()),
                            "match_run_id": match_run_id,
                            "solution_id": result.solution_id,
                            "final_rrf_score": result.final_rrf_score,
                            "rank": result.rank,
                            "signal_scores": result.signal_scores,
                            "signal_ranks": result.signal_ranks,
                            "created_at": now,
                        }
                        for result in fused_results
                    ],
                )

            conn.execute(
                match_runs.update()
                .where(match_runs.c.id == match_run_id)
                .values(
                    status=MATCH_RUN_STATUS_COMPLETED,
                    completed_at=now,
                    model_versions_used={
                        "attribute_match_version": ATTRIBUTE_MATCH_LOGIC_VERSION,
                    },
                )
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            conn.execute(
                match_runs.update()
                .where(match_runs.c.id == match_run_id)
                .values(
                    status=MATCH_RUN_STATUS_FAILED,
                    completed_at=_utcnow(),
                    error_message=str(exc)[:2000],
                )
            )
            conn.commit()
            raise
