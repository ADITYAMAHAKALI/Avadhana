"""Unit tests for the 90-day commitment lock and checkpoint transitions
(app.services.checkpoint_service).

Per CLAUDE.md constraint #2: "once committed, a user cannot resolve/
abandon/continue before 90 days have passed. No exceptions, no override
path, anywhere in the code." Tests the boundary explicitly at day 89,
day 90, and day 91, plus the resolve/abandon/continue outcomes
(status, immutable audit rows, reputation deltas).
"""

from datetime import timedelta

import pytest

from app.core.time import utcnow
from app.models.checkpoint import CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus
from app.models.user import User
from app.services.checkpoint_service import (
    REPUTATION_DELTA_ABANDON,
    REPUTATION_DELTA_CONTINUE,
    REPUTATION_DELTA_RESOLVE,
    apply_checkpoint,
)
from app.services.errors import CommitmentNotActiveError, LockActiveError, NotCommitmentOwnerError
from tests.unit.fakes import FakeCheckpointRepo, FakeCommitmentRepo, FakeUserRepo


def _seeded(*, days_since_started: int, user_id: str = "user-1"):
    """Builds a commitment started `days_since_started` days ago, with a
    lock_expires_at consistent with that start (started_at + 90 days),
    wired into fresh fake repos."""
    now = utcnow()
    started_at = now - timedelta(days=days_since_started)
    lock_expires_at = started_at + timedelta(days=90)

    commitment = Commitment(
        user_id=user_id,
        problem_id="problem-1",
        role="thinker",
        specialization=None,
        status=CommitmentStatus.ACTIVE.value,
        started_at=started_at,
        lock_expires_at=lock_expires_at,
    )

    commitment_repo = FakeCommitmentRepo()
    commitment_repo.add(commitment)
    checkpoint_repo = FakeCheckpointRepo()
    checkpoint_repo.add(CommitmentCheckpoint(commitment_id=commitment.id, event_type="created"))
    user_repo = FakeUserRepo()
    user_repo.add(User(id=user_id, name="Test User", email="t@example.com", password_hash="x"))

    return commitment, commitment_repo, checkpoint_repo, user_repo


@pytest.mark.parametrize("action", ["resolve", "abandon", "continue"])
def test_checkpoint_at_day_89_is_rejected(action):
    commitment, commitment_repo, checkpoint_repo, user_repo = _seeded(days_since_started=89)

    with pytest.raises(LockActiveError) as exc_info:
        apply_checkpoint(
            commitment_id=commitment.id,
            caller_user_id="user-1",
            action=action,
            note=None,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
            user_repo=user_repo,
        )
    assert exc_info.value.days_remaining >= 1
    # No state mutation happened.
    assert commitment_repo.get_by_id(commitment.id).status == "active"


def test_checkpoint_exactly_at_day_90_boundary_is_rejected_if_lock_not_yet_expired():
    # started_at + 90 days == lock_expires_at exactly; "now" is
    # infinitesimally before that instant in practice, so this should
    # still be rejected. We simulate this by starting the commitment
    # 90 days ago minus a few seconds (i.e. lock expires a few seconds
    # from "now").
    now = utcnow()
    started_at = now - timedelta(days=90) + timedelta(seconds=30)
    lock_expires_at = started_at + timedelta(days=90)

    commitment = Commitment(
        user_id="user-1",
        problem_id="problem-1",
        role="thinker",
        status=CommitmentStatus.ACTIVE.value,
        started_at=started_at,
        lock_expires_at=lock_expires_at,
    )
    commitment_repo = FakeCommitmentRepo()
    commitment_repo.add(commitment)
    checkpoint_repo = FakeCheckpointRepo()
    checkpoint_repo.add(CommitmentCheckpoint(commitment_id=commitment.id, event_type="created"))
    user_repo = FakeUserRepo()
    user_repo.add(User(id="user-1", name="Test User", email="t@example.com", password_hash="x"))

    with pytest.raises(LockActiveError):
        apply_checkpoint(
            commitment_id=commitment.id,
            caller_user_id="user-1",
            action="resolve",
            note=None,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
            user_repo=user_repo,
        )


def test_checkpoint_at_day_91_is_allowed():
    commitment, commitment_repo, checkpoint_repo, user_repo = _seeded(days_since_started=91)

    result = apply_checkpoint(
        commitment_id=commitment.id,
        caller_user_id="user-1",
        action="resolve",
        note="All done",
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        user_repo=user_repo,
    )
    assert result.status == "resolved"


def test_resolve_sets_terminal_status_frees_slot_and_awards_reputation():
    commitment, commitment_repo, checkpoint_repo, user_repo = _seeded(days_since_started=95)

    result = apply_checkpoint(
        commitment_id=commitment.id,
        caller_user_id="user-1",
        action="resolve",
        note="Fixed it",
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        user_repo=user_repo,
    )

    assert result.status == "resolved"
    assert commitment_repo.count_active_for_user("user-1") == 0  # slot freed
    assert user_repo.get_by_id("user-1").reputation == REPUTATION_DELTA_RESOLVE

    checkpoints = checkpoint_repo.list_for_commitment(commitment.id)
    event_types = [c.event_type for c in checkpoints]
    assert event_types == ["created", "resolved"]


def test_abandon_sets_terminal_status_frees_slot_and_penalizes_reputation():
    commitment, commitment_repo, checkpoint_repo, user_repo = _seeded(days_since_started=100)

    result = apply_checkpoint(
        commitment_id=commitment.id,
        caller_user_id="user-1",
        action="abandon",
        note="Giving up",
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        user_repo=user_repo,
    )

    assert result.status == "abandoned"
    assert commitment_repo.count_active_for_user("user-1") == 0  # slot freed
    assert user_repo.get_by_id("user-1").reputation == REPUTATION_DELTA_ABANDON  # negative


def test_continue_keeps_active_resets_lock_and_does_not_change_reputation():
    commitment, commitment_repo, checkpoint_repo, user_repo = _seeded(days_since_started=95)
    old_lock_expiry = commitment.lock_expires_at

    result = apply_checkpoint(
        commitment_id=commitment.id,
        caller_user_id="user-1",
        action="continue",
        note=None,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        user_repo=user_repo,
    )

    assert result.status == "active"
    assert result.lock_expires_at > old_lock_expiry
    # Still counts toward the 3-slot limit.
    assert commitment_repo.count_active_for_user("user-1") == 1
    assert user_repo.get_by_id("user-1").reputation == REPUTATION_DELTA_CONTINUE == 0


def test_abandoned_commitment_cannot_be_resolved_afterward_no_un_abandon():
    commitment, commitment_repo, checkpoint_repo, user_repo = _seeded(days_since_started=100)

    apply_checkpoint(
        commitment_id=commitment.id,
        caller_user_id="user-1",
        action="abandon",
        note=None,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        user_repo=user_repo,
    )

    with pytest.raises(CommitmentNotActiveError):
        apply_checkpoint(
            commitment_id=commitment.id,
            caller_user_id="user-1",
            action="resolve",
            note="Actually let's un-abandon this",
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
            user_repo=user_repo,
        )


def test_non_owner_cannot_checkpoint_someone_elses_commitment():
    commitment, commitment_repo, checkpoint_repo, user_repo = _seeded(
        days_since_started=100, user_id="owner"
    )

    with pytest.raises(NotCommitmentOwnerError):
        apply_checkpoint(
            commitment_id=commitment.id,
            caller_user_id="someone-else",
            action="resolve",
            note=None,
            commitment_repo=commitment_repo,
            checkpoint_repo=checkpoint_repo,
            user_repo=user_repo,
        )


def test_no_bypass_flag_exists_for_the_lock():
    """Documents the contract: apply_checkpoint's signature has no
    override/force/admin parameter of any kind. If this test starts
    failing because someone added one, that's the point — CLAUDE.md is
    explicit that there is no early-exit path."""
    import inspect

    sig = inspect.signature(apply_checkpoint)
    param_names = set(sig.parameters.keys())
    forbidden = {"force", "override", "bypass", "admin", "skip_lock"}
    assert not (param_names & forbidden)
