"""Unit tests for the human moderator override baseline (issue #59):
hide/restore business logic against fakes.

Authorization (platform-admin-only) is a FastAPI dependency
(`require_platform_admin`) covered by integration tests
(tests/integration/test_api_moderation.py); here we test the underlying
flag-flip + audit-event-insert behavior in isolation.
"""

import pytest

from app.models.feed import Comment, FeedPost
from app.models.moderation import ModerationAction, ModerationTargetType
from app.services.errors import ModerationTargetNotFoundError
from app.services.moderation_service import (
    hide_comment,
    hide_post,
    restore_comment,
    restore_post,
)
from tests.unit.fakes import FakeFeedRepo, FakeModerationRepo


def _post(problem_id="problem-1", **kwargs) -> FeedPost:
    return FeedPost(
        problem_id=problem_id,
        author_user_id="author-1",
        author_role="thinker",
        body="Some post body",
        **kwargs,
    )


def _comment(post_id, **kwargs) -> Comment:
    return Comment(
        post_id=post_id,
        author_user_id="author-1",
        author_role="thinker",
        body="Some comment body",
        **kwargs,
    )


def test_hide_post_flips_flag_and_writes_audit_event():
    feed_repo = FakeFeedRepo()
    moderation_repo = FakeModerationRepo()
    post = feed_repo.add_post(_post())

    hide_post(
        post_id=post.id,
        performed_by="admin-1",
        reason="Spam",
        feed_repo=feed_repo,
        moderation_repo=moderation_repo,
    )

    assert feed_repo.get_post(post.id).hidden is True
    assert len(moderation_repo.events) == 1
    event = moderation_repo.events[0]
    assert event.target_type == ModerationTargetType.POST.value
    assert event.target_id == post.id
    assert event.action == ModerationAction.HIDDEN.value
    assert event.performed_by == "admin-1"
    assert event.reason == "Spam"


def test_restore_post_flips_flag_back_and_writes_audit_event():
    feed_repo = FakeFeedRepo()
    moderation_repo = FakeModerationRepo()
    post = feed_repo.add_post(_post(hidden=True))

    restore_post(
        post_id=post.id,
        performed_by="admin-1",
        reason=None,
        feed_repo=feed_repo,
        moderation_repo=moderation_repo,
    )

    assert feed_repo.get_post(post.id).hidden is False
    assert len(moderation_repo.events) == 1
    assert moderation_repo.events[0].action == ModerationAction.RESTORED.value
    assert moderation_repo.events[0].reason is None


def test_hide_post_raises_for_unknown_post():
    feed_repo = FakeFeedRepo()
    moderation_repo = FakeModerationRepo()

    with pytest.raises(ModerationTargetNotFoundError):
        hide_post(
            post_id="does-not-exist",
            performed_by="admin-1",
            reason=None,
            feed_repo=feed_repo,
            moderation_repo=moderation_repo,
        )
    # No audit event written for a no-op action.
    assert moderation_repo.events == []


def test_hide_comment_flips_flag_and_writes_audit_event():
    feed_repo = FakeFeedRepo()
    moderation_repo = FakeModerationRepo()
    post = feed_repo.add_post(_post())
    comment = feed_repo.add_comment(_comment(post.id))

    hide_comment(
        comment_id=comment.id,
        performed_by="admin-1",
        reason="Off-topic abuse",
        feed_repo=feed_repo,
        moderation_repo=moderation_repo,
    )

    assert feed_repo.get_comment(comment.id).hidden is True
    event = moderation_repo.events[0]
    assert event.target_type == ModerationTargetType.COMMENT.value
    assert event.target_id == comment.id
    assert event.action == ModerationAction.HIDDEN.value


def test_restore_comment_flips_flag_back():
    feed_repo = FakeFeedRepo()
    moderation_repo = FakeModerationRepo()
    post = feed_repo.add_post(_post())
    comment = feed_repo.add_comment(_comment(post.id, hidden=True))

    restore_comment(
        comment_id=comment.id,
        performed_by="admin-1",
        reason="Appeal accepted",
        feed_repo=feed_repo,
        moderation_repo=moderation_repo,
    )

    assert feed_repo.get_comment(comment.id).hidden is False
    assert moderation_repo.events[0].action == ModerationAction.RESTORED.value


def test_hide_comment_raises_for_unknown_comment():
    feed_repo = FakeFeedRepo()
    moderation_repo = FakeModerationRepo()

    with pytest.raises(ModerationTargetNotFoundError):
        hide_comment(
            comment_id="does-not-exist",
            performed_by="admin-1",
            reason=None,
            feed_repo=feed_repo,
            moderation_repo=moderation_repo,
        )
    assert moderation_repo.events == []


def test_hidden_posts_excluded_from_default_list_but_included_with_flag():
    feed_repo = FakeFeedRepo()
    moderation_repo = FakeModerationRepo()
    visible_post = feed_repo.add_post(_post(problem_id="p1"))
    hidden_post = feed_repo.add_post(_post(problem_id="p1"))

    hide_post(
        post_id=hidden_post.id,
        performed_by="admin-1",
        reason=None,
        feed_repo=feed_repo,
        moderation_repo=moderation_repo,
    )

    default_listing = feed_repo.list_posts_for_problem("p1")
    assert [p.id for p in default_listing] == [visible_post.id]

    admin_listing = feed_repo.list_posts_for_problem("p1", include_hidden=True)
    assert {p.id for p in admin_listing} == {visible_post.id, hidden_post.id}


def test_hidden_comments_excluded_from_default_list_but_included_with_flag():
    feed_repo = FakeFeedRepo()
    moderation_repo = FakeModerationRepo()
    post = feed_repo.add_post(_post())
    visible_comment = feed_repo.add_comment(_comment(post.id))
    hidden_comment = feed_repo.add_comment(_comment(post.id))

    hide_comment(
        comment_id=hidden_comment.id,
        performed_by="admin-1",
        reason=None,
        feed_repo=feed_repo,
        moderation_repo=moderation_repo,
    )

    default_listing = feed_repo.list_comments_for_post(post.id)
    assert [c.id for c in default_listing] == [visible_comment.id]

    admin_listing = feed_repo.list_comments_for_post(post.id, include_hidden=True)
    assert {c.id for c in admin_listing} == {visible_comment.id, hidden_comment.id}
