"""In-memory fakes satisfying the repository ports in
`app.interfaces.repositories`, for fast unit tests of the service layer
with no database at all.

Each fake stores rows in a plain dict/list and implements just enough
query logic to support the service-layer functions under test — no
SQL, no ORM session, no Postgres/SQLite. This is what lets
`tests/unit/test_*.py` run in milliseconds and exercise the 3-slot and
90-day-lock constraints directly.
"""

from app.models.checkpoint import CheckpointEventType, CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus
from app.models.feed import Comment, FeedPost, PostLike
from app.models.problem import Problem
from app.models.user import User


class FakeUserRepo:
    def __init__(self):
        self.users: dict[str, User] = {}

    def get_by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        for u in self.users.values():
            if u.email == email:
                return u
        return None

    def add(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def update_reputation(self, user_id: str, delta: int) -> None:
        user = self.users.get(user_id)
        if user is not None:
            user.reputation += delta


class FakeProblemRepo:
    def __init__(self):
        self.problems: dict[str, Problem] = {}

    def get_by_id(self, problem_id: str) -> Problem | None:
        return self.problems.get(problem_id)

    def add(self, problem: Problem) -> Problem:
        self.problems[problem.id] = problem
        return problem

    def search(self, q=None, tier=None, location=None, category=None) -> list[Problem]:
        results = list(self.problems.values())
        if q:
            results = [p for p in results if q.lower() in p.title.lower() or q.lower() in p.summary.lower()]
        if tier:
            results = [p for p in results if p.tier == tier]
        if location:
            results = [p for p in results if location.lower() in p.location.lower()]
        if category:
            results = [p for p in results if category.lower() in p.category.lower()]
        return results


class FakeCommitmentRepo:
    def __init__(self, checkpoint_repo: "FakeCheckpointRepo | None" = None):
        self.commitments: dict[str, Commitment] = {}
        # Optional link to a FakeCheckpointRepo so
        # list_for_user_with_checkpoint_history can be answered without a
        # real join — mirrors the real SqlAlchemyCommitmentRepo's JOIN
        # against commitment_checkpoints. Tests exercising history should
        # construct both fakes together and pass checkpoint_repo in.
        self._checkpoint_repo = checkpoint_repo

    def get_by_id(self, commitment_id: str) -> Commitment | None:
        return self.commitments.get(commitment_id)

    def add(self, commitment: Commitment) -> Commitment:
        self.commitments[commitment.id] = commitment
        return commitment

    def count_active_for_user(self, user_id: str) -> int:
        return sum(
            1
            for c in self.commitments.values()
            if c.user_id == user_id and c.status == CommitmentStatus.ACTIVE.value
        )

    def get_active_for_user_and_problem(self, user_id: str, problem_id: str) -> Commitment | None:
        for c in self.commitments.values():
            if (
                c.user_id == user_id
                and c.problem_id == problem_id
                and c.status == CommitmentStatus.ACTIVE.value
            ):
                return c
        return None

    def list_active_for_user(self, user_id: str) -> list[Commitment]:
        return [
            c
            for c in self.commitments.values()
            if c.user_id == user_id and c.status == CommitmentStatus.ACTIVE.value
        ]

    def list_for_user_with_checkpoint_history(self, user_id: str) -> list[Commitment]:
        if self._checkpoint_repo is None:
            raise RuntimeError(
                "FakeCommitmentRepo needs a checkpoint_repo to answer "
                "list_for_user_with_checkpoint_history — construct it as "
                "FakeCommitmentRepo(checkpoint_repo=...)."
            )
        return [
            c
            for c in self.commitments.values()
            if c.user_id == user_id and self._checkpoint_repo.has_non_created_event(c.id)
        ]

    def count_active_by_role_for_problem(self, problem_id: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self.commitments.values():
            if c.problem_id == problem_id and c.status == CommitmentStatus.ACTIVE.value:
                counts[c.role] = counts.get(c.role, 0) + 1
        return counts


class FakeCheckpointRepo:
    def __init__(self):
        self.checkpoints: list[CommitmentCheckpoint] = []

    def add(self, checkpoint: CommitmentCheckpoint) -> CommitmentCheckpoint:
        self.checkpoints.append(checkpoint)
        return checkpoint

    def list_for_commitment(self, commitment_id: str) -> list[CommitmentCheckpoint]:
        return [c for c in self.checkpoints if c.commitment_id == commitment_id]

    def has_non_created_event(self, commitment_id: str) -> bool:
        return any(
            c.commitment_id == commitment_id and c.event_type != CheckpointEventType.CREATED.value
            for c in self.checkpoints
        )


class FakeFeedRepo:
    def __init__(self):
        self.posts: dict[str, FeedPost] = {}
        self.comments: dict[str, Comment] = {}
        self.likes: list[PostLike] = []

    def add_post(self, post: FeedPost) -> FeedPost:
        self.posts[post.id] = post
        return post

    def list_posts_for_problem(self, problem_id: str) -> list[FeedPost]:
        posts = [p for p in self.posts.values() if p.problem_id == problem_id]
        return sorted(posts, key=lambda p: p.created_at, reverse=True)

    def get_post(self, post_id: str) -> FeedPost | None:
        return self.posts.get(post_id)

    def add_comment(self, comment: Comment) -> Comment:
        self.comments[comment.id] = comment
        return comment

    def list_comments_for_post(self, post_id: str) -> list[Comment]:
        comments = [c for c in self.comments.values() if c.post_id == post_id]
        return sorted(comments, key=lambda c: c.created_at)

    def toggle_like(self, post_id: str, user_id: str) -> int:
        existing = next(
            (like for like in self.likes if like.post_id == post_id and like.user_id == user_id),
            None,
        )
        if existing is not None:
            self.likes.remove(existing)
        else:
            self.likes.append(PostLike(post_id=post_id, user_id=user_id))
        return self.like_count(post_id)

    def like_count(self, post_id: str) -> int:
        return sum(1 for like in self.likes if like.post_id == post_id)
