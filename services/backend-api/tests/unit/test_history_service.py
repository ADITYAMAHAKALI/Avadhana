"""Unit tests for commitment-history assembly, incl. that abandoned
status is visible and never reversible (CLAUDE.md: "Mark abandoned must
be visible on the user's profile")."""

from datetime import timedelta

from app.core.time import utcnow
from app.models.checkpoint import CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus
from app.services.history_service import latest_history_status_and_note


def _commitment(days_ago_started: int) -> Commitment:
    now = utcnow()
    return Commitment(
        id="c1",
        user_id="u1",
        problem_id="p1",
        role="thinker",
        status=CommitmentStatus.ABANDONED.value,
        started_at=now - timedelta(days=days_ago_started),
    )


def test_plain_created_only_commitment_has_no_history_entry():
    commitment = _commitment(days_ago_started=10)
    checkpoints = [CommitmentCheckpoint(commitment_id="c1", event_type="created")]
    assert latest_history_status_and_note(commitment, checkpoints) is None


def test_abandoned_commitment_produces_visible_history_note():
    commitment = _commitment(days_ago_started=12)
    now = utcnow()
    checkpoints = [
        CommitmentCheckpoint(commitment_id="c1", event_type="created", occurred_at=now - timedelta(days=12)),
        CommitmentCheckpoint(commitment_id="c1", event_type="abandoned", occurred_at=now),
    ]
    result = latest_history_status_and_note(commitment, checkpoints)
    assert result is not None
    status, note = result
    assert status == "abandoned"
    assert "Abandoned at day" in note


def test_resolved_commitment_note_mentions_days():
    commitment = _commitment(days_ago_started=94)
    now = utcnow()
    checkpoints = [
        CommitmentCheckpoint(commitment_id="c1", event_type="created", occurred_at=now - timedelta(days=94)),
        CommitmentCheckpoint(commitment_id="c1", event_type="resolved", occurred_at=now),
    ]
    result = latest_history_status_and_note(commitment, checkpoints)
    assert result is not None
    status, note = result
    assert status == "resolved"
    assert "Resolved after 94 days" == note


def test_continued_then_resolved_reports_the_latest_transition():
    commitment = _commitment(days_ago_started=200)
    now = utcnow()
    checkpoints = [
        CommitmentCheckpoint(commitment_id="c1", event_type="created", occurred_at=now - timedelta(days=200)),
        CommitmentCheckpoint(commitment_id="c1", event_type="continued", occurred_at=now - timedelta(days=100)),
        CommitmentCheckpoint(commitment_id="c1", event_type="resolved", occurred_at=now),
    ]
    result = latest_history_status_and_note(commitment, checkpoints)
    assert result is not None
    status, _ = result
    # Most recent transition wins, not the first one.
    assert status == "resolved"
