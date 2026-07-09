"""SQLAlchemy-backed implementations of the repository ports in
`app.interfaces.repositories`.

Each class wraps a `Session` (request-scoped, injected via
`app.db.session.get_session`) and structurally satisfies the
corresponding Protocol — no inheritance required (PEP 544), matching the
convention in `app/impl/health.py`.

These are thin: query construction only, no business rules. Slot
counting, lock enforcement, and reputation deltas live in
`app/services/*`, which depend on these ports — never on SQLAlchemy
directly — so the service layer stays testable against fakes.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.checkpoint import CheckpointEventType, CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus
from app.models.feed import Comment, FeedPost, PostLike
from app.models.problem import Problem
from app.models.user import User


class SqlAlchemyUserRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: str) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.session.execute(stmt).scalar_one_or_none()

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_reputation(self, user_id: str, delta: int) -> None:
        user = self.session.get(User, user_id)
        if user is None:
            return
        user.reputation += delta
        self.session.commit()


class SqlAlchemyProblemRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, problem_id: str) -> Problem | None:
        return self.session.get(Problem, problem_id)

    def add(self, problem: Problem) -> Problem:
        self.session.add(problem)
        self.session.commit()
        self.session.refresh(problem)
        return problem

    def search(
        self,
        q: str | None = None,
        tier: str | None = None,
        location: str | None = None,
        category: str | None = None,
    ) -> list[Problem]:
        stmt = select(Problem)
        if q:
            like = f"%{q}%"
            stmt = stmt.where((Problem.title.ilike(like)) | (Problem.summary.ilike(like)))
        if tier:
            stmt = stmt.where(Problem.tier == tier)
        if location:
            stmt = stmt.where(Problem.location.ilike(f"%{location}%"))
        if category:
            stmt = stmt.where(Problem.category.ilike(f"%{category}%"))
        stmt = stmt.order_by(Problem.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())


class SqlAlchemyCommitmentRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, commitment_id: str) -> Commitment | None:
        return self.session.get(Commitment, commitment_id)

    def add(self, commitment: Commitment) -> Commitment:
        self.session.add(commitment)
        self.session.commit()
        self.session.refresh(commitment)
        return commitment

    def count_active_for_user(self, user_id: str) -> int:
        stmt = select(func.count()).select_from(Commitment).where(
            Commitment.user_id == user_id,
            Commitment.status == CommitmentStatus.ACTIVE.value,
        )
        return self.session.execute(stmt).scalar_one()

    def get_active_for_user_and_problem(
        self, user_id: str, problem_id: str
    ) -> Commitment | None:
        stmt = select(Commitment).where(
            Commitment.user_id == user_id,
            Commitment.problem_id == problem_id,
            Commitment.status == CommitmentStatus.ACTIVE.value,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_active_for_user(self, user_id: str) -> list[Commitment]:
        stmt = select(Commitment).where(
            Commitment.user_id == user_id,
            Commitment.status == CommitmentStatus.ACTIVE.value,
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_for_user_with_checkpoint_history(self, user_id: str) -> list[Commitment]:
        stmt = (
            select(Commitment)
            .join(
                CommitmentCheckpoint,
                CommitmentCheckpoint.commitment_id == Commitment.id,
            )
            .where(
                Commitment.user_id == user_id,
                CommitmentCheckpoint.event_type != CheckpointEventType.CREATED.value,
            )
            .distinct()
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_active_by_role_for_problem(self, problem_id: str) -> dict[str, int]:
        stmt = (
            select(Commitment.role, func.count())
            .where(
                Commitment.problem_id == problem_id,
                Commitment.status == CommitmentStatus.ACTIVE.value,
            )
            .group_by(Commitment.role)
        )
        rows = self.session.execute(stmt).all()
        return {role: count for role, count in rows}


class SqlAlchemyCheckpointRepo:
    def __init__(self, session: Session):
        self.session = session

    def add(self, checkpoint: CommitmentCheckpoint) -> CommitmentCheckpoint:
        self.session.add(checkpoint)
        self.session.commit()
        self.session.refresh(checkpoint)
        return checkpoint

    def list_for_commitment(self, commitment_id: str) -> list[CommitmentCheckpoint]:
        stmt = (
            select(CommitmentCheckpoint)
            .where(CommitmentCheckpoint.commitment_id == commitment_id)
            .order_by(CommitmentCheckpoint.occurred_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def has_non_created_event(self, commitment_id: str) -> bool:
        stmt = select(func.count()).select_from(CommitmentCheckpoint).where(
            CommitmentCheckpoint.commitment_id == commitment_id,
            CommitmentCheckpoint.event_type != CheckpointEventType.CREATED.value,
        )
        return self.session.execute(stmt).scalar_one() > 0


class SqlAlchemyFeedRepo:
    def __init__(self, session: Session):
        self.session = session

    def add_post(self, post: FeedPost) -> FeedPost:
        self.session.add(post)
        self.session.commit()
        self.session.refresh(post)
        return post

    def list_posts_for_problem(self, problem_id: str) -> list[FeedPost]:
        stmt = (
            select(FeedPost)
            .where(FeedPost.problem_id == problem_id)
            .order_by(FeedPost.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_post(self, post_id: str) -> FeedPost | None:
        return self.session.get(FeedPost, post_id)

    def add_comment(self, comment: Comment) -> Comment:
        self.session.add(comment)
        self.session.commit()
        self.session.refresh(comment)
        return comment

    def list_comments_for_post(self, post_id: str) -> list[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def toggle_like(self, post_id: str, user_id: str) -> int:
        stmt = select(PostLike).where(
            PostLike.post_id == post_id, PostLike.user_id == user_id
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            self.session.delete(existing)
        else:
            self.session.add(PostLike(post_id=post_id, user_id=user_id))
        self.session.commit()
        return self.like_count(post_id)

    def like_count(self, post_id: str) -> int:
        stmt = select(func.count()).select_from(PostLike).where(PostLike.post_id == post_id)
        return self.session.execute(stmt).scalar_one()
