"""Solution + SolutionAttribute ORM models (GitHub issue #65).

`Solution` is the provider-side supply/lead-gen surface — publishing is
ALWAYS FREE (CLAUDE.md "Monetization": "charging providers to list would
kill the supply side before it exists"). No quota/billing check exists
anywhere in the create-Solution path, unlike RFP posting.

`category_tags` is stored as a simple JSON text list column per the
build brief ("no separate tags table needed") — `SolutionAttribute` is
the structured, queryable-by-key data; `category_tags` is coarse/display
-oriented.

`SolutionAttribute.attribute_key` deliberately mirrors
`RFPRequirement.attribute_key`'s vocabulary so later attribute-match
scoring (not built here — see CLAUDE.md matching-engine section) can
compare like-for-like keys without a translation layer.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class SolutionStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Solution(Base):
    __tablename__ = "solutions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)

    # Simple JSON list column (e.g. ["healthcare", "logistics"]) — no
    # separate tags table needed per the build brief.
    category_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SolutionStatus.DRAFT.value
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class SolutionAttribute(Base):
    __tablename__ = "solution_attributes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    solution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("solutions.id"), nullable=False, index=True
    )
    attribute_key: Mapped[str] = mapped_column(String(200), nullable=False)
    attribute_value: Mapped[str] = mapped_column(String(1000), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
