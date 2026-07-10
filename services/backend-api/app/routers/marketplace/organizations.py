"""Organization creation and membership management (GitHub issue #63).

All endpoints here require auth — unlike civic Problems (public read),
Organizations are B2B/B2G account objects with no equivalent "discovery
is public" requirement in the build brief, so every route (including
reads) depends on `get_current_user`. Business rules (creator becomes
first admin, admin-only member-add) live in
`app/services/marketplace_service.py`; this router is a thin HTTP
translation layer, same convention as `app/routers/commitments.py`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyOrganizationRepo
from app.models.user import User
from app.schemas_marketplace import (
    OrganizationCreateRequest,
    OrganizationMemberAddRequest,
    OrganizationMembershipOut,
    OrganizationOut,
)
from app.services.errors import NotOrgAdminError, OrganizationNotFoundError
from app.services.marketplace_service import add_member, create_organization
from app.services.presenters_marketplace import membership_to_out, organization_to_out

router = APIRouter(prefix="/marketplace/organizations", tags=["marketplace-organizations"])


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization_route(
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
    org_repo = SqlAlchemyOrganizationRepo(session)
    organization = org_repo.get_by_id(organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ORGANIZATION_NOT_FOUND",
                "message": f"No organization with id {organization_id}.",
            },
        )
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
    org_repo = SqlAlchemyOrganizationRepo(session)
    if org_repo.get_by_id(organization_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ORGANIZATION_NOT_FOUND",
                "message": f"No organization with id {organization_id}.",
            },
        )
    memberships = org_repo.list_memberships_for_organization(organization_id)
    return [membership_to_out(m) for m in memberships]
