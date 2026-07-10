"""BillingEvent ORM model — immutable audit trail for RFP free-quota
consumption and billable postings (GitHub issue #71).

Mirrors `app.models.checkpoint.CommitmentCheckpoint` and
`app.models.moderation.ModerationOverrideEvent` exactly: per CLAUDE.md's
immutability rule ("All moderation actions and AI operations should be
immutable — never update or delete, only insert new records"), every RFP
creation writes exactly one new row here (`free_rfp_posted` while under
`Organization.rfp_free_quota_limit`, `billable_rfp_posted` once it's
exceeded) — see `app/services/marketplace_service.py::create_rfp`.
Nothing in this codebase should ever UPDATE or DELETE a row in this
table — only that function INSERTs new rows, via
`app.impl.repositories.SqlAlchemyBillingEventRepo.add`.

`rfp_id` is nullable per CLAUDE.md "Domain model": "some billing events
might not tie to a specific RFP later, but for this phase they always
will" — every event this phase writes does carry an `rfp_id`, the column
is just left open for a future event_type that doesn't.

`amount` is nullable: no real pricing model exists yet (CLAUDE.md
"Monetization" — "the actual payment step ... is a separate, later piece
of work"). Always `None` for now; a future billing-integration pass sets
a real figure once pricing exists.

`event_type` is a plain string column (not a DB enum), consistent with
this codebase's other lightweight-enum columns (`RFP.status`,
`Organization.billing_status`) — "iteration speed over DB-level
strictness".
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class BillingEventType(str, enum.Enum):
    FREE_RFP_POSTED = "free_rfp_posted"
    BILLABLE_RFP_POSTED = "billable_rfp_posted"


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    rfp_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rfps.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
