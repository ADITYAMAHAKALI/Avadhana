"""ORM model package.

Every model module must be imported here so `Base.metadata` (used by
Alembic autogenerate and by the SQLite-backed integration tests'
`Base.metadata.create_all`) actually sees every table. Forgetting to add
a new model here is a common footgun — if a migration autogenerate comes
up empty for a table you just added, check this file first.
"""

from app.db.base import Base
from app.models.checkpoint import CommitmentCheckpoint
from app.models.commitment import Commitment
from app.models.feed import Comment, FeedPost, PostLike
from app.models.marketplace.billing import BillingEvent
from app.models.marketplace.embedding import EmbeddingVector
from app.models.marketplace.organization import Organization, OrganizationMembership
from app.models.marketplace.rfp import RFP, RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.models.moderation import ModerationOverrideEvent
from app.models.problem import Problem
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Problem",
    "Commitment",
    "CommitmentCheckpoint",
    "FeedPost",
    "PostLike",
    "Comment",
    "ModerationOverrideEvent",
    "Organization",
    "OrganizationMembership",
    "RFP",
    "RFPRequirement",
    "Solution",
    "SolutionAttribute",
    "BillingEvent",
    "EmbeddingVector",
]
