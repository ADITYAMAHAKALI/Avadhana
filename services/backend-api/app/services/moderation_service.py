"""Human moderator override business logic (issue #59): hide/restore a
`FeedPost` or `Comment`, and read back the audit log for a problem.

Authorization (platform-admin-only) happens one layer up, via the
`require_platform_admin` dependency on the router — by the time these
functions run, the caller has already been verified as an admin.

Every hide/restore call does two things, always together, never one
without the other:
  1. Flips the target's denormalized `hidden` flag (fast to query, used
     by normal feed reads).
  2. Inserts a new `ModerationOverrideEvent` row (immutable audit trail
     — never updated or deleted, per CLAUDE.md's immutability rule).
"""

from app.interfaces.repositories import FeedRepoPort, ModerationRepoPort
from app.models.feed import Comment, FeedPost
from app.models.moderation import ModerationAction, ModerationOverrideEvent, ModerationTargetType
from app.services.errors import ModerationTargetNotFoundError


def _apply(
    *,
    target_type: str,
    target_id: str,
    hidden: bool,
    performed_by: str,
    reason: str | None,
    moderation_repo: ModerationRepoPort,
    set_hidden_fn,
) -> None:
    target = set_hidden_fn(target_id, hidden)
    if target is None:
        raise ModerationTargetNotFoundError(target_type, target_id)

    moderation_repo.add(
        ModerationOverrideEvent(
            target_type=target_type,
            target_id=target_id,
            action=(
                ModerationAction.HIDDEN.value if hidden else ModerationAction.RESTORED.value
            ),
            performed_by=performed_by,
            reason=reason,
        )
    )


def hide_post(
    *,
    post_id: str,
    performed_by: str,
    reason: str | None,
    feed_repo: FeedRepoPort,
    moderation_repo: ModerationRepoPort,
) -> None:
    _apply(
        target_type=ModerationTargetType.POST.value,
        target_id=post_id,
        hidden=True,
        performed_by=performed_by,
        reason=reason,
        moderation_repo=moderation_repo,
        set_hidden_fn=feed_repo.set_post_hidden,
    )


def restore_post(
    *,
    post_id: str,
    performed_by: str,
    reason: str | None,
    feed_repo: FeedRepoPort,
    moderation_repo: ModerationRepoPort,
) -> None:
    _apply(
        target_type=ModerationTargetType.POST.value,
        target_id=post_id,
        hidden=False,
        performed_by=performed_by,
        reason=reason,
        moderation_repo=moderation_repo,
        set_hidden_fn=feed_repo.set_post_hidden,
    )


def hide_comment(
    *,
    comment_id: str,
    performed_by: str,
    reason: str | None,
    feed_repo: FeedRepoPort,
    moderation_repo: ModerationRepoPort,
) -> None:
    _apply(
        target_type=ModerationTargetType.COMMENT.value,
        target_id=comment_id,
        hidden=True,
        performed_by=performed_by,
        reason=reason,
        moderation_repo=moderation_repo,
        set_hidden_fn=feed_repo.set_comment_hidden,
    )


def restore_comment(
    *,
    comment_id: str,
    performed_by: str,
    reason: str | None,
    feed_repo: FeedRepoPort,
    moderation_repo: ModerationRepoPort,
) -> None:
    _apply(
        target_type=ModerationTargetType.COMMENT.value,
        target_id=comment_id,
        hidden=False,
        performed_by=performed_by,
        reason=reason,
        moderation_repo=moderation_repo,
        set_hidden_fn=feed_repo.set_comment_hidden,
    )
