"""ORM model -> API schema translation for the Marketplace module.

Sibling to `app/services/presenters.py`, matching the same split as
`app/schemas_marketplace.py` vs. `app/schemas.py` — kept separate so the
civic-platform presenter module doesn't grow a second, unrelated set of
imports for a product surface that's architecturally independent (see
CLAUDE.md "Solution Marketplace Architecture").
"""

from app.models.marketplace.billing import BillingEvent
from app.models.marketplace.matching import MatchRun, SolutionMatch
from app.models.marketplace.organization import Organization, OrganizationMembership
from app.models.marketplace.rfp import RFP, RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.schemas_marketplace import (
    AttributeMatchOut,
    BillingEventOut,
    MatchRunTriggerOut,
    OrganizationMembershipOut,
    OrganizationOut,
    RFPMatchesOut,
    RFPOut,
    RFPRequirementOut,
    SolutionAttributeOut,
    SolutionMatchOut,
    SolutionOut,
)
from app.services.marketplace_matching import AttributeMatchResult


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


def attribute_match_to_out(result: AttributeMatchResult) -> AttributeMatchOut:
    return AttributeMatchOut(
        solution=solution_to_out(result.solution),
        score=result.score,
        matched_requirement_ids=result.matched_requirement_ids,
    )


def match_run_to_out(match_run: MatchRun) -> MatchRunTriggerOut:
    return MatchRunTriggerOut(
        id=match_run.id,
        rfp_id=match_run.rfp_id,
        status=match_run.status,
        started_at=match_run.started_at,
    )


def solution_match_to_out(match: SolutionMatch, solution: Solution) -> SolutionMatchOut:
    return SolutionMatchOut(
        id=match.id,
        match_run_id=match.match_run_id,
        solution=solution_to_out(solution),
        final_rrf_score=match.final_rrf_score,
        rank=match.rank,
        signal_scores=dict(match.signal_scores or {}),
        signal_ranks=dict(match.signal_ranks or {}),
    )


def rfp_matches_to_out(
    match_run: MatchRun | None,
    matches_with_solutions: list[tuple[SolutionMatch, Solution]],
) -> RFPMatchesOut:
    return RFPMatchesOut(
        match_run=match_run_to_out(match_run) if match_run is not None else None,
        matches=[solution_match_to_out(match, solution) for match, solution in matches_with_solutions],
    )
