"""Commitment checkpoint transitions — enforces the 90-day lock and
applies reputation deltas.

This is THE enforcement point for CLAUDE.md's non-negotiable constraint
#2: "once committed, a user cannot resolve/abandon/continue before 90
days have passed. No exceptions, no override path, anywhere in the
code." The `_assert_lock_expired()` check below runs unconditionally for
every action (resolve/abandon/continue) before anything else happens —
there is no parameter, role, or flag that skips it. If you're tempted to
add one (e.g. "let moderators force an early exit"), don't: CLAUDE.md
Critical Open Issue #2 explicitly flags that an early-exit path is a
*product decision* that hasn't been made, not something to slip in as an
engineering convenience.

Reputation deltas (flat for SLC v1 — tier-weighting is explicitly
deferred per the build brief, since S-tier vs D-tier resolution "should
mean much more" per CLAUDE.md but the concrete weighting isn't decided
yet):
  - resolve:  +20
  - abandon:  -15
  - continue:   0  (deliberately neutral — rewarding "continue" would
                     incentivize endless-continue farming as a way to
                     rack up reputation without ever finishing anything,
                     which contradicts "rewards follow-through, not
                     activity")
"""

from app.core.time import utcnow
from app.interfaces.repositories import CheckpointRepoPort, CommitmentRepoPort, UserRepoPort
from app.models.checkpoint import CheckpointEventType, CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus, default_lock_expiry
from app.services.errors import (
    CommitmentNotActiveError,
    CommitmentNotFoundError,
    LockActiveError,
    NotCommitmentOwnerError,
)

REPUTATION_DELTA_RESOLVE = 20
REPUTATION_DELTA_ABANDON = -15
REPUTATION_DELTA_CONTINUE = 0

_ACTION_TO_EVENT_TYPE = {
    "resolve": CheckpointEventType.RESOLVED.value,
    "abandon": CheckpointEventType.ABANDONED.value,
    "continue": CheckpointEventType.CONTINUED.value,
}

_ACTION_TO_REPUTATION_DELTA = {
    "resolve": REPUTATION_DELTA_RESOLVE,
    "abandon": REPUTATION_DELTA_ABANDON,
    "continue": REPUTATION_DELTA_CONTINUE,
}


def _assert_lock_expired(commitment: Commitment) -> None:
    """No bypass. Ever. See module docstring."""
    now = utcnow()
    lock_expires_at = commitment.lock_expires_at
    if lock_expires_at.tzinfo is None:
        # SQLite (integration tests) doesn't persist tzinfo; normalize
        # before comparing so this works identically to Postgres.
        lock_expires_at = lock_expires_at.replace(tzinfo=now.tzinfo)
    if now < lock_expires_at:
        remaining_seconds = (lock_expires_at - now).total_seconds()
        # Round UP so "2 hours remaining" reports 1 day, not 0 — never
        # understate how much longer the lock holds.
        days_remaining = max(1, -(-int(remaining_seconds) // 86400))
        raise LockActiveError(days_remaining=days_remaining)


def apply_checkpoint(
    *,
    commitment_id: str,
    caller_user_id: str,
    action: str,
    note: str | None,
    commitment_repo: CommitmentRepoPort,
    checkpoint_repo: CheckpointRepoPort,
    user_repo: UserRepoPort,
) -> Commitment:
    commitment = commitment_repo.get_by_id(commitment_id)
    if commitment is None:
        raise CommitmentNotFoundError(commitment_id)
    if commitment.user_id != caller_user_id:
        raise NotCommitmentOwnerError(commitment_id)
    if commitment.status != CommitmentStatus.ACTIVE.value:
        # Terminal states never re-open — no un-resolving/un-abandoning,
        # and no re-triggering continue on a commitment that already
        # ended.
        raise CommitmentNotActiveError(commitment_id, commitment.status)

    # Hard gate — see module docstring. Runs before ANY state mutation.
    _assert_lock_expired(commitment)

    if action == "resolve":
        commitment.status = CommitmentStatus.RESOLVED.value
    elif action == "abandon":
        commitment.status = CommitmentStatus.ABANDONED.value
    elif action == "continue":
        # Stays ACTIVE — still counts toward the 3-slot limit — but the
        # clock resets for a fresh 90-day cycle.
        commitment.lock_expires_at = default_lock_expiry()
    else:  # pragma: no cover - guarded by Pydantic Literal at the API layer
        raise ValueError(f"Unknown checkpoint action: {action}")

    commitment = commitment_repo.add(commitment)

    checkpoint_repo.add(
        CommitmentCheckpoint(
            commitment_id=commitment.id,
            event_type=_ACTION_TO_EVENT_TYPE[action],
            note=note,
        )
    )

    delta = _ACTION_TO_REPUTATION_DELTA[action]
    if delta != 0:
        user_repo.update_reputation(caller_user_id, delta)

    return commitment
