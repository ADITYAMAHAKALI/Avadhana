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
from app.models.resolution_objection import ResolutionObjection
from app.models.user import User
from app.schemas import (
    CheckpointOut,
    CommentOut,
    CommitmentOut,
    CommittedProblemOut,
    FeedPostOut,
    ModerationOverrideEventOut,
    ProblemOut,
    ResolutionObjectionOut,
    UserOut,
)
from app.services.problem_lifecycle_service import ResolutionStatus

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


def problem_to_out(
    problem: Problem,
    role_counts: dict[str, int],
    resolution_status: ResolutionStatus | None = None,
) -> ProblemOut:
    # `resolution_status` is optional so every existing call site (list/
    # detail endpoints, tests) doesn't have to be touched in lockstep;
    # a freshly-created problem (no commitments yet) has an obvious
    # default of "open" with nothing claimed, matching what
    # `compute_resolution_status` would return anyway for zero members.
    status = resolution_status or ResolutionStatus(
        status="open",
        resolved_count=0,
        total_committed=0,
        threshold=None,
        window_start=None,
        window_ends_at=None,
        objection_count=0,
    )
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
        resolution_status=status.status,
        resolved_count=status.resolved_count,
        total_committed=status.total_committed,
        resolution_threshold=status.threshold,
        resolution_window_ends_at=status.window_ends_at,
        objection_count=status.objection_count,
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
        commitment_id=commitment.id,
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
        parent_comment_id=comment.parent_comment_id,
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


def resolution_objection_to_out(objection: ResolutionObjection) -> ResolutionObjectionOut:
    return ResolutionObjectionOut(
        id=objection.id,
        problem_id=objection.problem_id,
        objecting_user_id=objection.objecting_user_id,
        raised_at=objection.raised_at,
    )
