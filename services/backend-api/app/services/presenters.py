"""ORM model -> API schema translation.

Centralizing this here (rather than scattering `.model_validate(...)`
calls with ad-hoc field mapping across routers) keeps derived fields
(initials, avatarColor, roleLabel, timeAgo, dayInCycle) computed exactly
once, consistently, per CLAUDE.md's requirement that things like
`timeAgo` are "precomputed relative-time string server-side ... don't
leave this to the client."
"""

from app.core.presentation import avatar_color_for_user_id, initials_for_name, time_ago
from app.core.time import utcnow
from app.models.checkpoint import CommitmentCheckpoint
from app.models.commitment import Commitment
from app.models.feed import Comment, FeedPost
from app.models.moderation import ModerationOverrideEvent
from app.models.problem import Problem
from app.models.user import User
from app.schemas import (
    CheckpointOut,
    CommentOut,
    CommitmentOut,
    CommittedProblemOut,
    FeedPostOut,
    ModerationOverrideEventOut,
    ProblemOut,
    UserOut,
)

CYCLE_LENGTH_DAYS = 90


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        initials=initials_for_name(user.name),
        location=user.location,
        member_since=user.created_at,
        reputation=user.reputation,
        avatar_color=avatar_color_for_user_id(user.id),
    )


def problem_to_out(problem: Problem, role_counts: dict[str, int]) -> ProblemOut:
    return ProblemOut(
        id=problem.id,
        title=problem.title,
        summary=problem.summary,
        location=problem.location,
        category=problem.category,
        tier=problem.tier,
        created_at=problem.created_at,
        thinker_count=role_counts.get("thinker", 0),
        actor_count=role_counts.get("actor", 0),
        backer_count=role_counts.get("backer", 0),
    )


def commitment_to_out(commitment: Commitment) -> CommitmentOut:
    return CommitmentOut(
        id=commitment.id,
        problem_id=commitment.problem_id,
        role=commitment.role,
        specialization=commitment.specialization,
        status=commitment.status,
        started_at=commitment.started_at,
        lock_expires_at=commitment.lock_expires_at,
        created_at=commitment.created_at,
    )


def checkpoint_to_out(checkpoint: CommitmentCheckpoint) -> CheckpointOut:
    return CheckpointOut(
        id=checkpoint.id,
        commitment_id=checkpoint.commitment_id,
        event_type=checkpoint.event_type,
        occurred_at=checkpoint.occurred_at,
        note=checkpoint.note,
    )


def committed_problem_to_out(commitment: Commitment) -> CommittedProblemOut:
    now = utcnow()
    started_at = commitment.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=now.tzinfo)
    day_in_cycle = max(0, (now - started_at).days)
    return CommittedProblemOut(
        problem_id=commitment.problem_id,
        role=commitment.role,
        specialization=commitment.specialization,
        day_in_cycle=day_in_cycle,
        cycle_length_days=CYCLE_LENGTH_DAYS,
        # Task board is out of scope for SLC v1 (see build brief's
        # "Explicit scope boundaries") — always null until it exists.
        next_task=None,
    )


_ROLE_LABELS = {"thinker": "Thinker", "actor": "Actor", "backer": "Backer"}


def role_label(role: str) -> str:
    return _ROLE_LABELS.get(role, role.capitalize())


def post_to_out(post: FeedPost, author: User, like_count: int) -> FeedPostOut:
    return FeedPostOut(
        id=post.id,
        author_initials=initials_for_name(author.name),
        author_name=author.name,
        author_color=avatar_color_for_user_id(author.id),
        role_label=role_label(post.author_role),
        time_ago=time_ago(post.created_at),
        body=post.body,
        like_count=like_count,
    )


def comment_to_out(comment: Comment, author: User) -> CommentOut:
    return CommentOut(
        id=comment.id,
        post_id=comment.post_id,
        author_initials=initials_for_name(author.name),
        author_name=author.name,
        author_color=avatar_color_for_user_id(author.id),
        role_label=role_label(comment.author_role),
        time_ago=time_ago(comment.created_at),
        body=comment.body,
    )


def moderation_event_to_out(event: ModerationOverrideEvent) -> ModerationOverrideEventOut:
    return ModerationOverrideEventOut(
        id=event.id,
        target_type=event.target_type,
        target_id=event.target_id,
        action=event.action,
        performed_by=event.performed_by,
        reason=event.reason,
        occurred_at=event.occurred_at,
    )
