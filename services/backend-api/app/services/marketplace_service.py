"""Marketplace business rules: Organization membership/admin gates, RFP
posting (member-only), Solution publishing (member-only, always free),
and visibility filtering for RFP search.

Mirrors the shape of `app/services/commitment_service.py` and
`app/services/commitment_gate.py` — plain functions taking repo ports,
raising the domain exceptions in `app/services/errors.py`, with zero
FastAPI dependency so they're importable/testable from `tests/unit/`
without a database. Routers (`app/routers/marketplace/*.py`) translate
these exceptions into HTTP responses.

Explicit non-goals enforced here (per the build brief): no quota/billing
check anywhere in `create_solution` (publishing is always free — CLAUDE.md
"Monetization"), and no quota/billing check in `create_rfp` either (RFP
free-quota *tracking* exists as columns on `Organization` but the
paywall gate itself is a later phase, not built in this pass).
"""

from app.interfaces.repositories import OrganizationRepoPort, RFPRepoPort, SolutionRepoPort
from app.models.marketplace.organization import (
    Organization,
    OrganizationMembership,
    OrganizationMembershipRole,
)
from app.models.marketplace.rfp import RFP, RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.services.errors import (
    NotOrgAdminError,
    NotOrgMemberError,
    OrganizationNotFoundError,
    RFPNotFoundError,
    SolutionNotFoundError,
)


def create_organization(
    *, name: str, creator_user_id: str, org_repo: OrganizationRepoPort
) -> Organization:
    """Creates an Organization and grants its creator the first `admin`
    membership — there is no path to a memberless Organization."""
    organization = org_repo.add(Organization(name=name))
    org_repo.add_membership(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=creator_user_id,
            role=OrganizationMembershipRole.ADMIN.value,
        )
    )
    return organization


def add_member(
    *,
    organization_id: str,
    caller_user_id: str,
    new_member_user_id: str,
    role: str,
    org_repo: OrganizationRepoPort,
) -> OrganizationMembership:
    """Admin-only: adds `new_member_user_id` to `organization_id` with
    the given role. Raises NotOrgAdminError if the caller isn't an admin
    member (this also covers "caller isn't a member at all", since a
    non-member has no membership row to be admin on)."""
    if org_repo.get_by_id(organization_id) is None:
        raise OrganizationNotFoundError(organization_id)

    caller_membership = org_repo.get_membership(organization_id, caller_user_id)
    if caller_membership is None or caller_membership.role != OrganizationMembershipRole.ADMIN.value:
        raise NotOrgAdminError(organization_id)

    return org_repo.add_membership(
        OrganizationMembership(
            organization_id=organization_id,
            user_id=new_member_user_id,
            role=role,
        )
    )


def require_org_member(
    *, organization_id: str, user_id: str, org_repo: OrganizationRepoPort
) -> OrganizationMembership:
    """Raises OrganizationNotFoundError / NotOrgMemberError, or returns
    the caller's membership row. Shared gate for RFP posting and
    Solution publishing — both require org membership, neither requires
    admin (CLAUDE.md build brief: "must be an OrganizationMembership
    member of the posting org")."""
    if org_repo.get_by_id(organization_id) is None:
        raise OrganizationNotFoundError(organization_id)

    membership = org_repo.get_membership(organization_id, user_id)
    if membership is None:
        raise NotOrgMemberError(organization_id)
    return membership


def create_rfp(
    *,
    organization_id: str,
    caller_user_id: str,
    title: str,
    description: str,
    budget_min: float | None,
    budget_max: float | None,
    timeline: str,
    industry: str,
    geography: str,
    resolution_mode: str,
    visibility: str,
    org_repo: OrganizationRepoPort,
    rfp_repo: RFPRepoPort,
) -> RFP:
    require_org_member(organization_id=organization_id, user_id=caller_user_id, org_repo=org_repo)

    rfp = RFP(
        organization_id=organization_id,
        title=title,
        description=description,
        budget_min=budget_min,
        budget_max=budget_max,
        timeline=timeline,
        industry=industry,
        geography=geography,
        resolution_mode=resolution_mode,
        visibility=visibility,
    )
    return rfp_repo.add(rfp)


def add_rfp_requirement(
    *,
    rfp_id: str,
    caller_user_id: str,
    attribute_key: str,
    attribute_value: str,
    weight: float,
    is_hard_constraint: bool,
    org_repo: OrganizationRepoPort,
    rfp_repo: RFPRepoPort,
) -> RFPRequirement:
    rfp = rfp_repo.get_by_id(rfp_id)
    if rfp is None:
        raise RFPNotFoundError(rfp_id)
    require_org_member(organization_id=rfp.organization_id, user_id=caller_user_id, org_repo=org_repo)

    requirement = RFPRequirement(
        rfp_id=rfp_id,
        attribute_key=attribute_key,
        attribute_value=attribute_value,
        weight=weight,
        is_hard_constraint=is_hard_constraint,
    )
    return rfp_repo.add_requirement(requirement)


def search_rfps(
    *,
    caller_user_id: str | None,
    industry: str | None,
    geography: str | None,
    resolution_mode: str | None,
    org_repo: OrganizationRepoPort,
    rfp_repo: RFPRepoPort,
) -> list[RFP]:
    """Search across both visibilities, then filters invite_only RFPs
    down to only those whose posting org the caller belongs to (build
    brief: "invite-only RFPs should not appear in a public unauthenticated
    list, only to members of the posting org for now"). An anonymous
    caller (`caller_user_id is None`) never sees invite_only RFPs."""
    all_rfps = rfp_repo.search(
        industry=industry, geography=geography, resolution_mode=resolution_mode
    )

    visible: list[RFP] = []
    member_org_ids: set[str] = set()
    for rfp in all_rfps:
        if rfp.visibility != "invite_only":
            visible.append(rfp)
            continue
        if caller_user_id is None:
            continue
        if rfp.organization_id not in member_org_ids:
            membership = org_repo.get_membership(rfp.organization_id, caller_user_id)
            if membership is not None:
                member_org_ids.add(rfp.organization_id)
        if rfp.organization_id in member_org_ids:
            visible.append(rfp)
    return visible


def create_solution(
    *,
    organization_id: str,
    caller_user_id: str,
    title: str,
    description: str,
    category_tags: list[str],
    org_repo: OrganizationRepoPort,
    solution_repo: SolutionRepoPort,
) -> Solution:
    """Publishing is ALWAYS FREE — no quota/billing check anywhere in
    this path, ever (CLAUDE.md "Monetization"). The only gate is org
    membership."""
    require_org_member(organization_id=organization_id, user_id=caller_user_id, org_repo=org_repo)

    solution = Solution(
        organization_id=organization_id,
        title=title,
        description=description,
        category_tags=category_tags,
    )
    return solution_repo.add(solution)


def add_solution_attribute(
    *,
    solution_id: str,
    caller_user_id: str,
    attribute_key: str,
    attribute_value: str,
    org_repo: OrganizationRepoPort,
    solution_repo: SolutionRepoPort,
) -> SolutionAttribute:
    solution = solution_repo.get_by_id(solution_id)
    if solution is None:
        raise SolutionNotFoundError(solution_id)
    require_org_member(
        organization_id=solution.organization_id, user_id=caller_user_id, org_repo=org_repo
    )

    attribute = SolutionAttribute(
        solution_id=solution_id,
        attribute_key=attribute_key,
        attribute_value=attribute_value,
    )
    return solution_repo.add_attribute(attribute)
