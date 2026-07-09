"""ModerationOverrideEvent ORM model — immutable audit trail for the
human-moderator override baseline (issue #59).

No AI moderation exists yet (deferred, post-v1) — this is the baseline
*human* lever: a platform admin (`User.is_platform_admin`, gated via
`app.core.auth_dependencies.require_platform_admin`) can hide or restore
an abusive/spam `FeedPost` or `Comment`. Per CLAUDE.md's immutability
rule ("All moderation actions and AI operations should be immutable —
never update or delete, only insert new records") and mirroring
`app.models.checkpoint.CommitmentCheckpoint` exactly: every hide/restore
action writes one new row here. Nothing in this codebase should ever
UPDATE or DELETE a row in this table — only
`app/services/moderation_service.py` INSERTs new rows.

The target's current-state `hidden` flag (on `FeedPost`/`Comment`, see
`app/models/feed.py`) is a separate, mutable, denormalized projection —
this table is the durable "why/who/when" record behind it, and is what
`GET /problems/{problem_id}/moderation-log` reads back (CLAUDE.md
"Transparency: Committed members can view moderation logs for their
problem" — scoped to admin-only for this baseline pass, see that
router's docstring for why).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class ModerationTargetType(str, enum.Enum):
    POST = "post"
    COMMENT = "comment"


class ModerationAction(str, enum.Enum):
    HIDDEN = "hidden"
    RESTORED = "restored"


class ModerationOverrideEvent(Base):
    __tablename__ = "moderation_override_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    performed_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
