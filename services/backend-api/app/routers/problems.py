"""Problem creation (authenticated) and discovery (public).

GET endpoints here require no auth at all, by design — problems are
searchable/readable by anyone (CLAUDE.md "Problem Creation": "Problem
becomes searchable immediately"; "External Discovery & Visitor Flow":
share links must work for non-members). Only POST (creation) requires a
JWT.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.db.session import get_session
from app.impl.repositories import (
    SqlAlchemyCheckpointRepo,
    SqlAlchemyCommitmentRepo,
    SqlAlchemyProblemRepo,
    SqlAlchemyResolutionObjectionRepo,
)
from app.interfaces.repositories import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.models.problem import Problem
from app.models.user import User
from app.schemas import ProblemCreateRequest, ProblemOut, ResolutionObjectionOut
from app.services.errors import AlreadyObjectedError, NoActiveResolutionWindowError
from app.services.errors import NotCommittedError as NotCommittedServiceError
from app.services.presenters import problem_to_out, resolution_objection_to_out
from app.services.problem_lifecycle_service import compute_resolution_status, raise_objection

router = APIRouter(prefix="/problems", tags=["problems"])


@router.post("", response_model=ProblemOut, status_code=status.HTTP_201_CREATED)
def create_problem(
    body: ProblemCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ProblemOut:
    problem_repo = SqlAlchemyProblemRepo(session)
    problem = Problem(
        title=body.title,
        summary=body.summary,
        location=body.location,
        category=body.category,
        tier=body.tier,
        created_by_user_id=current_user.id,
    )
    problem = problem_repo.add(problem)
    # Freshly created: no commitments yet, so all role counts are 0.
    return problem_to_out(problem, role_counts={})


@router.get("", response_model=list[ProblemOut])
def list_problems(
    q: str | None = Query(default=None),
    tier: str | None = Query(default=None),
    location: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[ProblemOut]:
    problem_repo = SqlAlchemyProblemRepo(session)
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    checkpoint_repo = SqlAlchemyCheckpointRepo(session)
    objection_repo = SqlAlchemyResolutionObjectionRepo(session)
    problems = problem_repo.search(
        q=q, tier=tier, location=location, category=category, limit=limit, offset=offset
    )
    # Batched (issue #77 N+1 fix): one grouped query across every
    # returned problem id instead of one `count_active_by_role_for_problem`
    # round trip per problem.
    role_counts = commitment_repo.count_active_by_role_for_problems([p.id for p in problems])
    # Resolution status (issue #100) is NOT batched the same way yet —
    # each problem still gets its own `compute_resolution_status` call
    # (a handful of small queries per problem). Acceptable at SLC v1
    # scale (same reasoning as the rest of this module's compute-on-read
    # approach); revisit with a batched variant if `GET /problems`
    # list sizes grow large enough for this to matter.
    return [
        problem_to_out(
            p,
            role_counts.get(p.id, {}),
            compute_resolution_status(
                p,
                commitment_repo=commitment_repo,
                checkpoint_repo=checkpoint_repo,
                objection_repo=objection_repo,
            ),
        )
        for p in problems
    ]


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: str, session: Session = Depends(get_session)) -> ProblemOut:
    problem_repo = SqlAlchemyProblemRepo(session)
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    checkpoint_repo = SqlAlchemyCheckpointRepo(session)
    objection_repo = SqlAlchemyResolutionObjectionRepo(session)
    problem = problem_repo.get_by_id(problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "PROBLEM_NOT_FOUND", "message": f"No problem with id {problem_id}."},
        )
    resolution_status = compute_resolution_status(
        problem,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
        objection_repo=objection_repo,
    )
    return problem_to_out(
        problem, commitment_repo.count_active_by_role_for_problem(problem.id), resolution_status
    )


@router.post(
    "/{problem_id}/objections",
    response_model=ResolutionObjectionOut,
    status_code=status.HTTP_201_CREATED,
)
def raise_objection_route(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResolutionObjectionOut:
    """Raise one objection against the current resolution-claim episode
    on a problem (issue #100). Committed-member-gated, but deliberately
    NOT via `require_committed_member` (which only recognizes ACTIVE
    commitments) — a member whose own checkpoint just flipped their
    commitment to RESOLVED must still be able to object to a DIFFERENT
    member's resolve claim, so this uses the same "currently committed
    = ACTIVE or RESOLVED" concept the status computation itself uses.
    See `app.services.problem_lifecycle_service.raise_objection`.
    """
    problem_repo = SqlAlchemyProblemRepo(session)
    problem = problem_repo.get_by_id(problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "PROBLEM_NOT_FOUND", "message": f"No problem with id {problem_id}."},
        )

    try:
        objection = raise_objection(
            problem=problem,
            caller_user_id=current_user.id,
            commitment_repo=SqlAlchemyCommitmentRepo(session),
            checkpoint_repo=SqlAlchemyCheckpointRepo(session),
            objection_repo=SqlAlchemyResolutionObjectionRepo(session),
        )
    except NotCommittedServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_COMMITTED", "message": str(exc)},
        ) from exc
    except NoActiveResolutionWindowError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "NO_ACTIVE_RESOLUTION_WINDOW", "message": str(exc)},
        ) from exc
    except AlreadyObjectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "ALREADY_OBJECTED", "message": str(exc)},
        ) from exc

    return resolution_objection_to_out(objection)
