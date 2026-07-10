"""Community-promotion bridge: RFP -> civic Problem (GitHub issue #70).

`POST /marketplace/rfps/{rfp_id}/promote` is the one deliberate bridge
between the Marketplace and the civic commitment-first platform
(CLAUDE.md "Solution Marketplace Architecture": "The one deliberate
bridge between the two systems is the 'promote to community' flow ...
once an RFP crosses that bridge, the resulting civic Problem plays by
the civic rules like any other").

Separate file from `app/routers/marketplace/rfps.py` (rather than an
extra route added to that router) for the same reason `matches.py` is
its own file alongside `matching.py`: this endpoint straddles two
otherwise-independent product surfaces (Marketplace + civic Problems) and
reaches into `app.impl.repositories.SqlAlchemyProblemRepo` /
`app.services.presenters.problem_to_out`, imports that the rest of
`app/routers/marketplace/` deliberately has no reason to carry.

Response shape: the created civic `Problem` (via the existing
`problem_to_out` presenter, the same one `POST /problems` returns),
not the RFP. The RFP's own updated representation (with
`promotedProblemId` now set) is already retrievable via the existing
`GET /marketplace/rfps/{rfp_id}` — no need to duplicate it here, and the
Problem is the actual thing that was just created and is what the caller
most likely wants to act on next (e.g. redirect to its page).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.db.session import get_session
from app.impl.repositories import (
    SqlAlchemyOrganizationRepo,
    SqlAlchemyProblemRepo,
    SqlAlchemyRFPRepo,
)
from app.models.user import User
from app.schemas import ProblemOut
from app.schemas_marketplace import RFPPromoteRequest
from app.services.errors import (
    NotOrgMemberError,
    RFPAlreadyPromotedError,
    RFPNotCommunityResolvableError,
    RFPNotFoundError,
)
from app.services.marketplace_service import promote_rfp_to_problem
from app.services.presenters import problem_to_out

router = APIRouter(prefix="/marketplace/rfps", tags=["marketplace-promotion"])


@router.post(
    "/{rfp_id}/promote",
    response_model=ProblemOut,
    status_code=status.HTTP_201_CREATED,
)
def promote_rfp_route(
    rfp_id: str,
    body: RFPPromoteRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ProblemOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp_repo = SqlAlchemyRFPRepo(session)
    problem_repo = SqlAlchemyProblemRepo(session)
    try:
        problem = promote_rfp_to_problem(
            rfp_id=rfp_id,
            caller_user_id=current_user.id,
            tier=body.tier,
            org_repo=org_repo,
            rfp_repo=rfp_repo,
            problem_repo=problem_repo,
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
    except RFPNotCommunityResolvableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "RFP_NOT_COMMUNITY_RESOLVABLE", "message": str(exc)},
        ) from exc
    except RFPAlreadyPromotedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "RFP_ALREADY_PROMOTED", "message": str(exc)},
        ) from exc

    # Freshly created: no commitments yet, so all role counts are 0 —
    # same convention as POST /problems (app/routers/problems.py).
    return problem_to_out(problem, role_counts={})
