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
from app.impl.repositories import SqlAlchemyCommitmentRepo, SqlAlchemyProblemRepo
from app.models.problem import Problem
from app.models.user import User
from app.schemas import ProblemCreateRequest, ProblemOut
from app.services.presenters import problem_to_out

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
    session: Session = Depends(get_session),
) -> list[ProblemOut]:
    problem_repo = SqlAlchemyProblemRepo(session)
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    problems = problem_repo.search(q=q, tier=tier, location=location, category=category)
    return [
        problem_to_out(p, commitment_repo.count_active_by_role_for_problem(p.id))
        for p in problems
    ]


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: str, session: Session = Depends(get_session)) -> ProblemOut:
    problem_repo = SqlAlchemyProblemRepo(session)
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    problem = problem_repo.get_by_id(problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "PROBLEM_NOT_FOUND", "message": f"No problem with id {problem_id}."},
        )
    return problem_to_out(problem, commitment_repo.count_active_by_role_for_problem(problem.id))
