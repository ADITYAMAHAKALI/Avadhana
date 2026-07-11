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

Reputation deltas are tier-weighted per CLAUDE.md's "Problem Lifecycle
Protocol" > "Reward protocol" (issue #101) — resolving/abandoning a
higher-tier problem moves reputation more than a lower-tier one, making
concrete the Gamification & Reputation section's principle that "a badge
for resolving an S-tier problem should mean much more than one for a
D-tier problem":

  Tier | Resolve | Abandon | Continue
  -----|---------|---------|---------
  D    |    +10  |    -15  |    0
  C    |    +20  |    -15  |    0
  B    |    +35  |    -20  |    0
  A    |    +60  |    -25  |    0
  S    |   +100  |    -30  |    0

`continue` stays a flat 0 at every tier — per CLAUDE.md, "persistence
itself isn't the signal being rewarded, follow-through to an actual
outcome is." Rewarding it would incentivize endless-continue farming as
a way to rack up reputation without ever finishing anything, which
contradicts "rewards follow-through, not activity."
"""

from app.core.time import utcnow
from app.interfaces.repositories import (
    CheckpointRepoPort,
    CommitmentRepoPort,
    ProblemRepoPort,
    UserRepoPort,
)
from app.models.checkpoint import CheckpointEventType, CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus, default_lock_expiry
from app.services.errors import (
    CommitmentNotActiveError,
    CommitmentNotFoundError,
    LockActiveError,
    NotCommitmentOwnerError,
    ProblemNotFoundError,
)

REPUTATION_DELTA_CONTINUE = 0

_ACTION_TO_EVENT_TYPE = {
    "resolve": CheckpointEventType.RESOLVED.value,
    "abandon": CheckpointEventType.ABANDONED.value,
    "continue": CheckpointEventType.CONTINUED.value,
}

# Tier-weighted reputation deltas, keyed by (action, tier). `continue` is
# intentionally absent here — it's a single flat constant handled
# separately in `_reputation_delta_for()`, not a 5-row table, since it
# doesn't vary by tier.
_REPUTATION_DELTA_TABLE: dict[tuple[str, str], int] = {
    ("resolve", "D"): 10,
    ("resolve", "C"): 20,
    ("resolve", "B"): 35,
    ("resolve", "A"): 60,
    ("resolve", "S"): 100,
    ("abandon", "D"): -15,
    ("abandon", "C"): -15,
    ("abandon", "B"): -20,
    ("abandon", "A"): -25,
    ("abandon", "S"): -30,
}


def _reputation_delta_for(action: str, tier: str) -> int:
    if action == "continue":
        return REPUTATION_DELTA_CONTINUE
    return _REPUTATION_DELTA_TABLE[(action, tier)]


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
    problem_repo: ProblemRepoPort,
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

    # Tier-weighted deltas need the Problem row (Commitment only carries
    # problem_id, not tier) — one extra lookup via the same
    # ProblemRepoPort.get_by_id already used elsewhere (e.g.
    # app/routers/problems.py), no new repo method needed.
    problem = problem_repo.get_by_id(commitment.problem_id)
    if problem is None:  # pragma: no cover - FK guarantees this in practice
        raise ProblemNotFoundError(commitment.problem_id)

    delta = _reputation_delta_for(action, problem.tier)
    if delta != 0:
        user_repo.update_reputation(caller_user_id, delta)

    return commitment
