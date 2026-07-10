"""RFP + RFPRequirement ORM models (GitHub issue #64).

`RFP` is a buyer Organization's problem posting with structured
requirements, resolved either by promotion into a civic `Problem`
(`resolution_mode: community`), by the matching engine
(`resolution_mode: marketplace`), or both. See CLAUDE.md "Solution
Marketplace Architecture" -> "Two resolution modes per RFP" and "Domain
model".

`promoted_problem_id` and `is_billable`:
- `promoted_problem_id`: set by
  `app.services.marketplace_service.promote_rfp_to_problem` (issue #70,
  `POST /marketplace/rfps/{rfp_id}/promote`) once an RFP is promoted into
  a civic Problem. Null until then; an RFP may only be promoted once.
- `is_billable`: set True by `app.services.marketplace_service.create_rfp`
  (issue #71) when the posting Organization's `rfp_free_quota_used`
  (post-increment) exceeds `rfp_free_quota_limit` — see
  `app/models/marketplace/organization.py` docstring and
  `app/models/marketplace/billing.py`. Real payment processing (charging
  a card, invoicing) is still out of scope; this only flags the RFP as
  billable and logs a `BillingEvent`.

`resolution_mode`, `visibility`, and `status` are plain string columns
(not DB enums), consistent with `Problem.tier`'s "iteration speed over
DB-level strictness" reasoning — validated at the Pydantic schema layer.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class ResolutionMode(str, enum.Enum):
    COMMUNITY = "community"
    MARKETPLACE = "marketplace"
    BOTH = "both"


class RFPVisibility(str, enum.Enum):
    PUBLIC = "public"
    INVITE_ONLY = "invite_only"


class RFPStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class RFP(Base):
    __tablename__ = "rfps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)

    # Nullable: some RFPs won't have a public budget (CLAUDE.md build
    # brief, issue #64 scope).
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    timeline: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    industry: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    geography: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    resolution_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RFPVisibility.PUBLIC.value
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RFPStatus.DRAFT.value
    )

    # Set by the promotion flow (issue #70). No FK constraint enforced at
    # the DB level here since `problems.id` lives in the civic schema
    # this module deliberately doesn't couple to at the ORM-relationship
    # level (see module docstring); a plain nullable string column keeps
    # that boundary clean while still recording the link.
    promoted_problem_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Column only, always False for now — real billing gating is a later
    # phase (see app/models/marketplace/organization.py docstring).
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class RFPRequirement(Base):
    __tablename__ = "rfp_requirements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rfp_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfps.id"), nullable=False, index=True
    )
    attribute_key: Mapped[str] = mapped_column(String(200), nullable=False)
    attribute_value: Mapped[str] = mapped_column(String(1000), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_hard_constraint: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
