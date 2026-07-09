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

    def list_posts_for_problem(self, problem_id: str) -> list[FeedPost]:
        """Newest first."""
        ...

    def get_post(self, post_id: str) -> FeedPost | None: ...

    def add_comment(self, comment: Comment) -> Comment: ...

    def list_comments_for_post(self, post_id: str) -> list[Comment]: ...

    def toggle_like(self, post_id: str, user_id: str) -> int:
        """Toggle: inserts a like if none exists for (post, user), else
        removes it. Returns the post's new total like count."""
        ...

    def like_count(self, post_id: str) -> int: ...


__all__ = [
    "UserRepoPort",
    "ProblemRepoPort",
    "CommitmentRepoPort",
    "CheckpointRepoPort",
    "FeedRepoPort",
]
