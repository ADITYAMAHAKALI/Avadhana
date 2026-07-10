"""Pydantic request/response models for the Solution Marketplace module
(GitHub issues #63, #64, #65 under epic #62).

Kept as a separate sibling module (not folded into the flat
`app/schemas.py`) per that file's own docstring, which flags itself for
a split once the schema surface grows unwieldy — the Marketplace surface
(Organization/RFP/Solution + their nested requirement/attribute rows) is
large enough on its own to justify a dedicated module without disturbing
any existing import of `app.schemas`. Nothing in `app/schemas.py`
changes; every existing `from app.schemas import ...` continues to work
unmodified.

Same `CamelModel` convention as `app/schemas.py` (camelCase on the wire,
snake_case in Python) — imported from there rather than redefined, so
both modules share one base and one `to_camel` alias generator.
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas import CamelModel

OrganizationRole = Literal["admin", "member"]
ResolutionMode = Literal["community", "marketplace", "both"]
RFPVisibility = Literal["public", "invite_only"]
RFPStatus = Literal["draft", "open", "closed"]
SolutionStatus = Literal["draft", "published"]
BillingEventType = Literal["free_rfp_posted", "billable_rfp_posted"]


# --- Organizations ----------------------------------------------------


class OrganizationCreateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=300)


class OrganizationOut(CamelModel):
    id: str
    name: str
    rfp_free_quota_used: int
    rfp_free_quota_limit: int
    billing_status: str
    created_at: datetime


class OrganizationMemberAddRequest(CamelModel):
    user_id: str
    role: OrganizationRole = "member"


class OrganizationMembershipOut(CamelModel):
    id: str
    organization_id: str
    user_id: str
    role: OrganizationRole
    created_at: datetime


# --- RFPs ---------------------------------------------------------------


class RFPRequirementCreateRequest(CamelModel):
    attribute_key: str = Field(min_length=1, max_length=200)
    attribute_value: str = Field(min_length=1, max_length=1000)
    weight: float = Field(default=1.0, ge=0.0)
    is_hard_constraint: bool = False


class RFPRequirementOut(CamelModel):
    id: str
    rfp_id: str
    attribute_key: str
    attribute_value: str
    weight: float
    is_hard_constraint: bool
    created_at: datetime


class RFPCreateRequest(CamelModel):
    organization_id: str
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    budget_min: float | None = Field(default=None, ge=0.0)
    budget_max: float | None = Field(default=None, ge=0.0)
    timeline: str = Field(default="", max_length=300)
    industry: str = Field(default="", max_length=100)
    geography: str = Field(default="", max_length=200)
    resolution_mode: ResolutionMode = "marketplace"
    visibility: RFPVisibility = "public"


class RFPOut(CamelModel):
    id: str
    organization_id: str
    title: str
    description: str
    budget_min: float | None
    budget_max: float | None
    timeline: str
    industry: str
    geography: str
    resolution_mode: ResolutionMode
    visibility: RFPVisibility
    status: RFPStatus
    # Column-only for now (issue #70 wires the real promotion flow) —
    # always null until that lands.
    promoted_problem_id: str | None
    # Column-only for now (billing gating is a later phase) — always
    # False.
    is_billable: bool
    created_at: datetime


# --- Solutions ------------------------------------------------------------


class SolutionAttributeCreateRequest(CamelModel):
    attribute_key: str = Field(min_length=1, max_length=200)
    attribute_value: str = Field(min_length=1, max_length=1000)


class SolutionAttributeOut(CamelModel):
    id: str
    solution_id: str
    attribute_key: str
    attribute_value: str
    created_at: datetime


class SolutionCreateRequest(CamelModel):
    organization_id: str
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    category_tags: list[str] = Field(default_factory=list)


class SolutionOut(CamelModel):
    id: str
    organization_id: str
    title: str
    description: str
    category_tags: list[str]
    status: SolutionStatus
    created_at: datetime


# --- Billing events (issue #71) -------------------------------------------


class BillingEventOut(CamelModel):
    id: str
    organization_id: str
    rfp_id: str | None
    event_type: BillingEventType
    amount: float | None
    occurred_at: datetime


# --- Error payloads (documented shapes, transported via HTTPException
# detail, same convention as app/schemas.py) -------------------------------


class NotOrgMemberError(CamelModel):
    error: Literal["NOT_ORG_MEMBER"] = "NOT_ORG_MEMBER"
    message: str


class NotOrgAdminError(CamelModel):
    error: Literal["NOT_ORG_ADMIN"] = "NOT_ORG_ADMIN"
    message: str
