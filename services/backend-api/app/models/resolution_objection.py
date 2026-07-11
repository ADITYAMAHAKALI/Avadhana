"""ResolutionObjection ORM model — immutable audit trail for the
problem-level resolution-verification protocol (issue #100).

Per CLAUDE.md "Problem Lifecycle Protocol": a problem's aggregate status
becomes Resolved once >= 2 committed members (or a strict majority,
whichever is smaller) have independently marked their own commitment
`resolved` via a `CommitmentCheckpoint`, AND no committed member has
raised an objection within a 7-day window starting from the *first*
`resolved` claim. Any committed member may raise exactly ONE objection
during that window — a single lightweight action, not a full dispute
process.

Mirrors `app.models.checkpoint.CommitmentCheckpoint` and
`app.models.moderation.ModerationOverrideEvent` exactly: insert-only,
per CLAUDE.md's immutability rule ("All moderation actions and AI
operations should be immutable — never update or delete, only insert
new records"). Nothing in this codebase should ever UPDATE or DELETE a
row in this table — only `app/services/problem_lifecycle_service.py`
INSERTs new rows (via the objection endpoint in
`app/routers/problems.py`).

"One objection per user per resolution-claim episode": there is no
`episode_id` column here by design. An "episode" is not a stored
concept — it's derived at read time in
`app/services/problem_lifecycle_service.py` from the timestamp of the
earliest currently-relevant `resolved` checkpoint claim (see that
module's docstring for the exact boundary rule). Objection rows are
timestamped (`raised_at`) and matched against the *current* episode's
window by comparing `raised_at` to the episode's `[window_start,
window_start + 7 days)` range — an objection from a past, already-closed
episode simply falls outside that range and is ignored, without ever
needing to be deleted or tagged as stale. This keeps the audit trail
permanent (an objection is never erased when a new episode begins)
while still only counting toward the episode it was actually raised
in.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class ResolutionObjection(Base):
    __tablename__ = "resolution_objections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    problem_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("problems.id"), nullable=False, index=True
    )
    objecting_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    raised_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
