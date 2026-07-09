"""Commitment creation and checkpoint transitions.

Thin translation layer only: the actual enforcement of the 3-slot limit
(app.services.commitment_service) and the 90-day lock
(app.services.checkpoint_service) lives in the service layer, which this
router calls and then maps domain exceptions to the exact HTTP status
codes/bodies the API contract specifies.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.db.session import get_session
from app.impl.repositories import (
    SqlAlchemyCheckpointRepo,
    SqlAlchemyCommitmentRepo,
    SqlAlchemyProblemRepo,
    SqlAlchemyUserRepo,
)
from app.models.user import User
from app.schemas import (
    CheckpointOut,
    CheckpointRequest,
    CommitmentCreateRequest,
    CommitmentOut,
)
from app.services.checkpoint_service import apply_checkpoint
from app.services.commitment_service import create_commitment
from app.services.errors import (
    AlreadyCommittedError,
    CommitmentNotActiveError,
    CommitmentNotFoundError,
    LockActiveError,
    NotCommitmentOwnerError,
    ProblemNotFoundError,
    SlotLimitExceededError,
)
from app.services.presenters import checkpoint_to_out, commitment_to_out

router = APIRouter(tags=["commitments"])


@router.post(
    "/problems/{problem_id}/commitments",
    response_model=CommitmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_commitment_route(
    problem_id: str,
    body: CommitmentCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CommitmentOut:
    try:
        commitment = create_commitment(
            user_id=current_user.id,
            problem_id=problem_id,
            role=body.role,
            specialization=body.specialization,
            problem_repo=SqlAlchemyProblemRepo(session),
            commitment_repo=SqlAlchemyCommitmentRepo(session),
            checkpoint_repo=SqlAlchemyCheckpointRepo(session),
        )
    except ProblemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "PROBLEM_NOT_FOUND", "message": str(exc)},
        ) from exc
    except AlreadyCommittedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "ALREADY_COMMITTED", "message": str(exc)},
        ) from exc
    except SlotLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "SLOT_LIMIT_EXCEEDED",
                "message": str(exc),
                "used": exc.used,
                "total": exc.total,
            },
        ) from exc

    return commitment_to_out(commitment)


@router.post("/commitments/{commitment_id}/checkpoint", response_model=CommitmentOut)
def checkpoint_route(
    commitment_id: str,
    body: CheckpointRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CommitmentOut:
    try:
        commitment = apply_checkpoint(
            commitment_id=commitment_id,
            caller_user_id=current_user.id,
            action=body.action,
            note=body.note,
            commitment_repo=SqlAlchemyCommitmentRepo(session),
            checkpoint_repo=SqlAlchemyCheckpointRepo(session),
            user_repo=SqlAlchemyUserRepo(session),
        )
    except CommitmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "COMMITMENT_NOT_FOUND", "message": str(exc)},
        ) from exc
    except NotCommitmentOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_COMMITMENT_OWNER", "message": str(exc)},
        ) from exc
    except LockActiveError as exc:
        # No bypass anywhere in the code — see
        # app.services.checkpoint_service module docstring.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "LOCK_ACTIVE",
                "message": str(exc),
                "daysRemaining": exc.days_remaining,
            },
        ) from exc
    except CommitmentNotActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "COMMITMENT_NOT_ACTIVE", "message": str(exc)},
        ) from exc

    return commitment_to_out(commitment)


@router.get("/commitments/{commitment_id}/checkpoints", response_model=list[CheckpointOut])
def list_checkpoints_route(
    commitment_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CheckpointOut]:
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    commitment = commitment_repo.get_by_id(commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "COMMITMENT_NOT_FOUND",
                "message": f"Commitment {commitment_id} not found.",
            },
        )
    if commitment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "NOT_COMMITMENT_OWNER",
                "message": "Only the commitment owner can view its checkpoints.",
            },
        )

    checkpoint_repo = SqlAlchemyCheckpointRepo(session)
    checkpoints = checkpoint_repo.list_for_commitment(commitment_id)
    return [checkpoint_to_out(c) for c in checkpoints]
