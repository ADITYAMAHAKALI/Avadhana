"""Organization + OrganizationMembership ORM models (GitHub issue #63).

`Organization` is the account type for enterprises/agencies/solution
providers on the Marketplace — deliberately NOT the same as a civic
`User` (see CLAUDE.md "Solution Marketplace Architecture" -> "Domain
model"). A `User` acts on an Organization's behalf via
`OrganizationMembership` when posting RFPs or publishing Solutions.

`rfp_free_quota_used` / `rfp_free_quota_limit` / `billing_status` exist
as plain columns only for this phase — no quota-enforcement or paywall
logic is wired up yet (that's a later phase per the build brief's
explicit non-goals). `billing_status` is a plain string column (not a DB
enum) for the same "iteration speed over DB-level strictness" reasoning
already used for `Problem.tier` (see `app/models/problem.py`).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base

DEFAULT_RFP_FREE_QUOTA_LIMIT = 100


class OrganizationMembershipRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class BillingStatus(str, enum.Enum):
    ACTIVE = "active"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)

    # Quota/billing columns only — no enforcement logic yet (issue #63
    # scope; the paywall gate and BillingEvent ledger are later phases,
    # see CLAUDE.md "Monetization").
    rfp_free_quota_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rfp_free_quota_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_RFP_FREE_QUOTA_LIMIT
    )
    billing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=BillingStatus.ACTIVE.value
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
