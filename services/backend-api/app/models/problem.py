"""Problem ORM model.

Deliberately minimal for SLC v1: no hierarchy (parent/child pointers),
no split/merge, no tier-reclassification history — those are explicitly
deferred (see CLAUDE.md "What This Platform Is Not" scope and the
backend-build brief's "Explicit scope boundaries"). The API always
reports `parentProblemTitle: null` and `followingCount: 0` for now; when
hierarchy/follow-tracking land, this model gains real columns and the
API stops hardcoding those fields.

Role counts (thinkerCount/actorCount/backerCount) are NOT stored columns
— they're computed live from ACTIVE commitments at read time (see
`app/services/problem_service.py`). Storing denormalized counters here
would require careful invalidation on every commitment/checkpoint
transition; for SLC v1 scale, a COUNT query per problem read is simpler
and can't drift out of sync.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base

# Kept as a plain tuple (not a DB enum) so adding/renaming tiers later is
# a one-line change, not a migration. Validated at the Pydantic schema
# layer (app/schemas.py), not enforced as a DB CHECK constraint — SLC v1
# trades a little DB-level strictness for iteration speed here.
VALID_TIERS = ("S", "A", "B", "C", "D")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(String(5000), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    tier: Mapped[str] = mapped_column(String(1), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
