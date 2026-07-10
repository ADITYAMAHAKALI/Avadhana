"""Tests for the Marketplace RRF matching job (GitHub issue #68,
`impl.marketplace_matching_job`).

Two layers:
1. Pure-function tests for the reimplemented scoring/ranking/fusion
   logic (hard-constraint filter, attribute-match score, cosine
   similarity, rank_signal, fuse_rrf) — plain dicts, no DB, mirroring
   `services/backend-api/tests/unit/test_marketplace_matching.py`'s
   style for the identical algorithms.
2. `run_matching_job` orchestration tests against an in-memory SQLite
   engine built from `impl/marketplace_db.py`'s `metadata` — this is the
   "fake DB layer via the same SQLAlchemy Core Table definitions" option
   the build brief calls out, chosen over a hand-rolled fake connection
   since `metadata.create_all()` against SQLite gives a real, if
   lightweight, database to exercise the actual SQL this job issues
   (inserts, updates, filters) rather than a mock that could drift from
   what real Postgres actually does.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select

from impl.marketplace_db import (
    embedding_vectors,
    match_runs,
    metadata,
    rfp_requirements,
    rfps,
    solution_attributes,
    solution_matches,
    solutions,
)
from impl.marketplace_matching_job import (
    DEFAULT_RRF_K,
    MATCH_RUN_STATUS_COMPLETED,
    MATCH_RUN_STATUS_FAILED,
    cosine_similarity,
    default_signal_weights,
    filter_hard_constraints,
    fuse_rrf,
    most_recent_vector_by_owner_and_space,
    rank_signal,
    run_matching_job,
    score_attribute_match,
    solution_satisfies_hard_constraints,
)


# --- Pure function tests -------------------------------------------------


def _requirement(key, value, weight=1.0, hard=False):
    return {"attribute_key": key, "attribute_value": value, "weight": weight, "is_hard_constraint": hard}


def _attribute(key, value):
    return {"attribute_key": key, "attribute_value": value}


def test_hard_constraint_filtering_drops_non_satisfying_candidates():
    requirements = [_requirement("certification", "ISO-27001", hard=True)]
    survivors = filter_hard_constraints(
        [
            ({"id": "s1"}, [_attribute("certification", "ISO-27001")]),
            ({"id": "s2"}, [_attribute("industry", "logistics")]),
        ],
        requirements,
    )
    assert [s["id"] for s, _ in survivors] == ["s1"]


def test_solution_satisfies_hard_constraints_true_with_no_hard_requirements():
    assert solution_satisfies_hard_constraints([], [_requirement("x", "y", hard=False)]) is True


def test_score_attribute_match_matches_backend_api_formula():
    requirements = [_requirement("industry", "logistics", weight=3.0), _requirement("region", "south", weight=1.0)]
    attrs = [_attribute("industry", "logistics")]
    assert score_attribute_match(attrs, requirements) == 0.75


def test_score_attribute_match_zero_requirements_is_zero():
    assert score_attribute_match([_attribute("x", "y")], []) == 0.0


def test_cosine_similarity_basic():
    assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_most_recent_vector_by_owner_and_space_picks_newest():
    rows = [
        {"owner_id": "s1", "embedding_space": "summary", "vector": [1.0], "generated_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        {"owner_id": "s1", "embedding_space": "summary", "vector": [2.0], "generated_at": datetime(2026, 6, 1, tzinfo=timezone.utc)},
    ]
    result = most_recent_vector_by_owner_and_space(rows)
    assert result[("s1", "summary")] == [2.0]


def test_rank_signal_orders_and_breaks_ties():
    assert rank_signal({"a": 0.9, "b": 0.9, "c": 0.1}) == {"a": 1, "b": 2, "c": 3}


def test_default_signal_weights_equal_split():
    assert default_signal_weights(["a", "b"]) == {"a": 0.5, "b": 0.5}


def test_fuse_rrf_single_signal():
    results = fuse_rrf(signal_scores_by_solution={"s1": {"attribute_match": 0.9}, "s2": {"attribute_match": 0.1}})
    by_id = {r.solution_id: r for r in results}
    k = DEFAULT_RRF_K
    assert abs(by_id["s1"].final_rrf_score - (1.0 / (k + 1))) < 1e-9
    assert by_id["s1"].rank == 1
    assert by_id["s2"].rank == 2


def test_fuse_rrf_missing_signal_handled_gracefully():
    results = fuse_rrf(
        signal_scores_by_solution={
            "s1": {"attribute_match": 0.9, "summary": 0.9},
            "s2": {"attribute_match": 0.8},
        }
    )
    by_id = {r.solution_id: r for r in results}
    assert "summary" not in by_id["s2"].signal_scores
    assert by_id["s1"].rank == 1


# --- run_matching_job orchestration tests --------------------------------


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    metadata.create_all(eng)
    yield eng
    eng.dispose()


def _insert_rfp(engine, rfp_id="rfp-1", org_id="org-buyer"):
    with engine.begin() as conn:
        conn.execute(
            rfps.insert().values(id=rfp_id, organization_id=org_id, title="RFP", description="d")
        )


def _insert_requirement(engine, rfp_id, key, value, weight=1.0, hard=False):
    with engine.begin() as conn:
        conn.execute(
            rfp_requirements.insert().values(
                id=str(uuid.uuid4()),
                rfp_id=rfp_id,
                attribute_key=key,
                attribute_value=value,
                weight=weight,
                is_hard_constraint=hard,
            )
        )


def _insert_solution(engine, solution_id, org_id="org-provider", status="published", title="Sol"):
    with engine.begin() as conn:
        conn.execute(
            solutions.insert().values(
                id=solution_id,
                organization_id=org_id,
                title=title,
                description="d",
                status=status,
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )


def _insert_solution_attribute(engine, solution_id, key, value):
    with engine.begin() as conn:
        conn.execute(
            solution_attributes.insert().values(
                id=str(uuid.uuid4()), solution_id=solution_id, attribute_key=key, attribute_value=value
            )
        )


def _insert_embedding(engine, owner_id, space, vector, generated_at=None):
    with engine.begin() as conn:
        conn.execute(
            embedding_vectors.insert().values(
                id=str(uuid.uuid4()),
                owner_type="rfp" if owner_id.startswith("rfp") else "solution",
                owner_id=owner_id,
                embedding_space=space,
                vector=vector,
                generated_at=generated_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )


def _insert_pending_match_run(engine, match_run_id, rfp_id, triggered_by="user-1"):
    with engine.begin() as conn:
        conn.execute(
            match_runs.insert().values(
                id=match_run_id,
                rfp_id=rfp_id,
                triggered_by=triggered_by,
                model_versions_used={},
                status="pending",
                started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )


def test_run_matching_job_end_to_end_attribute_only(engine):
    _insert_rfp(engine)
    _insert_requirement(engine, "rfp-1", "certification", "ISO-27001", weight=1.0, hard=True)
    _insert_requirement(engine, "rfp-1", "industry", "logistics", weight=2.0)

    _insert_solution(engine, "sol-full", title="Full Match")
    _insert_solution_attribute(engine, "sol-full", "certification", "ISO-27001")
    _insert_solution_attribute(engine, "sol-full", "industry", "logistics")

    _insert_solution(engine, "sol-partial", title="Partial Match")
    _insert_solution_attribute(engine, "sol-partial", "certification", "ISO-27001")

    _insert_solution(engine, "sol-fails-hard", title="Fails Hard Constraint")
    _insert_solution_attribute(engine, "sol-fails-hard", "industry", "logistics")

    _insert_solution(engine, "sol-draft", status="draft", title="Draft")
    _insert_solution_attribute(engine, "sol-draft", "certification", "ISO-27001")
    _insert_solution_attribute(engine, "sol-draft", "industry", "logistics")

    _insert_pending_match_run(engine, "run-1", "rfp-1")

    run_matching_job("rfp-1", "user-1", "run-1", engine=engine)

    with engine.connect() as conn:
        run_row = conn.execute(select(match_runs).where(match_runs.c.id == "run-1")).mappings().first()
        assert run_row["status"] == MATCH_RUN_STATUS_COMPLETED
        assert run_row["completed_at"] is not None
        assert run_row["model_versions_used"]["attribute_match_version"] == "v1"

        match_rows = list(
            conn.execute(
                select(solution_matches)
                .where(solution_matches.c.match_run_id == "run-1")
                .order_by(solution_matches.c.rank)
            ).mappings()
        )

    solution_ids = [r["solution_id"] for r in match_rows]
    # Draft and hard-constraint-failing solutions never appear.
    assert "sol-draft" not in solution_ids
    assert "sol-fails-hard" not in solution_ids
    assert solution_ids == ["sol-full", "sol-partial"]
    assert match_rows[0]["rank"] == 1
    assert match_rows[0]["signal_scores"]["attribute_match"] == 1.0
    assert match_rows[1]["signal_scores"]["attribute_match"] == pytest.approx(1.0 / 3.0)


def test_run_matching_job_combines_attribute_and_embedding_signals(engine):
    _insert_rfp(engine)
    _insert_requirement(engine, "rfp-1", "industry", "logistics", weight=1.0)

    _insert_solution(engine, "sol-a", title="A")
    _insert_solution_attribute(engine, "sol-a", "industry", "logistics")
    _insert_solution(engine, "sol-b", title="B")
    # sol-b has no attribute match at all, but a strong embedding match.

    _insert_embedding(engine, "rfp-1", "summary", [1.0, 0.0])
    _insert_embedding(engine, "sol-a", "summary", [0.0, 1.0])  # orthogonal -> 0 similarity
    _insert_embedding(engine, "sol-b", "summary", [1.0, 0.0])  # identical -> 1.0 similarity

    _insert_pending_match_run(engine, "run-2", "rfp-1")
    run_matching_job("rfp-1", "user-1", "run-2", engine=engine)

    with engine.connect() as conn:
        match_rows = list(
            conn.execute(
                select(solution_matches)
                .where(solution_matches.c.match_run_id == "run-2")
                .order_by(solution_matches.c.rank)
            ).mappings()
        )

    by_id = {r["solution_id"]: r for r in match_rows}
    assert by_id["sol-a"]["signal_scores"]["attribute_match"] == 1.0
    assert by_id["sol-a"]["signal_scores"]["summary"] == pytest.approx(0.0, abs=1e-9)
    assert by_id["sol-b"]["signal_scores"]["attribute_match"] == 0.0
    assert by_id["sol-b"]["signal_scores"]["summary"] == pytest.approx(1.0)


def test_run_matching_job_solution_with_zero_embeddings_still_ranks_on_attribute_match(engine):
    _insert_rfp(engine)
    _insert_requirement(engine, "rfp-1", "industry", "logistics", weight=1.0)

    _insert_solution(engine, "sol-no-embedding", title="No Embedding")
    _insert_solution_attribute(engine, "sol-no-embedding", "industry", "logistics")

    _insert_solution(engine, "sol-with-embedding", title="With Embedding")
    _insert_solution_attribute(engine, "sol-with-embedding", "industry", "logistics")
    _insert_embedding(engine, "rfp-1", "summary", [1.0, 0.0])
    _insert_embedding(engine, "sol-with-embedding", "summary", [1.0, 0.0])

    _insert_pending_match_run(engine, "run-3", "rfp-1")
    run_matching_job("rfp-1", "user-1", "run-3", engine=engine)

    with engine.connect() as conn:
        match_rows = list(
            conn.execute(
                select(solution_matches).where(solution_matches.c.match_run_id == "run-3")
            ).mappings()
        )

    by_id = {r["solution_id"]: r for r in match_rows}
    assert "summary" not in by_id["sol-no-embedding"]["signal_scores"]
    assert by_id["sol-with-embedding"]["signal_scores"]["summary"] == pytest.approx(1.0)
    # The no-embedding solution must still be present, ranked purely on
    # attribute_match — not dropped or errored on.
    assert set(by_id.keys()) == {"sol-no-embedding", "sol-with-embedding"}


def test_run_matching_job_no_candidates_completes_with_empty_matches(engine):
    _insert_rfp(engine)
    _insert_requirement(engine, "rfp-1", "industry", "logistics", weight=1.0)
    _insert_pending_match_run(engine, "run-4", "rfp-1")

    run_matching_job("rfp-1", "user-1", "run-4", engine=engine)

    with engine.connect() as conn:
        run_row = conn.execute(select(match_runs).where(match_runs.c.id == "run-4")).mappings().first()
        assert run_row["status"] == MATCH_RUN_STATUS_COMPLETED
        match_rows = list(
            conn.execute(
                select(solution_matches).where(solution_matches.c.match_run_id == "run-4")
            ).mappings()
        )
    assert match_rows == []


def test_run_matching_job_missing_rfp_marks_run_failed_and_reraises(engine):
    _insert_pending_match_run(engine, "run-5", "rfp-does-not-exist")

    with pytest.raises(ValueError, match="not found"):
        run_matching_job("rfp-does-not-exist", "user-1", "run-5", engine=engine)

    with engine.connect() as conn:
        run_row = conn.execute(select(match_runs).where(match_runs.c.id == "run-5")).mappings().first()
    assert run_row["status"] == MATCH_RUN_STATUS_FAILED
    assert run_row["error_message"] is not None
    assert "not found" in run_row["error_message"]
    assert run_row["completed_at"] is not None


def test_run_matching_job_uses_most_recent_embedding_per_owner_and_space(engine):
    _insert_rfp(engine)
    _insert_requirement(engine, "rfp-1", "industry", "logistics", weight=1.0)
    _insert_solution(engine, "sol-a", title="A")
    _insert_solution_attribute(engine, "sol-a", "industry", "logistics")

    _insert_embedding(engine, "rfp-1", "summary", [1.0, 0.0], generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    # Old, stale embedding for sol-a: orthogonal (would score 0).
    _insert_embedding(engine, "sol-a", "summary", [0.0, 1.0], generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    # Newer embedding: identical to the RFP's (should win, score 1.0).
    _insert_embedding(engine, "sol-a", "summary", [1.0, 0.0], generated_at=datetime(2026, 6, 1, tzinfo=timezone.utc))

    _insert_pending_match_run(engine, "run-6", "rfp-1")
    run_matching_job("rfp-1", "user-1", "run-6", engine=engine)

    with engine.connect() as conn:
        match_row = conn.execute(
            select(solution_matches).where(solution_matches.c.match_run_id == "run-6")
        ).mappings().first()

    assert match_row["signal_scores"]["summary"] == pytest.approx(1.0)
