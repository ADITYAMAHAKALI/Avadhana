"""Commitment ORM model — the row that spends a focus slot.

This table is the enforcement point for two of the three non-negotiable
constraints in CLAUDE.md:

  1. 3-slot system: `app/services/commitment_service.py` counts rows with
     `status == ACTIVE` for a user before allowing a new commitment.
  2. 90-day commitment lock: `lock_expires_at` is set to
     `started_at + 90 days` at creation and reset to `now + 90 days` on
     `continue`. `app/services/checkpoint_service.py` refuses ANY
     checkpoint transition while `utcnow() < lock_expires_at` — there is
     no flag, role, or code path that bypasses this check.

Status semantics:
  - ACTIVE: counts toward the 3-slot limit. Set at creation; stays ACTIVE
    across `continue` checkpoints (a fresh 90-day cycle starts, but the
    slot is still spent).
  - RESOLVED / ABANDONED: terminal. Slot is freed (excluded from the
    3-slot count) and gated-voice checks fail from this point on — a
    resolved/abandoned commitment no longer grants posting rights on
    that problem. Never transitions back to ACTIVE (no "un-abandon").

Role/specialization: `specialization` must be null unless `role ==
ACTOR` — validated at the Pydantic schema layer (app/schemas.py) since
it's a request-shape rule, not a storage rule; the column itself stays
nullable for every role.
"""

import enum
import uuid
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base

LOCK_PERIOD_DAYS = 90


class CommitmentRole(str, enum.Enum):
    THINKER = "thinker"
    ACTOR = "actor"
    BACKER = "backer"


class ActorSpecialization(str, enum.Enum):
    LEGAL = "Legal"
    RESEARCH = "Research"
    CONTENT = "Content"
    WEB_APP_DEV = "Web & app dev"
    AD_CAMPAIGN = "Ad campaign"
    FIELD_ORGANIZING = "Field organizing"


class CommitmentStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


def default_lock_expiry() -> datetime:
    return utcnow() + timedelta(days=LOCK_PERIOD_DAYS)


class Commitment(Base):
    __tablename__ = "commitments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    problem_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("problems.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CommitmentStatus.ACTIVE.value
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    lock_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=default_lock_expiry
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    # Whether this commitment has ever had a resolve/abandon/continue
    # checkpoint applied (beyond the initial "created" audit row). Drives
    # the commitment-history vs. committed-problems split in the API:
    # a plain first-cycle ACTIVE commitment with no checkpoint history
    # belongs in `GET /users/me/committed-problems`; one that has been
    # through at least one resolve/abandon/continue belongs in
    # `GET /users/me/commitment-history` (per the API contract). We
    # derive this from the CommitmentCheckpoint rows rather than storing
    # a redundant boolean, to keep a single source of truth.
