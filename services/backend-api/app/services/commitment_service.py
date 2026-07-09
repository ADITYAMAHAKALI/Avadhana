"""Commitment creation — enforces the 3-slot system.

This is THE enforcement point for CLAUDE.md's non-negotiable constraint
#1: "a user can have at most 3 ACTIVE commitments. A 4th attempt must be
hard-blocked with a clear error (409), not a soft warning." The check
below (`count_active_for_user(...) >= MAX_ACTIVE_COMMITMENTS`) is the
ONLY gate on commitment creation — there is no override flag, no admin
bypass, no "soft" path. Any future code path that creates a Commitment
row MUST go through `create_commitment()` below rather than constructing
one directly, or it silently reintroduces a way around the slot limit.
"""

from app.interfaces.repositories import CheckpointRepoPort, CommitmentRepoPort, ProblemRepoPort
from app.models.checkpoint import CheckpointEventType, CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus
from app.services.errors import AlreadyCommittedError, ProblemNotFoundError, SlotLimitExceededError

MAX_ACTIVE_COMMITMENTS = 3


def create_commitment(
    *,
    user_id: str,
    problem_id: str,
    role: str,
    specialization: str | None,
    problem_repo: ProblemRepoPort,
    commitment_repo: CommitmentRepoPort,
    checkpoint_repo: CheckpointRepoPort,
) -> Commitment:
    if problem_repo.get_by_id(problem_id) is None:
        raise ProblemNotFoundError(problem_id)

    if commitment_repo.get_active_for_user_and_problem(user_id, problem_id) is not None:
        raise AlreadyCommittedError(problem_id)

    used = commitment_repo.count_active_for_user(user_id)
    if used >= MAX_ACTIVE_COMMITMENTS:
        # Hard block — see module docstring. No exceptions, no roles that
        # skip this, ever.
        raise SlotLimitExceededError(used=used, total=MAX_ACTIVE_COMMITMENTS)

    commitment = Commitment(
        user_id=user_id,
        problem_id=problem_id,
        role=role,
        specialization=specialization,
        status=CommitmentStatus.ACTIVE.value,
    )
    commitment = commitment_repo.add(commitment)

    # Immutable audit trail starts at creation (CLAUDE.md: insert-only,
    # never updated/deleted).
    checkpoint_repo.add(
        CommitmentCheckpoint(
            commitment_id=commitment.id,
            event_type=CheckpointEventType.CREATED.value,
            note=None,
        )
    )
    return commitment
