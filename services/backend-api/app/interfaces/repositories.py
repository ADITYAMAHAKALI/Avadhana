"""Repository ports (interfaces) for persistence.

Defined as `typing.Protocol`s, matching the convention in
`app/interfaces/health.py`. Each port is deliberately narrow — just the
operations the service layer actually needs — so a fake in-memory
implementation (see `tests/unit/fakes.py`) can satisfy it in a handful of
lines, with no database involved.

Kept in one file (rather than one-file-per-port like `health.py`/
`service_info.py`) because these ports are small, numerous, and used
together constantly by the service layer — splitting each into its own
file would mean six near-empty files with heavy cross-import churn as
the domain model settles. Revisit if any single port grows complex
enough to warrant its own module.

These ports operate on the ORM model types directly (`app.models.*`)
rather than separate "domain" dataclasses. For a service this size, a
parallel domain-model layer would be pure ceremony — the ORM models
already have no FastAPI/HTTP dependencies, so they're perfectly fine to
pass through the service layer. Fakes construct the same ORM classes
in-memory (never touching a DB session), which is enough to keep the
service layer unit-testable per the brief.
"""

from typing import Protocol

from app.models.checkpoint import CommitmentCheckpoint
from app.models.commitment import Commitment
from app.models.feed import Comment, FeedPost
from app.models.marketplace.organization import Organization, OrganizationMembership
from app.models.marketplace.rfp import RFP, RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.models.moderation import ModerationOverrideEvent
from app.models.problem import Problem
from app.models.user import User


class UserRepoPort(Protocol):
    def get_by_id(self, user_id: str) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def add(self, user: User) -> User: ...

    def update_reputation(self, user_id: str, delta: int) -> None:
        """Apply a reputation delta. The ONLY mutation path for
        reputation — callers are checkpoint transitions, never feed
        activity (see CLAUDE.md Gamification section)."""
        ...


class ProblemRepoPort(Protocol):
    def get_by_id(self, problem_id: str) -> Problem | None: ...

    def add(self, problem: Problem) -> Problem: ...

    def search(
        self,
        q: str | None = None,
        tier: str | None = None,
        location: str | None = None,
        category: str | None = None,
    ) -> list[Problem]: ...


class CommitmentRepoPort(Protocol):
    def get_by_id(self, commitment_id: str) -> Commitment | None: ...

    def add(self, commitment: Commitment) -> Commitment: ...

    def count_active_for_user(self, user_id: str) -> int:
        """Count of the caller's ACTIVE commitments — the 3-slot gate."""
        ...

    def get_active_for_user_and_problem(
        self, user_id: str, problem_id: str
    ) -> Commitment | None:
        """Used for both the ALREADY_COMMITTED check on creation and the
        commitment-gated-voice check on feed writes."""
        ...

    def list_active_for_user(self, user_id: str) -> list[Commitment]: ...

    def list_for_user_with_checkpoint_history(self, user_id: str) -> list[Commitment]:
        """Commitments that have at least one non-`created` checkpoint
        (resolved/abandoned/continued) — backs commitment-history."""
        ...

    def count_active_by_role_for_problem(self, problem_id: str) -> dict[str, int]:
        """Live thinker/actor/backer counts for a problem."""
        ...


class CheckpointRepoPort(Protocol):
    def add(self, checkpoint: CommitmentCheckpoint) -> CommitmentCheckpoint:
        """Insert-only — never update or delete (CLAUDE.md immutability
        rule for audit trails)."""
        ...

    def list_for_commitment(self, commitment_id: str) -> list[CommitmentCheckpoint]: ...

    def has_non_created_event(self, commitment_id: str) -> bool:
        """True once a commitment has been through resolve/abandon/
        continue — used to route it into commitment-history."""
        ...


class FeedRepoPort(Protocol):
    def add_post(self, post: FeedPost) -> FeedPost: ...

    def list_posts_for_problem(
        self, problem_id: str, *, include_hidden: bool = False
    ) -> list[FeedPost]:
        """Newest first. `include_hidden=False` (the default, used by
        every normal read endpoint) filters `hidden=True` rows out at
        the query level — hidden content never round-trips to a normal
        caller. Only the admin-only moderation-log / future "view as
        admin" paths pass `include_hidden=True`."""
        ...

    def get_post(self, post_id: str) -> FeedPost | None:
        """Unfiltered — callers that need to check/act on a post
        (including moderation) must be able to fetch it regardless of
        its hidden state."""
        ...

    def set_post_hidden(self, post_id: str, hidden: bool) -> FeedPost | None:
        """Flips the denormalized current-state flag. Always called
        alongside a `ModerationOverrideEvent` insert (see
        `app/services/moderation_service.py`) — never on its own."""
        ...

    def add_comment(self, comment: Comment) -> Comment: ...

    def list_comments_for_post(
        self, post_id: str, *, include_hidden: bool = False
    ) -> list[Comment]:
        """See `list_posts_for_problem` for the `include_hidden`
        contract."""
        ...

    def get_comment(self, comment_id: str) -> Comment | None:
        """Unfiltered, same rationale as `get_post`."""
        ...

    def set_comment_hidden(self, comment_id: str, hidden: bool) -> Comment | None:
        """See `set_post_hidden`."""
        ...

    def toggle_like(self, post_id: str, user_id: str) -> int:
        """Toggle: inserts a like if none exists for (post, user), else
        removes it. Returns the post's new total like count."""
        ...

    def like_count(self, post_id: str) -> int: ...


class ModerationRepoPort(Protocol):
    def add(self, event: ModerationOverrideEvent) -> ModerationOverrideEvent:
        """Insert-only — never update or delete (CLAUDE.md immutability
        rule for audit trails), matching CheckpointRepoPort.add."""
        ...

    def list_for_problem(self, problem_id: str) -> list[ModerationOverrideEvent]:
        """Every override event for posts/comments belonging to this
        problem, newest first — backs
        `GET /problems/{problem_id}/moderation-log`."""
        ...


class OrganizationRepoPort(Protocol):
    def get_by_id(self, organization_id: str) -> Organization | None: ...

    def add(self, organization: Organization) -> Organization: ...

    def add_membership(self, membership: OrganizationMembership) -> OrganizationMembership: ...

    def get_membership(
        self, organization_id: str, user_id: str
    ) -> OrganizationMembership | None:
        """The membership row (if any) for this user in this
        organization — used both for the member-only gate on
        RFP/Solution creation and the admin-only gate on adding new
        members."""
        ...

    def list_memberships_for_organization(
        self, organization_id: str
    ) -> list[OrganizationMembership]: ...

    def list_organizations_for_user(self, user_id: str) -> list[Organization]:
        """Every Organization the given user holds a membership in —
        backs `GET /marketplace/organizations/mine`."""
        ...


class RFPRepoPort(Protocol):
    def get_by_id(self, rfp_id: str) -> RFP | None: ...

    def add(self, rfp: RFP) -> RFP: ...

    def search(
        self,
        *,
        industry: str | None = None,
        geography: str | None = None,
        resolution_mode: str | None = None,
        visibility: str | None = None,
    ) -> list[RFP]:
        """Unfiltered by caller identity — visibility (invite-only vs.
        public) is enforced by the service layer, which knows the
        caller's org memberships, not by this port."""
        ...

    def add_requirement(self, requirement: RFPRequirement) -> RFPRequirement: ...

    def list_requirements(self, rfp_id: str) -> list[RFPRequirement]: ...


class SolutionRepoPort(Protocol):
    def get_by_id(self, solution_id: str) -> Solution | None: ...

    def add(self, solution: Solution) -> Solution: ...

    def search(
        self,
        *,
        category_tag: str | None = None,
        organization_id: str | None = None,
        status: str | None = None,
    ) -> list[Solution]: ...

    def add_attribute(self, attribute: SolutionAttribute) -> SolutionAttribute: ...

    def list_attributes(self, solution_id: str) -> list[SolutionAttribute]: ...


__all__ = [
    "UserRepoPort",
    "ProblemRepoPort",
    "CommitmentRepoPort",
    "CheckpointRepoPort",
    "FeedRepoPort",
    "ModerationRepoPort",
    "OrganizationRepoPort",
    "RFPRepoPort",
    "SolutionRepoPort",
]
