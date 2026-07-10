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


# --- Marketplace (issues #63, #64, #65) ------------------------------------


class OrganizationNotFoundError(Exception):
    def __init__(self, organization_id: str):
        self.organization_id = organization_id
        super().__init__(f"Organization {organization_id} not found.")


class NotOrgMemberError(Exception):
    """Raised when a caller with no OrganizationMembership on the given
    Organization attempts an action that requires membership (posting an
    RFP, publishing a Solution)."""

    def __init__(self, organization_id: str):
        self.organization_id = organization_id
        super().__init__(
            f"Caller is not a member of organization {organization_id}."
        )


class NotOrgAdminError(Exception):
    """Raised when a caller with a non-admin (or no) membership attempts
    an admin-only action (adding a new member)."""

    def __init__(self, organization_id: str):
        self.organization_id = organization_id
        super().__init__(
            f"Caller is not an admin of organization {organization_id}."
        )


class RFPNotFoundError(Exception):
    def __init__(self, rfp_id: str):
        self.rfp_id = rfp_id
        super().__init__(f"RFP {rfp_id} not found.")


class SolutionNotFoundError(Exception):
    def __init__(self, solution_id: str):
        self.solution_id = solution_id
        super().__init__(f"Solution {solution_id} not found.")


class RFPNotCommunityResolvableError(Exception):
    """Raised when promotion is attempted on an RFP whose
    `resolution_mode` is `marketplace`-only (issue #70). Only `community`
    and `both` RFPs may be promoted into a civic Problem — see CLAUDE.md
    "Solution Marketplace Architecture" -> "Two resolution modes per
    RFP"."""

    def __init__(self, rfp_id: str, resolution_mode: str):
        self.rfp_id = rfp_id
        self.resolution_mode = resolution_mode
        super().__init__(
            f"RFP {rfp_id} has resolution_mode={resolution_mode!r}; only "
            "'community' or 'both' RFPs can be promoted into a civic Problem."
        )


class RFPAlreadyPromotedError(Exception):
    """Raised when promotion is attempted a second time on an RFP whose
    `promoted_problem_id` is already set — an RFP may only be promoted
    once, never creating a second, duplicate Problem."""

    def __init__(self, rfp_id: str, promoted_problem_id: str):
        self.rfp_id = rfp_id
        self.promoted_problem_id = promoted_problem_id
        super().__init__(
            f"RFP {rfp_id} was already promoted to Problem {promoted_problem_id}."
        )
