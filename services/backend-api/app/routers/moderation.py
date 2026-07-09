"""Human moderator override baseline (issue #59).

No AI moderation exists yet (deferred, post-v1) — this is the baseline
*human* lever CLAUDE.md calls for: "Moderators (initially you) can
always override auto-blocks and reverse decisions. This is critical
during beta." All write endpoints here are gated by
`require_platform_admin` (app.core.auth_dependencies) — there is no
self-service way to become an admin (see app/models/user.py docstring).

`GET /problems/{problem_id}/moderation-log` is the transparency piece
CLAUDE.md calls for ("Committed members can view moderation logs for
their problem"). For this baseline pass it's scoped to admin-only
rather than all committed members — widening it to committed members is
a natural, explicitly-flagged follow-up, not done here because the
committed-member-scoped read path doesn't exist for this kind of
cross-post/comment aggregate view yet and deserves its own design pass.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import require_platform_admin
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyFeedRepo, SqlAlchemyModerationRepo
from app.models.user import User
from app.schemas import ModerationActionRequest, ModerationOverrideEventOut
from app.services.errors import ModerationTargetNotFoundError
from app.services.moderation_service import (
    hide_comment,
    hide_post,
    restore_comment,
    restore_post,
)
from app.services.presenters import moderation_event_to_out

router = APIRouter(tags=["moderation"])


def _get_post_or_404(feed_repo: SqlAlchemyFeedRepo, problem_id: str, post_id: str):
    post = feed_repo.get_post(post_id)
    if post is None or post.problem_id != problem_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "POST_NOT_FOUND",
                "message": f"No post with id {post_id} on this problem.",
            },
        )
    return post


def _get_comment_or_404(feed_repo: SqlAlchemyFeedRepo, post_id: str, comment_id: str):
    comment = feed_repo.get_comment(comment_id)
    if comment is None or comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "COMMENT_NOT_FOUND",
                "message": f"No comment with id {comment_id} on this post.",
            },
        )
    return comment


@router.post(
    "/problems/{problem_id}/posts/{post_id}/moderation/hide",
    status_code=status.HTTP_204_NO_CONTENT,
)
def hide_post_route(
    problem_id: str,
    post_id: str,
    body: ModerationActionRequest,
    admin: User = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> None:
    feed_repo = SqlAlchemyFeedRepo(session)
    moderation_repo = SqlAlchemyModerationRepo(session)
    _get_post_or_404(feed_repo, problem_id, post_id)
    try:
        hide_post(
            post_id=post_id,
            performed_by=admin.id,
            reason=body.reason,
            feed_repo=feed_repo,
            moderation_repo=moderation_repo,
        )
    except ModerationTargetNotFoundError as exc:  # pragma: no cover - guarded above
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "POST_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/problems/{problem_id}/posts/{post_id}/moderation/restore",
    status_code=status.HTTP_204_NO_CONTENT,
)
def restore_post_route(
    problem_id: str,
    post_id: str,
    body: ModerationActionRequest,
    admin: User = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> None:
    feed_repo = SqlAlchemyFeedRepo(session)
    moderation_repo = SqlAlchemyModerationRepo(session)
    _get_post_or_404(feed_repo, problem_id, post_id)
    try:
        restore_post(
            post_id=post_id,
            performed_by=admin.id,
            reason=body.reason,
            feed_repo=feed_repo,
            moderation_repo=moderation_repo,
        )
    except ModerationTargetNotFoundError as exc:  # pragma: no cover - guarded above
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "POST_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/problems/{problem_id}/posts/{post_id}/comments/{comment_id}/moderation/hide",
    status_code=status.HTTP_204_NO_CONTENT,
)
def hide_comment_route(
    problem_id: str,
    post_id: str,
    comment_id: str,
    body: ModerationActionRequest,
    admin: User = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> None:
    feed_repo = SqlAlchemyFeedRepo(session)
    moderation_repo = SqlAlchemyModerationRepo(session)
    _get_post_or_404(feed_repo, problem_id, post_id)
    _get_comment_or_404(feed_repo, post_id, comment_id)
    try:
        hide_comment(
            comment_id=comment_id,
            performed_by=admin.id,
            reason=body.reason,
            feed_repo=feed_repo,
            moderation_repo=moderation_repo,
        )
    except ModerationTargetNotFoundError as exc:  # pragma: no cover - guarded above
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "COMMENT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/problems/{problem_id}/posts/{post_id}/comments/{comment_id}/moderation/restore",
    status_code=status.HTTP_204_NO_CONTENT,
)
def restore_comment_route(
    problem_id: str,
    post_id: str,
    comment_id: str,
    body: ModerationActionRequest,
    admin: User = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> None:
    feed_repo = SqlAlchemyFeedRepo(session)
    moderation_repo = SqlAlchemyModerationRepo(session)
    _get_post_or_404(feed_repo, problem_id, post_id)
    _get_comment_or_404(feed_repo, post_id, comment_id)
    try:
        restore_comment(
            comment_id=comment_id,
            performed_by=admin.id,
            reason=body.reason,
            feed_repo=feed_repo,
            moderation_repo=moderation_repo,
        )
    except ModerationTargetNotFoundError as exc:  # pragma: no cover - guarded above
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "COMMENT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.get(
    "/problems/{problem_id}/moderation-log",
    response_model=list[ModerationOverrideEventOut],
)
def moderation_log_route(
    problem_id: str,
    admin: User = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> list[ModerationOverrideEventOut]:
    moderation_repo = SqlAlchemyModerationRepo(session)
    events = moderation_repo.list_for_problem(problem_id)
    return [moderation_event_to_out(e) for e in events]
