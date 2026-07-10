"""ORM model -> API schema translation for the Marketplace module.

Sibling to `app/services/presenters.py`, matching the same split as
`app/schemas_marketplace.py` vs. `app/schemas.py` — kept separate so the
civic-platform presenter module doesn't grow a second, unrelated set of
imports for a product surface that's architecturally independent (see
CLAUDE.md "Solution Marketplace Architecture").
"""

from app.models.marketplace.billing import BillingEvent
from app.models.marketplace.organization import Organization, OrganizationMembership
from app.models.marketplace.rfp import RFP, RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.schemas_marketplace import (
    BillingEventOut,
    OrganizationMembershipOut,
    OrganizationOut,
    RFPOut,
    RFPRequirementOut,
    SolutionAttributeOut,
    SolutionOut,
)


def organization_to_out(organization: Organization) -> OrganizationOut:
    return OrganizationOut(
        id=organization.id,
        name=organization.name,
        rfp_free_quota_used=organization.rfp_free_quota_used,
        rfp_free_quota_limit=organization.rfp_free_quota_limit,
        billing_status=organization.billing_status,
        created_at=organization.created_at,
    )


def membership_to_out(membership: OrganizationMembership) -> OrganizationMembershipOut:
    return OrganizationMembershipOut(
        id=membership.id,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        role=membership.role,
        created_at=membership.created_at,
    )


def rfp_to_out(rfp: RFP) -> RFPOut:
    return RFPOut(
        id=rfp.id,
        organization_id=rfp.organization_id,
        title=rfp.title,
        description=rfp.description,
        budget_min=rfp.budget_min,
        budget_max=rfp.budget_max,
        timeline=rfp.timeline,
        industry=rfp.industry,
        geography=rfp.geography,
        resolution_mode=rfp.resolution_mode,
        visibility=rfp.visibility,
        status=rfp.status,
        promoted_problem_id=rfp.promoted_problem_id,
        is_billable=rfp.is_billable,
        created_at=rfp.created_at,
    )


def rfp_requirement_to_out(requirement: RFPRequirement) -> RFPRequirementOut:
    return RFPRequirementOut(
        id=requirement.id,
        rfp_id=requirement.rfp_id,
        attribute_key=requirement.attribute_key,
        attribute_value=requirement.attribute_value,
        weight=requirement.weight,
        is_hard_constraint=requirement.is_hard_constraint,
        created_at=requirement.created_at,
    )


def solution_to_out(solution: Solution) -> SolutionOut:
    return SolutionOut(
        id=solution.id,
        organization_id=solution.organization_id,
        title=solution.title,
        description=solution.description,
        category_tags=list(solution.category_tags or []),
        status=solution.status,
        created_at=solution.created_at,
    )


def solution_attribute_to_out(attribute: SolutionAttribute) -> SolutionAttributeOut:
    return SolutionAttributeOut(
        id=attribute.id,
        solution_id=attribute.solution_id,
        attribute_key=attribute.attribute_key,
        attribute_value=attribute.attribute_value,
        created_at=attribute.created_at,
    )


def billing_event_to_out(event: BillingEvent) -> BillingEventOut:
    return BillingEventOut(
        id=event.id,
        organization_id=event.organization_id,
        rfp_id=event.rfp_id,
        event_type=event.event_type,
        amount=event.amount,
        occurred_at=event.occurred_at,
    )
