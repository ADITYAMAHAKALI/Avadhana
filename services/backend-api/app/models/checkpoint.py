"""CommitmentCheckpoint ORM model — immutable audit trail.

Every commitment lifecycle transition (including the initial `created`
event fired at commitment creation) writes one row here. Per CLAUDE.md:
"All moderation actions and AI operations should be immutable — never
update or delete, only insert new records." The same principle is
applied here for commitment checkpoints, since they're the audit record
behind reputation changes and the public commitment-history profile —
retroactively editing them would undermine the "reputational cost is the
point" design goal (CLAUDE.md "Mark abandoned must be visible ... and
never be counterbalanced").

Nothing in this codebase should ever UPDATE or DELETE a row in this
table — only `app/services/checkpoint_service.py` INSERTs new rows.

`GET /users/me/commitment-history` also uses the presence of a
non-`created` checkpoint (resolved/abandoned/continued) to decide
whether a commitment belongs in "history" vs. "committed-problems" —
see `app/models/commitment.py` docstring.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class CheckpointEventType(str, enum.Enum):
    CREATED = "created"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"
    CONTINUED = "continued"


class CommitmentCheckpoint(Base):
    __tablename__ = "commitment_checkpoints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    commitment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("commitments.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
