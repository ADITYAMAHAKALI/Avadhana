"""Commitment-history assembly for GET /users/me/commitment-history.

A commitment appears here once it has at least one non-`created`
checkpoint (resolved/abandoned/continued) — see
`app/models/commitment.py` docstring for why plain first-cycle ACTIVE
commitments belong in committed-problems instead. The status/note shown
reflect the MOST RECENT such checkpoint (e.g. a commitment continued
twice then resolved shows "resolved", not "continued" — the latest
transition is what's currently true of the commitment).
"""

from app.core.time import utcnow
from app.models.checkpoint import CheckpointEventType, CommitmentCheckpoint
from app.models.commitment import Commitment

_EVENT_TO_HISTORY_STATUS = {
    CheckpointEventType.RESOLVED.value: "resolved",
    CheckpointEventType.ABANDONED.value: "abandoned",
    CheckpointEventType.CONTINUED.value: "continued",
}


def latest_history_status_and_note(
    commitment: Commitment, checkpoints: list[CommitmentCheckpoint]
) -> tuple[str, str] | None:
    """Returns (status, note) for the most recent non-`created` checkpoint,
    or None if the commitment has no such checkpoint yet (i.e. it doesn't
    belong in history)."""
    relevant = [c for c in checkpoints if c.event_type != CheckpointEventType.CREATED.value]
    if not relevant:
        return None
    latest = max(relevant, key=lambda c: c.occurred_at)
    status = _EVENT_TO_HISTORY_STATUS[latest.event_type]

    started_at = commitment.started_at
    occurred_at = latest.occurred_at
    now = utcnow()
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=now.tzinfo)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=now.tzinfo)
    days_elapsed = max(0, (occurred_at - started_at).days)

    if status == "resolved":
        note = f"Resolved after {days_elapsed} days"
    elif status == "abandoned":
        note = f"Abandoned at day {days_elapsed}"
    else:
        note = "Continued for another cycle"

    return status, note
