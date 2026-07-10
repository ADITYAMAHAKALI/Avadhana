"""Organization creation and membership management (GitHub issue #63),
plus the billing-events ledger (GitHub issue #71).

All endpoints here require auth — unlike civic Problems (public read),
Organizations are B2B/B2G account objects with no equivalent "discovery
is public" requirement in the build brief, so every route (including
reads) depends on `get_current_user`. Business rules (creator becomes
first admin, admin-only member-add, admin-only billing-events read) live
in `app/services/marketplace_service.py`; this router is a thin HTTP
translation layer, same convention as `app/routers/commitments.py`.

`POST /marketplace/organizations` additionally carries a per-user rate
limit (GitHub issue #73 — "Free-tier abuse safeguards"): CLAUDE.md
"Solution Marketplace Architecture" -> "Open questions" flags that
"nothing yet stops an Organization from creating many Organizations to
keep resetting the 100-RFP free quota." This is a PARTIAL mitigation,
not a solved problem — see `ORGANIZATION_CREATE_RATE_LIMIT`'s docstring
in `app/core/rate_limit.py` for the honest limits: it slows down a
single account minting Organizations in a burst, but does nothing to
stop an abuser from signing up multiple accounts (each with their own
fresh rate-limit bucket) and creating one Organization per account. A
real fix needs account-level abuse signals (e.g. reputation, email
verification, manual review past some Organization-count threshold) that
don't exist yet anywhere in this codebase — out of scope for this pass,
flagged honestly rather than silently declared "handled".
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.rate_limit import ORGANIZATION_CREATE_RATE_LIMIT, _user_or_ip_key, limiter
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyBillingEventRepo, SqlAlchemyOrganizationRepo
from app.models.user import User
from app.schemas_marketplace import (
    BillingEventOut,
    OrganizationCreateRequest,
    OrganizationMemberAddRequest,
    OrganizationMembershipOut,
    OrganizationOut,
)
from app.services.errors import NotOrgAdminError, NotOrgMemberError, OrganizationNotFoundError
from app.services.marketplace_service import (
    add_member,
    create_organization,
    list_billing_events,
    require_org_member,
)
from app.services.presenters_marketplace import (
    billing_event_to_out,
    membership_to_out,
    organization_to_out,
)

router = APIRouter(prefix="/marketplace/organizations", tags=["marketplace-organizations"])


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(ORGANIZATION_CREATE_RATE_LIMIT, key_func=_user_or_ip_key)
def create_organization_route(
    request: Request,
    body: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OrganizationOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    organization = create_organization(
        name=body.name, creator_user_id=current_user.id, org_repo=org_repo
    )
    return organization_to_out(organization)


@router.get("/mine", response_model=list[OrganizationOut])
def list_my_organizations_route(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[OrganizationOut]:
    org_repo = SqlAlchemyOrganizationRepo(session)
    organizations = org_repo.list_organizations_for_user(current_user.id)
    return [organization_to_out(o) for o in organizations]


@router.get("/{organization_id}", response_model=OrganizationOut)
def get_organization_route(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OrganizationOut:
    """Membership-gated, same shielding convention as invite-only RFPs
    (`rfps.py`): a non-member gets the same 404 an actually-missing
    Organization would, rather than a 403 that would confirm the
    Organization exists. Fixes GitHub issue #84 (IDOR — this endpoint
    previously returned any Organization's billing status/quota to any
    authenticated user regardless of membership)."""
    org_repo = SqlAlchemyOrganizationRepo(session)
    try:
        require_org_member(
            organization_id=organization_id, user_id=current_user.id, org_repo=org_repo
        )
    except (OrganizationNotFoundError, NotOrgMemberError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ORGANIZATION_NOT_FOUND",
                "message": f"No organization with id {organization_id}.",
            },
        ) from exc
    organization = org_repo.get_by_id(organization_id)
    return organization_to_out(organization)


@router.post(
    "/{organization_id}/members",
    response_model=OrganizationMembershipOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member_route(
    organization_id: str,
    body: OrganizationMemberAddRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OrganizationMembershipOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    try:
        membership = add_member(
            organization_id=organization_id,
            caller_user_id=current_user.id,
            new_member_user_id=body.user_id,
            role=body.role,
            org_repo=org_repo,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "ORGANIZATION_NOT_FOUND", "message": str(exc)},
        ) from exc
    except NotOrgAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_ORG_ADMIN", "message": str(exc)},
        ) from exc

    return membership_to_out(membership)


@router.get("/{organization_id}/members", response_model=list[OrganizationMembershipOut])
def list_members_route(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[OrganizationMembershipOut]:
    """Membership-gated — see `get_organization_route`'s docstring.
    Fixes GitHub issue #84 (IDOR — this endpoint previously returned any
    Organization's full member roster, user IDs + roles, to any
    authenticated user regardless of membership)."""
    org_repo = SqlAlchemyOrganizationRepo(session)
    try:
        require_org_member(
            organization_id=organization_id, user_id=current_user.id, org_repo=org_repo
        )
    except (OrganizationNotFoundError, NotOrgMemberError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ORGANIZATION_NOT_FOUND",
                "message": f"No organization with id {organization_id}.",
            },
        ) from exc
    memberships = org_repo.list_memberships_for_organization(organization_id)
    return [membership_to_out(m) for m in memberships]


@router.get("/{organization_id}/billing-events", response_model=list[BillingEventOut])
def list_billing_events_route(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[BillingEventOut]:
    org_repo = SqlAlchemyOrganizationRepo(session)
    billing_repo = SqlAlchemyBillingEventRepo(session)
    try:
        events = list_billing_events(
            organization_id=organization_id,
            caller_user_id=current_user.id,
            org_repo=org_repo,
            billing_repo=billing_repo,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "ORGANIZATION_NOT_FOUND", "message": str(exc)},
        ) from exc
    except NotOrgAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_ORG_ADMIN", "message": str(exc)},
        ) from exc

    return [billing_event_to_out(e) for e in events]
