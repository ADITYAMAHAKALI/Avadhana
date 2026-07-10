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
from app.models.marketplace.billing import BillingEvent
from app.models.marketplace.matching import MatchRun, SolutionMatch
from app.models.marketplace.organization import Organization, OrganizationMembership
from app.models.marketplace.rfp import RFP, RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.models.moderation import ModerationOverrideEvent
from app.models.problem import Problem
from app.models.user import User

# Pagination defaults/cap shared by every list/search port + router in
# this module (issue #76). A single source of truth so "default 20, cap
# 100" doesn't drift between e.g. problems and RFPs.
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100


class UserRepoPort(Protocol):
    def get_by_id(self, user_id: str) -> User | None: ...

    def get_by_ids(self, user_ids: list[str]) -> dict[str, User]:
        """Batch lookup — one `WHERE id IN (...)` query instead of N
        `get_by_id` round trips. Used to resolve feed post/comment
        authors without an N+1 (issue #77). Returns a dict keyed by id;
        unknown ids are simply absent, mirroring `get_by_id`'s `None`
        for a miss."""
        ...

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
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[Problem]:
        """`limit`/`offset` applied at the SQL level (issue #76), never
        as a Python-level slice of an already-fetched full result."""
        ...


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

    def count_active_by_role_for_problems(
        self, problem_ids: list[str]
    ) -> dict[str, dict[str, int]]:
        """Batched form of `count_active_by_role_for_problem` — one
        grouped query across all given problem ids instead of one query
        per problem (issue #77 N+1 fix on `GET /problems`). Returns a
        dict keyed by problem id; a problem id with no active commitments
        at all is simply absent (caller should treat a missing key the
        same as an empty role-count dict, same as `{}` from the
        single-problem method)."""
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
        self,
        problem_id: str,
        *,
        include_hidden: bool = False,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[FeedPost]:
        """Newest first, `limit`/`offset` applied at the SQL level (issue
        #76). `include_hidden=False` (the default, used by every normal
        read endpoint) filters `hidden=True` rows out at the query level
        — hidden content never round-trips to a normal caller. Only the
        admin-only moderation-log / future "view as admin" paths pass
        `include_hidden=True`."""
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
        self,
        post_id: str,
        *,
        include_hidden: bool = False,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[Comment]:
        """See `list_posts_for_problem` for the `include_hidden` and
        `limit`/`offset` contract."""
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

    def like_counts_for_posts(self, post_ids: list[str]) -> dict[str, int]:
        """Batched form of `like_count` — one grouped `COUNT(*) ...
        GROUP BY post_id` query across all given post ids instead of one
        query per post (issue #77 N+1 fix on `GET /problems/{id}/posts`).
        A post id with zero likes is simply absent from the returned
        dict (caller should treat a missing key as 0, same as
        `like_count` returning 0 for a post with no likes)."""
        ...


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

    def increment_rfp_quota_used(self, organization_id: str) -> Organization:
        """Atomically bumps `rfp_free_quota_used` by 1 and returns the
        updated Organization row — the ONLY mutation path for that
        counter (issue #71 paywall gate). Called once per successful RFP
        creation, from `app.services.marketplace_service.create_rfp`."""
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
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[RFP]:
        """Unfiltered by caller identity — visibility (invite-only vs.
        public) is enforced by the service layer, which knows the
        caller's org memberships, not by this port. `limit`/`offset`
        applied at the SQL level (issue #76); note the service layer
        (`search_rfps`) further filters invite-only rows out in Python
        *after* this call, so the page the caller ultimately sees can be
        smaller than `limit` — see that function's docstring."""
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
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[Solution]:
        """`organization_id`/`status` are pushed into SQL and paginated
        there directly. `category_tag` is NOT — `category_tags` is a
        generic JSON list column (see `app.models.marketplace.solution`)
        with no containment operator that works identically on both
        SQLite (this repo's integration test backend) and Postgres
        (dev/prod), so it's applied in Python after fetching, same as
        before this port grew pagination (issue #76's audit flagged this
        as a related, pre-existing bug). To keep `limit`/`offset`
        meaningful *after* that Python filter, the implementation fetches
        a larger internal superset from the DB, filters by
        `category_tag` in Python, and only then applies `limit`/`offset`
        to the filtered list — see `SqlAlchemySolutionRepo.search` for
        the exact mechanics."""
        ...

    def add_attribute(self, attribute: SolutionAttribute) -> SolutionAttribute: ...

    def list_attributes(self, solution_id: str) -> list[SolutionAttribute]: ...


class BillingEventRepoPort(Protocol):
    def add(self, event: BillingEvent) -> BillingEvent:
        """Insert-only — never update or delete (CLAUDE.md immutability
        rule for audit trails), matching CheckpointRepoPort.add /
        ModerationRepoPort.add."""
        ...

    def list_for_organization(self, organization_id: str) -> list[BillingEvent]:
        """Newest first — backs
        `GET /marketplace/organizations/{id}/billing-events`."""
        ...


class MatchRepoPort(Protocol):
    """Backend-api's side of the RRF matching engine (issue #68) — only
    what the HTTP surface needs: create the `MatchRun` row a trigger
    request enqueues (status=pending) and read back the most recent
    completed run's ranked matches. The job itself (writing `SolutionMatch`
    rows, transitioning `MatchRun.status`) runs in
    `services/ai-coordinator-worker`, deliberately NOT through this repo
    port — see that service's `impl/marketplace_matching_job.py` module
    docstring for why it uses SQLAlchemy Core against the same tables
    instead of importing this ORM-based port from a separate,
    independently-deployable service."""

    def add_match_run(self, match_run: MatchRun) -> MatchRun:
        """Insert-only from backend-api's perspective — the trigger
        endpoint creates exactly one `pending` row per trigger request.
        Only the worker job (via its own SQLAlchemy Core connection, not
        this port) ever transitions a run's status afterward."""
        ...

    def get_latest_completed_run(self, rfp_id: str) -> MatchRun | None:
        """Most recent (`started_at` descending) `MatchRun` with
        `status == "completed"` for this RFP — backs
        `GET /marketplace/rfps/{rfp_id}/matches`. Returns None if no run
        has ever completed (e.g. never triggered, or still running/failed)."""
        ...

    def list_matches_for_run(self, match_run_id: str) -> list[SolutionMatch]:
        """All `SolutionMatch` rows for one run, ordered by `rank`
        ascending (best match first)."""
        ...


__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "MAX_PAGE_LIMIT",
    "UserRepoPort",
    "ProblemRepoPort",
    "CommitmentRepoPort",
    "CheckpointRepoPort",
    "FeedRepoPort",
    "ModerationRepoPort",
    "OrganizationRepoPort",
    "RFPRepoPort",
    "SolutionRepoPort",
    "BillingEventRepoPort",
    "MatchRepoPort",
]
