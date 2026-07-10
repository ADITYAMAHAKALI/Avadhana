"""Solution publishing, attributes, and search (GitHub issue #65).

Publishing a Solution requires the caller to be an OrganizationMembership
member of the provider org — enforced in
`app/services/marketplace_service.py`. Unlike RFP posting, this path has
NO quota/billing check anywhere, ever (CLAUDE.md "Monetization": "Solution
publishing: always free"). Reading/searching Solutions is public — supply
-side listings are the provider-acquisition/lead-gen surface, so there's
no invite-only concept here (unlike RFPs).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyOrganizationRepo, SqlAlchemySolutionRepo
from app.interfaces.repositories import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.models.user import User
from app.schemas_marketplace import (
    SolutionAttributeCreateRequest,
    SolutionAttributeOut,
    SolutionCreateRequest,
    SolutionOut,
)
from app.services.errors import NotOrgMemberError, OrganizationNotFoundError, SolutionNotFoundError
from app.services.marketplace_service import add_solution_attribute, create_solution
from app.services.presenters_marketplace import solution_attribute_to_out, solution_to_out

router = APIRouter(prefix="/marketplace/solutions", tags=["marketplace-solutions"])


@router.post("", response_model=SolutionOut, status_code=status.HTTP_201_CREATED)
def create_solution_route(
    body: SolutionCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SolutionOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    solution_repo = SqlAlchemySolutionRepo(session)
    try:
        solution = create_solution(
            organization_id=body.organization_id,
            caller_user_id=current_user.id,
            title=body.title,
            description=body.description,
            category_tags=body.category_tags,
            org_repo=org_repo,
            solution_repo=solution_repo,
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

    return solution_to_out(solution)


@router.get("", response_model=list[SolutionOut])
def search_solutions_route(
    category_tag: str | None = Query(default=None, alias="categoryTag"),
    organization_id: str | None = Query(default=None, alias="organizationId"),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[SolutionOut]:
    solution_repo = SqlAlchemySolutionRepo(session)
    solutions = solution_repo.search(
        category_tag=category_tag, organization_id=organization_id, limit=limit, offset=offset
    )
    return [solution_to_out(s) for s in solutions]


@router.get("/{solution_id}", response_model=SolutionOut)
def get_solution_route(solution_id: str, session: Session = Depends(get_session)) -> SolutionOut:
    solution_repo = SqlAlchemySolutionRepo(session)
    solution = solution_repo.get_by_id(solution_id)
    if solution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SOLUTION_NOT_FOUND", "message": f"No solution with id {solution_id}."},
        )
    return solution_to_out(solution)


@router.post(
    "/{solution_id}/attributes",
    response_model=SolutionAttributeOut,
    status_code=status.HTTP_201_CREATED,
)
def add_solution_attribute_route(
    solution_id: str,
    body: SolutionAttributeCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SolutionAttributeOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    solution_repo = SqlAlchemySolutionRepo(session)
    try:
        attribute = add_solution_attribute(
            solution_id=solution_id,
            caller_user_id=current_user.id,
            attribute_key=body.attribute_key,
            attribute_value=body.attribute_value,
            org_repo=org_repo,
            solution_repo=solution_repo,
        )
    except SolutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SOLUTION_NOT_FOUND", "message": str(exc)},
        ) from exc
    except NotOrgMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_ORG_MEMBER", "message": str(exc)},
        ) from exc

    return solution_attribute_to_out(attribute)


@router.get("/{solution_id}/attributes", response_model=list[SolutionAttributeOut])
def list_solution_attributes_route(
    solution_id: str, session: Session = Depends(get_session)
) -> list[SolutionAttributeOut]:
    solution_repo = SqlAlchemySolutionRepo(session)
    if solution_repo.get_by_id(solution_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SOLUTION_NOT_FOUND", "message": f"No solution with id {solution_id}."},
        )
    attributes = solution_repo.list_attributes(solution_id)
    return [solution_attribute_to_out(a) for a in attributes]
