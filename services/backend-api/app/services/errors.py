"""Domain-level exceptions raised by the service layer.

Routers catch these and translate them into the exact HTTP status codes
and error-body shapes required by the API contract. Keeping these as
plain exceptions (not HTTPException) is what makes the service layer
importable and testable with zero FastAPI dependency (see tests/unit/).
"""


class SlotLimitExceededError(Exception):
    def __init__(self, used: int, total: int):
        self.used = used
        self.total = total
        super().__init__(
            f"Cannot commit: all {total} focus slots are in use ({used}/{total})."
        )


class AlreadyCommittedError(Exception):
    def __init__(self, problem_id: str):
        self.problem_id = problem_id
        super().__init__(f"Already have an active commitment on problem {problem_id}.")


class ProblemNotFoundError(Exception):
    def __init__(self, problem_id: str):
        self.problem_id = problem_id
        super().__init__(f"Problem {problem_id} not found.")


class CommitmentNotFoundError(Exception):
    def __init__(self, commitment_id: str):
        self.commitment_id = commitment_id
        super().__init__(f"Commitment {commitment_id} not found.")


class NotCommitmentOwnerError(Exception):
    def __init__(self, commitment_id: str):
        self.commitment_id = commitment_id
        super().__init__(f"Caller does not own commitment {commitment_id}.")


class LockActiveError(Exception):
    """Raised when a checkpoint is attempted before the 90-day lock
    expires. This check has NO bypass anywhere in the codebase — see
    app/services/checkpoint_service.py."""

    def __init__(self, days_remaining: int):
        self.days_remaining = days_remaining
        super().__init__(
            f"Commitment is locked for {days_remaining} more day(s); "
            "the 90-day commitment lock has no early-exit path."
        )


class CommitmentNotActiveError(Exception):
    """Raised when a checkpoint action is attempted on a commitment
    that's already terminal (resolved/abandoned) — no un-resolving or
    un-abandoning."""

    def __init__(self, commitment_id: str, status: str):
        self.commitment_id = commitment_id
        self.status = status
        super().__init__(f"Commitment {commitment_id} is already {status}.")


class NotCommittedError(Exception):
    """Raised by the commitment-gated-voice check — caller is
    authenticated but has no ACTIVE commitment on the target problem."""

    def __init__(self, problem_id: str):
        self.problem_id = problem_id
        super().__init__(
            "Only committed members can post here. Commit a focus slot to "
            "this problem to participate."
        )


class ModerationTargetNotFoundError(Exception):
    """Raised when a hide/restore is attempted on a post/comment id that
    doesn't exist, or (for comments) doesn't belong to the given post, or
    (for either) doesn't belong to the given problem."""

    def __init__(self, target_type: str, target_id: str):
        self.target_type = target_type
        self.target_id = target_id
        super().__init__(f"No {target_type} with id {target_id} on this problem.")
