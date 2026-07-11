"""Unit tests for the aggregate problem-resolution status computation
(app.services.problem_lifecycle_service), against fake in-memory repos —
no DB involved, same convention as test_checkpoint_service.py.

Covers the exact scenarios called out in the issue #100 task brief:
  - below-threshold (still open)
  - exactly-threshold with no objection (resolved)
  - exactly-threshold with an objection inside the window (disputed)
  - objection arriving after the window closed (no effect, still resolved)
  - a problem with only 1 committed member total (threshold unreachable
    — see problem_lifecycle_service's module docstring for the exact
    ">= 2, or majority, whichever is smaller" interpretation)
"""

from datetime import timedelta

from app.core.time import utcnow
from app.models.checkpoint import CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus
from app.models.problem import Problem
from app.models.resolution_objection import ResolutionObjection
from app.services.errors import AlreadyObjectedError, NoActiveResolutionWindowError, NotCommittedError
from app.services.problem_lifecycle_service import (
    OBJECTION_WINDOW,
    compute_resolution_status,
    raise_objection,
)
from tests.unit.fakes import FakeCheckpointRepo, FakeCommitmentRepo, FakeResolutionObjectionRepo

import pytest


def _problem() -> Problem:
    return Problem(
        title="Test problem",
        summary="Summary",
        location="Pune",
        category="civic",
        tier="C",
        created_by_user_id="creator-1",
    )


def _commitment(
    *, user_id: str, problem_id: str, status: str = CommitmentStatus.ACTIVE.value
) -> Commitment:
    return Commitment(
        user_id=user_id,
        problem_id=problem_id,
        role="thinker",
        specialization=None,
        status=status,
    )


def _seed(members_with_events: list[tuple[Commitment, list[tuple[str, object]]]]):
    """Wires a FakeCommitmentRepo/FakeCheckpointRepo/FakeResolutionObjectionRepo
    from (commitment, [(event_type, occurred_at), ...]) pairs. Always
    prepends a 'created' event (mirrors real checkpoint history) before
    the given events, deliberately far enough in the past that it never
    outraces an explicit `occurred_at` passed for a later event —
    `CommitmentCheckpoint`'s default `occurred_at=utcnow()` fires at
    object-construction wall-clock time, which could otherwise land
    AFTER an explicit past timestamp given to a subsequent event and
    corrupt "most recent checkpoint" ordering."""
    commitment_repo = FakeCommitmentRepo()
    checkpoint_repo = FakeCheckpointRepo()
    objection_repo = FakeResolutionObjectionRepo()

    for commitment, events in members_with_events:
        commitment_repo.add(commitment)
        checkpoint_repo.add(
            CommitmentCheckpoint(
                commitment_id=commitment.id,
                event_type="created",
                occurred_at=utcnow() - timedelta(days=365),
            )
        )
        for event_type, occurred_at in events:
            checkpoint_repo.add(
                CommitmentCheckpoint(
                    commitment_id=commitment.id,
                    event_type=event_type,
                    occurred_at=occurred_at,
                )
            )

    return commitment_repo, checkpoint_repo, objection_repo


def test_below_threshold_stays_open():
    """3 committed members (threshold = 2), only 1 has resolved: open."""
    problem = _problem()
    now = utcnow()
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m2 = _commitment(user_id="u2", problem_id=problem.id)
    m3 = _commitment(user_id="u3", problem_id=problem.id)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", now)]),
            (m2, []),
            (m3, []),
        ]
    )

    result = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
        now=now,
    )
    assert result.status == "open"
    assert result.resolved_count == 1
    assert result.total_committed == 3
    assert result.threshold == 2


def test_exactly_threshold_no_objection_resolves():
    """2 committed members, both resolved, window elapsed, no objection: resolved."""
    problem = _problem()
    now = utcnow()
    claim_time = now - OBJECTION_WINDOW - timedelta(hours=1)
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m2 = _commitment(user_id="u2", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", claim_time)]),
            (m2, [("resolved", claim_time + timedelta(minutes=5))]),
        ]
    )

    result = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
        now=now,
    )
    assert result.status == "resolved"
    assert result.resolved_count == 2
    assert result.threshold == 2
    assert result.objection_count == 0


def test_exactly_threshold_still_within_window_is_pending():
    """Threshold met but the 7-day window hasn't elapsed yet: pending_resolution, not resolved."""
    problem = _problem()
    now = utcnow()
    claim_time = now - timedelta(days=1)
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m2 = _commitment(user_id="u2", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", claim_time)]),
            (m2, [("resolved", claim_time)]),
        ]
    )

    result = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
        now=now,
    )
    assert result.status == "pending_resolution"


def test_objection_inside_window_disputes():
    problem = _problem()
    now = utcnow()
    claim_time = now - timedelta(days=1)
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m2 = _commitment(user_id="u2", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m3 = _commitment(user_id="u3", problem_id=problem.id)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", claim_time)]),
            (m2, [("resolved", claim_time)]),
            (m3, []),
        ]
    )
    objection_repo.add(
        ResolutionObjection(
            problem_id=problem.id,
            objecting_user_id="u3",
            raised_at=claim_time + timedelta(hours=2),
        )
    )

    result = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
        now=now,
    )
    assert result.status == "disputed"
    assert result.objection_count == 1


def test_objection_after_window_closed_has_no_effect_still_resolves():
    problem = _problem()
    now = utcnow()
    claim_time = now - OBJECTION_WINDOW - timedelta(days=1)
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m2 = _commitment(user_id="u2", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m3 = _commitment(user_id="u3", problem_id=problem.id)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", claim_time)]),
            (m2, [("resolved", claim_time)]),
            (m3, []),
        ]
    )
    # Objection raised AFTER window_start + 7 days — outside the window.
    late_objection_time = claim_time + OBJECTION_WINDOW + timedelta(days=1)
    objection_repo.add(
        ResolutionObjection(
            problem_id=problem.id,
            objecting_user_id="u3",
            raised_at=late_objection_time,
        )
    )

    result = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
        now=now,
    )
    assert result.status == "resolved"
    assert result.objection_count == 0


def test_lone_committed_member_cannot_self_resolve():
    """1 committed member total: threshold is unreachable (None) — a
    lone claim is never sufficient corroboration, per the documented
    ">= 2 is a hard floor" decision in problem_lifecycle_service."""
    problem = _problem()
    now = utcnow()
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", now)]),
        ]
    )

    result = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
        now=now,
    )
    assert result.status == "open"
    assert result.threshold is None
    assert result.resolved_count == 1
    assert result.total_committed == 1


def test_abandoned_members_excluded_from_denominator_and_claims():
    """An abandoned member doesn't count toward total_committed even if
    their last real event before abandoning was irrelevant; also
    verifies threshold scales with the non-abandoned population only."""
    problem = _problem()
    now = utcnow()
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m2 = _commitment(user_id="u2", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m3 = _commitment(user_id="u3", problem_id=problem.id, status=CommitmentStatus.ABANDONED.value)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", now - timedelta(days=1))]),
            (m2, [("resolved", now - timedelta(days=1))]),
            (m3, [("abandoned", now - timedelta(days=2))]),
        ]
    )

    result = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
        now=now,
    )
    # total_committed excludes the abandoned member: 2, not 3.
    assert result.total_committed == 2
    assert result.threshold == 2
    assert result.status == "pending_resolution"


@pytest.mark.parametrize(
    # threshold = min(2, majority(n)) for n >= 2. majority(n) grows with
    # n (3 for n=5, 4 for n=7, ...) but the cap of 2 always wins once
    # n >= 4 — "whichever is the smaller number" means the requirement
    # never exceeds 2 regardless of how large the committed group gets.
    "total,expected_threshold",
    [(2, 2), (3, 2), (4, 2), (5, 2), (7, 2)],
)
def test_threshold_matches_min_of_2_and_majority(total, expected_threshold):
    """Direct check of the 'min(2, majority(n)), floor of 2 requires
    n>=2' rule at several member counts."""
    problem = _problem()
    now = utcnow()
    members_with_events = []
    for i in range(total):
        m = _commitment(user_id=f"u{i}", problem_id=problem.id)
        members_with_events.append((m, []))

    commitment_repo, checkpoint_repo, objection_repo = _seed(members_with_events)

    result = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
        now=now,
    )
    assert result.threshold == expected_threshold
    assert result.total_committed == total


# --- raise_objection() ------------------------------------------------


def test_raise_objection_requires_committed_membership():
    problem = _problem()
    now = utcnow()
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m2 = _commitment(user_id="u2", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", now - timedelta(days=1))]),
            (m2, [("resolved", now - timedelta(days=1))]),
        ]
    )

    with pytest.raises(NotCommittedError):
        raise_objection(
            problem=problem,
            caller_user_id="stranger",
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
            objection_repo=objection_repo,
        )


def test_raise_objection_requires_active_window():
    """No threshold met yet -> nothing to object to."""
    problem = _problem()
    now = utcnow()
    m1 = _commitment(user_id="u1", problem_id=problem.id)
    m2 = _commitment(user_id="u2", problem_id=problem.id)

    commitment_repo, checkpoint_repo, objection_repo = _seed([(m1, []), (m2, [])])

    with pytest.raises(NoActiveResolutionWindowError):
        raise_objection(
            problem=problem,
            caller_user_id="u1",
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
            objection_repo=objection_repo,
        )


def test_raise_objection_twice_by_same_user_rejected():
    problem = _problem()
    now = utcnow()
    claim_time = now - timedelta(days=1)
    m1 = _commitment(user_id="u1", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m2 = _commitment(user_id="u2", problem_id=problem.id, status=CommitmentStatus.RESOLVED.value)
    m3 = _commitment(user_id="u3", problem_id=problem.id)

    commitment_repo, checkpoint_repo, objection_repo = _seed(
        [
            (m1, [("resolved", claim_time)]),
            (m2, [("resolved", claim_time)]),
            (m3, []),
        ]
    )

    raise_objection(
        problem=problem,
        caller_user_id="u3",
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
    )

    with pytest.raises(AlreadyObjectedError):
        raise_objection(
            problem=problem,
            caller_user_id="u3",
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
            objection_repo=objection_repo,
        )
