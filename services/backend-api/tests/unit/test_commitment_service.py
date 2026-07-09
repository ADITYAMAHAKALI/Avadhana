"""Unit tests for the 3-slot system (app.services.commitment_service).

Per CLAUDE.md constraint #1: "a user can have at most 3 ACTIVE
commitments. A 4th attempt must be hard-blocked with a clear error
(409), not a soft warning." These tests exercise the service function
directly against in-memory fakes — no HTTP layer, no database.
"""

import pytest

from app.models.problem import Problem
from app.services.commitment_service import MAX_ACTIVE_COMMITMENTS, create_commitment
from app.services.errors import AlreadyCommittedError, ProblemNotFoundError, SlotLimitExceededError
from tests.unit.fakes import FakeCheckpointRepo, FakeCommitmentRepo, FakeProblemRepo


def _make_problem_repo(n: int) -> tuple[FakeProblemRepo, list[str]]:
    repo = FakeProblemRepo()
    ids = []
    for i in range(n):
        p = Problem(title=f"Problem {i}", summary="s", location="l", category="c", tier="D", created_by_user_id="creator")
        repo.add(p)
        ids.append(p.id)
    return repo, ids


def test_exactly_three_active_commitments_are_allowed():
    problem_repo, problem_ids = _make_problem_repo(3)
    commitment_repo = FakeCommitmentRepo()
    checkpoint_repo = FakeCheckpointRepo()

    for pid in problem_ids:
        commitment = create_commitment(
            user_id="user-1",
            problem_id=pid,
            role="thinker",
            specialization=None,
            problem_repo=problem_repo,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
        )
        assert commitment.status == "active"

    assert commitment_repo.count_active_for_user("user-1") == MAX_ACTIVE_COMMITMENTS


def test_fourth_active_commitment_is_hard_blocked_with_409_style_error():
    problem_repo, problem_ids = _make_problem_repo(4)
    commitment_repo = FakeCommitmentRepo()
    checkpoint_repo = FakeCheckpointRepo()

    for pid in problem_ids[:3]:
        create_commitment(
            user_id="user-1",
            problem_id=pid,
            role="thinker",
            specialization=None,
            problem_repo=problem_repo,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
        )

    with pytest.raises(SlotLimitExceededError) as exc_info:
        create_commitment(
            user_id="user-1",
            problem_id=problem_ids[3],
            role="thinker",
            specialization=None,
            problem_repo=problem_repo,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
        )

    # Error carries clear, explicit counts — not a soft nudge.
    assert exc_info.value.used == 3
    assert exc_info.value.total == 3
    # No 4th commitment was actually created.
    assert commitment_repo.count_active_for_user("user-1") == 3


def test_creation_writes_immutable_created_checkpoint():
    problem_repo, problem_ids = _make_problem_repo(1)
    commitment_repo = FakeCommitmentRepo()
    checkpoint_repo = FakeCheckpointRepo()

    commitment = create_commitment(
        user_id="user-1",
        problem_id=problem_ids[0],
        role="backer",
        specialization=None,
        problem_repo=problem_repo,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
    )

    checkpoints = checkpoint_repo.list_for_commitment(commitment.id)
    assert len(checkpoints) == 1
    assert checkpoints[0].event_type == "created"


def test_cannot_double_commit_to_the_same_problem():
    problem_repo, problem_ids = _make_problem_repo(1)
    commitment_repo = FakeCommitmentRepo()
    checkpoint_repo = FakeCheckpointRepo()

    create_commitment(
        user_id="user-1",
        problem_id=problem_ids[0],
        role="thinker",
        specialization=None,
        problem_repo=problem_repo,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
    )

    with pytest.raises(AlreadyCommittedError):
        create_commitment(
            user_id="user-1",
            problem_id=problem_ids[0],
            role="actor",
            specialization="Legal",
            problem_repo=problem_repo,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
        )


def test_commit_to_nonexistent_problem_raises_not_found():
    problem_repo = FakeProblemRepo()
    commitment_repo = FakeCommitmentRepo()
    checkpoint_repo = FakeCheckpointRepo()

    with pytest.raises(ProblemNotFoundError):
        create_commitment(
            user_id="user-1",
            problem_id="does-not-exist",
            role="thinker",
            specialization=None,
            problem_repo=problem_repo,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
        )


def test_slot_limit_is_per_user_not_global():
    problem_repo, problem_ids = _make_problem_repo(4)
    commitment_repo = FakeCommitmentRepo()
    checkpoint_repo = FakeCheckpointRepo()

    for pid in problem_ids[:3]:
        create_commitment(
            user_id="user-1",
            problem_id=pid,
            role="thinker",
            specialization=None,
            problem_repo=problem_repo,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
        )

    # A different user is unaffected by user-1's slot usage.
    commitment = create_commitment(
        user_id="user-2",
        problem_id=problem_ids[3],
        role="thinker",
        specialization=None,
        problem_repo=problem_repo,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
    )
    assert commitment.status == "active"
