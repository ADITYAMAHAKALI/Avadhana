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

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.checkpoint import CheckpointEventType, CommitmentCheckpoint
from app.models.commitment import Commitment, CommitmentStatus
from app.models.feed import Comment, FeedPost, PostLike
from app.models.marketplace.billing import BillingEvent
from app.models.marketplace.organization import Organization, OrganizationMembership
from app.models.marketplace.rfp import RFP, RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.models.moderation import ModerationOverrideEvent, ModerationTargetType
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

    def list_posts_for_problem(
        self, problem_id: str, *, include_hidden: bool = False
    ) -> list[FeedPost]:
        stmt = select(FeedPost).where(FeedPost.problem_id == problem_id)
        if not include_hidden:
            stmt = stmt.where(FeedPost.hidden.is_(False))
        stmt = stmt.order_by(FeedPost.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def get_post(self, post_id: str) -> FeedPost | None:
        return self.session.get(FeedPost, post_id)

    def set_post_hidden(self, post_id: str, hidden: bool) -> FeedPost | None:
        post = self.session.get(FeedPost, post_id)
        if post is None:
            return None
        post.hidden = hidden
        self.session.commit()
        self.session.refresh(post)
        return post

    def add_comment(self, comment: Comment) -> Comment:
        self.session.add(comment)
        self.session.commit()
        self.session.refresh(comment)
        return comment

    def list_comments_for_post(
        self, post_id: str, *, include_hidden: bool = False
    ) -> list[Comment]:
        stmt = select(Comment).where(Comment.post_id == post_id)
        if not include_hidden:
            stmt = stmt.where(Comment.hidden.is_(False))
        stmt = stmt.order_by(Comment.created_at.asc())
        return list(self.session.execute(stmt).scalars().all())

    def get_comment(self, comment_id: str) -> Comment | None:
        return self.session.get(Comment, comment_id)

    def set_comment_hidden(self, comment_id: str, hidden: bool) -> Comment | None:
        comment = self.session.get(Comment, comment_id)
        if comment is None:
            return None
        comment.hidden = hidden
        self.session.commit()
        self.session.refresh(comment)
        return comment

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


class SqlAlchemyModerationRepo:
    def __init__(self, session: Session):
        self.session = session

    def add(self, event: ModerationOverrideEvent) -> ModerationOverrideEvent:
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_for_problem(self, problem_id: str) -> list[ModerationOverrideEvent]:
        # ModerationOverrideEvent.target_id is a polymorphic FK (post or
        # comment id, per target_type) with no DB-level foreign key
        # constraint, so "events for this problem" is answered by two
        # separate id-set lookups (post ids owned by the problem, and
        # comment ids owned by those posts) rather than a single JOIN.
        post_ids = list(
            self.session.execute(
                select(FeedPost.id).where(FeedPost.problem_id == problem_id)
            )
            .scalars()
            .all()
        )
        comment_ids: list[str] = []
        if post_ids:
            comment_ids = list(
                self.session.execute(
                    select(Comment.id).where(Comment.post_id.in_(post_ids))
                )
                .scalars()
                .all()
            )

        conditions = []
        if post_ids:
            conditions.append(
                (ModerationOverrideEvent.target_type == ModerationTargetType.POST.value)
                & (ModerationOverrideEvent.target_id.in_(post_ids))
            )
        if comment_ids:
            conditions.append(
                (ModerationOverrideEvent.target_type == ModerationTargetType.COMMENT.value)
                & (ModerationOverrideEvent.target_id.in_(comment_ids))
            )
        if not conditions:
            return []

        stmt = (
            select(ModerationOverrideEvent)
            .where(or_(*conditions))
            .order_by(ModerationOverrideEvent.occurred_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())


class SqlAlchemyOrganizationRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, organization_id: str) -> Organization | None:
        return self.session.get(Organization, organization_id)

    def add(self, organization: Organization) -> Organization:
        self.session.add(organization)
        self.session.commit()
        self.session.refresh(organization)
        return organization

    def add_membership(self, membership: OrganizationMembership) -> OrganizationMembership:
        self.session.add(membership)
        self.session.commit()
        self.session.refresh(membership)
        return membership

    def get_membership(
        self, organization_id: str, user_id: str
    ) -> OrganizationMembership | None:
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_memberships_for_organization(
        self, organization_id: str
    ) -> list[OrganizationMembership]:
        stmt = (
            select(OrganizationMembership)
            .where(OrganizationMembership.organization_id == organization_id)
            .order_by(OrganizationMembership.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_organizations_for_user(self, user_id: str) -> list[Organization]:
        stmt = (
            select(Organization)
            .join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Organization.id,
            )
            .where(OrganizationMembership.user_id == user_id)
            .order_by(Organization.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def increment_rfp_quota_used(self, organization_id: str) -> Organization:
        # session.get + attribute mutation, same read-modify-commit
        # pattern as SqlAlchemyUserRepo.update_reputation — no
        # SELECT ... FOR UPDATE here since this is a single-process
        # solo-dev deployment (see app/core/rate_limit.py's identical
        # reasoning for skipping cross-replica coordination at this
        # stage); revisit if backend-api is ever horizontally scaled.
        organization = self.session.get(Organization, organization_id)
        if organization is None:
            raise ValueError(f"Organization {organization_id} not found.")
        organization.rfp_free_quota_used += 1
        self.session.commit()
        self.session.refresh(organization)
        return organization


class SqlAlchemyRFPRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, rfp_id: str) -> RFP | None:
        return self.session.get(RFP, rfp_id)

    def add(self, rfp: RFP) -> RFP:
        self.session.add(rfp)
        self.session.commit()
        self.session.refresh(rfp)
        return rfp

    def search(
        self,
        *,
        industry: str | None = None,
        geography: str | None = None,
        resolution_mode: str | None = None,
        visibility: str | None = None,
    ) -> list[RFP]:
        stmt = select(RFP)
        if industry:
            stmt = stmt.where(RFP.industry.ilike(f"%{industry}%"))
        if geography:
            stmt = stmt.where(RFP.geography.ilike(f"%{geography}%"))
        if resolution_mode:
            stmt = stmt.where(RFP.resolution_mode == resolution_mode)
        if visibility:
            stmt = stmt.where(RFP.visibility == visibility)
        stmt = stmt.order_by(RFP.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def add_requirement(self, requirement: RFPRequirement) -> RFPRequirement:
        self.session.add(requirement)
        self.session.commit()
        self.session.refresh(requirement)
        return requirement

    def list_requirements(self, rfp_id: str) -> list[RFPRequirement]:
        stmt = (
            select(RFPRequirement)
            .where(RFPRequirement.rfp_id == rfp_id)
            .order_by(RFPRequirement.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())


class SqlAlchemySolutionRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, solution_id: str) -> Solution | None:
        return self.session.get(Solution, solution_id)

    def add(self, solution: Solution) -> Solution:
        self.session.add(solution)
        self.session.commit()
        self.session.refresh(solution)
        return solution

    def search(
        self,
        *,
        category_tag: str | None = None,
        organization_id: str | None = None,
    ) -> list[Solution]:
        stmt = select(Solution)
        if organization_id:
            stmt = stmt.where(Solution.organization_id == organization_id)
        stmt = stmt.order_by(Solution.created_at.desc())
        solutions = list(self.session.execute(stmt).scalars().all())
        if category_tag:
            # category_tags is a JSON list column — filtering by
            # membership is done in Python rather than a DB-specific JSON
            # operator, since this must work identically against both
            # SQLite (integration tests) and Postgres (dev/prod).
            solutions = [s for s in solutions if category_tag in (s.category_tags or [])]
        return solutions

    def add_attribute(self, attribute: SolutionAttribute) -> SolutionAttribute:
        self.session.add(attribute)
        self.session.commit()
        self.session.refresh(attribute)
        return attribute

    def list_attributes(self, solution_id: str) -> list[SolutionAttribute]:
        stmt = (
            select(SolutionAttribute)
            .where(SolutionAttribute.solution_id == solution_id)
            .order_by(SolutionAttribute.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())


class SqlAlchemyBillingEventRepo:
    def __init__(self, session: Session):
        self.session = session

    def add(self, event: BillingEvent) -> BillingEvent:
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_for_organization(self, organization_id: str) -> list[BillingEvent]:
        stmt = (
            select(BillingEvent)
            .where(BillingEvent.organization_id == organization_id)
            .order_by(BillingEvent.occurred_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())
