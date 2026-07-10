"""Marketplace ORM model subpackage.

Deliberately split from the flat `app/models/*.py` layout used by the
civic Problem/Commitment mechanic — see CLAUDE.md "Solution Marketplace
Architecture" -> "Service boundaries (solo-dev pragmatism)": this is a
distinct product surface (B2B/B2G RFP <-> Solution matching) that is
architecturally independent of the 3-slot / 90-day-lock / commitment-
gated-voice civic mechanic, and structured this way specifically so it
can be extracted into its own service later without a rework.

Every model module here must ALSO be imported by `app/models/__init__.py`
(not just this file) so `Base.metadata` sees every table for Alembic
autogenerate and the SQLite-backed integration tests' `create_all()` —
same footgun warning as the top-level `app/models/__init__.py` docstring.
"""

from app.models.marketplace.billing import BillingEvent
from app.models.marketplace.embedding import EmbeddingVector
from app.models.marketplace.organization import Organization, OrganizationMembership
from app.models.marketplace.rfp import RFP, RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute

__all__ = [
    "Organization",
    "OrganizationMembership",
    "RFP",
    "RFPRequirement",
    "Solution",
    "SolutionAttribute",
    "BillingEvent",
    "EmbeddingVector",
]
