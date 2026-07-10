"""RFP posting, requirements, and search (GitHub issue #64).

Posting an RFP (and attaching requirements to it) requires the caller to
be an OrganizationMembership member of the posting org — enforced in
`app/services/marketplace_service.py`, not here. Reading a single RFP or
searching the RFP list is public (no 401 on GET), matching the civic
Problem router's "discovery is public" convention — EXCEPT invite-only
RFPs, which only members of the posting org can see (build brief: "keep
it simple: invite_only visible only to org members"). Search therefore
needs to know who's asking (if anyone) without *requiring* auth, so this
module defines its own optional-auth dependency rather than reusing
`get_current_user` (which 401s on a missing token).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyOrganizationRepo, SqlAlchemyRFPRepo
from app.models.user import User
from app.schemas_marketplace import (
    RFPCreateRequest,
    RFPOut,
    RFPRequirementCreateRequest,
    RFPRequirementOut,
)
from app.services.errors import NotOrgMemberError, OrganizationNotFoundError, RFPNotFoundError
from app.services.marketplace_service import add_rfp_requirement, create_rfp, search_rfps
from app.services.presenters_marketplace import rfp_requirement_to_out, rfp_to_out

router = APIRouter(prefix="/marketplace/rfps", tags=["marketplace-rfps"])

# Same HTTPBearer(auto_error=False) primitive as
# app.core.auth_dependencies, but resolved to `user_id | None` rather
# than raising 401 — search/get here must work for anonymous visitors
# too, just with invite-only RFPs filtered out for them.
_bearer_scheme = HTTPBearer(auto_error=False)


def _optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    if credentials is None or not credentials.credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except InvalidTokenError:
        return None


@router.post("", response_model=RFPOut, status_code=status.HTTP_201_CREATED)
def create_rfp_route(
    body: RFPCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RFPOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp_repo = SqlAlchemyRFPRepo(session)
    try:
        rfp = create_rfp(
            organization_id=body.organization_id,
            caller_user_id=current_user.id,
            title=body.title,
            description=body.description,
            budget_min=body.budget_min,
            budget_max=body.budget_max,
            timeline=body.timeline,
            industry=body.industry,
            geography=body.geography,
            resolution_mode=body.resolution_mode,
            visibility=body.visibility,
            org_repo=org_repo,
            rfp_repo=rfp_repo,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "ORGANIZATION_NOT_FOUND", "message": str(exc)},
        ) from exc
    except NotOrgMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_ORG_MEMBER", "message": str(exc)},
        ) from exc

    return rfp_to_out(rfp)


@router.get("", response_model=list[RFPOut])
def search_rfps_route(
    industry: str | None = Query(default=None),
    geography: str | None = Query(default=None),
    resolution_mode: str | None = Query(default=None, alias="resolutionMode"),
    caller_user_id: str | None = Depends(_optional_user_id),
    session: Session = Depends(get_session),
) -> list[RFPOut]:
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp_repo = SqlAlchemyRFPRepo(session)
    rfps = search_rfps(
        caller_user_id=caller_user_id,
        industry=industry,
        geography=geography,
        resolution_mode=resolution_mode,
        org_repo=org_repo,
        rfp_repo=rfp_repo,
    )
    return [rfp_to_out(r) for r in rfps]


@router.get("/{rfp_id}", response_model=RFPOut)
def get_rfp_route(
    rfp_id: str,
    caller_user_id: str | None = Depends(_optional_user_id),
    session: Session = Depends(get_session),
) -> RFPOut:
    rfp_repo = SqlAlchemyRFPRepo(session)
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp = rfp_repo.get_by_id(rfp_id)
    if rfp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RFP_NOT_FOUND", "message": f"No RFP with id {rfp_id}."},
        )
    if rfp.visibility == "invite_only":
        member = (
            caller_user_id is not None
            and org_repo.get_membership(rfp.organization_id, caller_user_id) is not None
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "RFP_NOT_FOUND", "message": f"No RFP with id {rfp_id}."},
            )
    return rfp_to_out(rfp)


@router.post(
    "/{rfp_id}/requirements",
    response_model=RFPRequirementOut,
    status_code=status.HTTP_201_CREATED,
)
def add_rfp_requirement_route(
    rfp_id: str,
    body: RFPRequirementCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RFPRequirementOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp_repo = SqlAlchemyRFPRepo(session)
    try:
        requirement = add_rfp_requirement(
            rfp_id=rfp_id,
            caller_user_id=current_user.id,
            attribute_key=body.attribute_key,
            attribute_value=body.attribute_value,
            weight=body.weight,
            is_hard_constraint=body.is_hard_constraint,
            org_repo=org_repo,
            rfp_repo=rfp_repo,
        )
    except RFPNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RFP_NOT_FOUND", "message": str(exc)},
        ) from exc
    except NotOrgMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_ORG_MEMBER", "message": str(exc)},
        ) from exc

    return rfp_requirement_to_out(requirement)


@router.get("/{rfp_id}/requirements", response_model=list[RFPRequirementOut])
def list_rfp_requirements_route(
    rfp_id: str,
    caller_user_id: str | None = Depends(_optional_user_id),
    session: Session = Depends(get_session),
) -> list[RFPRequirementOut]:
    rfp_repo = SqlAlchemyRFPRepo(session)
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp = rfp_repo.get_by_id(rfp_id)
    if rfp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RFP_NOT_FOUND", "message": f"No RFP with id {rfp_id}."},
        )
    if rfp.visibility == "invite_only":
        member = (
            caller_user_id is not None
            and org_repo.get_membership(rfp.organization_id, caller_user_id) is not None
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "RFP_NOT_FOUND", "message": f"No RFP with id {rfp_id}."},
            )
    requirements = rfp_repo.list_requirements(rfp_id)
    return [rfp_requirement_to_out(r) for r in requirements]
