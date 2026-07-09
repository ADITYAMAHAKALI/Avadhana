"""Current-user endpoints: profile, focus slots, committed problems,
commitment history. All authenticated (there is no "view another user's
profile" endpoint yet — out of scope for SLC v1, not mentioned in the
API contract).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.db.session import get_session
from app.impl.repositories import (
    SqlAlchemyCheckpointRepo,
    SqlAlchemyCommitmentRepo,
    SqlAlchemyProblemRepo,
)
from app.models.user import User
from app.schemas import CommitmentHistoryOut, CommittedProblemOut, FocusSlotsOut, UserOut
from app.services.commitment_service import MAX_ACTIVE_COMMITMENTS
from app.services.history_service import latest_history_status_and_note
from app.services.presenters import committed_problem_to_out, user_to_out

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return user_to_out(current_user)


@router.get("/focus-slots", response_model=FocusSlotsOut)
def get_focus_slots(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FocusSlotsOut:
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    used = commitment_repo.count_active_for_user(current_user.id)
    return FocusSlotsOut(used=used, total=MAX_ACTIVE_COMMITMENTS)


@router.get("/committed-problems", response_model=list[CommittedProblemOut])
def get_committed_problems(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CommittedProblemOut]:
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    active = commitment_repo.list_active_for_user(current_user.id)
    return [committed_problem_to_out(c) for c in active]


@router.get("/commitment-history", response_model=list[CommitmentHistoryOut])
def get_commitment_history(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CommitmentHistoryOut]:
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    checkpoint_repo = SqlAlchemyCheckpointRepo(session)
    problem_repo = SqlAlchemyProblemRepo(session)

    commitments = commitment_repo.list_for_user_with_checkpoint_history(current_user.id)

    out: list[CommitmentHistoryOut] = []
    for commitment in commitments:
        checkpoints = checkpoint_repo.list_for_commitment(commitment.id)
        result = latest_history_status_and_note(commitment, checkpoints)
        if result is None:
            continue
        status_value, note = result
        problem = problem_repo.get_by_id(commitment.problem_id)
        problem_title = problem.title if problem is not None else "(deleted problem)"
        out.append(
            CommitmentHistoryOut(
                problem_title=problem_title,
                role=commitment.role,
                status=status_value,
                note=note,
            )
        )
    return out
