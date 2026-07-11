"""Unit tests for problem-feed business logic (posts/comments/likes) and
the commitment lookup that backs commitment-gated voice.

The actual 401-vs-403 HTTP behavior of `require_committed_member` is
covered by integration tests (tests/integration/test_api_feed.py) since
it's a FastAPI dependency; here we test the underlying repo query and
feed_service functions it relies on.
"""

import pytest

from app.models.problem import Problem
from app.services.commitment_service import create_commitment
from app.services.feed_service import (
    InvalidParentCommentError,
    create_comment,
    create_post,
    toggle_like,
)
from tests.unit.fakes import FakeCheckpointRepo, FakeCommitmentRepo, FakeFeedRepo, FakeProblemRepo


def _committed_setup(role="thinker"):
    problem_repo = FakeProblemRepo()
    problem = Problem(title="P", summary="s", location="l", category="c", tier="D", created_by_user_id="creator")
    problem_repo.add(problem)
    commitment_repo = FakeCommitmentRepo()
    checkpoint_repo = FakeCheckpointRepo()
    commitment = create_commitment(
        user_id="user-1",
        problem_id=problem.id,
        role=role,
        specialization=None,
        problem_repo=problem_repo,
        commitment_repo=commitment_repo,
        checkpoint_repo=checkpoint_repo,
    )
    return problem, commitment, commitment_repo


def test_get_active_for_user_and_problem_finds_committed_member():
    problem, commitment, commitment_repo = _committed_setup()
    found = commitment_repo.get_active_for_user_and_problem("user-1", problem.id)
    assert found is not None
    assert found.id == commitment.id


def test_get_active_for_user_and_problem_returns_none_for_non_member():
    problem, commitment, commitment_repo = _committed_setup()
    found = commitment_repo.get_active_for_user_and_problem("some-other-user", problem.id)
    assert found is None


def test_create_post_stores_authors_role_at_post_time():
    problem, commitment, _ = _committed_setup(role="actor")
    feed_repo = FakeFeedRepo()
    post = create_post(
        problem_id=problem.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Filed the RTI today.",
        feed_repo=feed_repo,
    )
    assert post.author_role == "actor"
    assert feed_repo.list_posts_for_problem(problem.id) == [post]


def test_create_comment_attached_to_post():
    problem, commitment, _ = _committed_setup()
    feed_repo = FakeFeedRepo()
    post = create_post(
        problem_id=problem.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Post body",
        feed_repo=feed_repo,
    )
    comment = create_comment(
        post_id=post.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="A comment",
        feed_repo=feed_repo,
    )
    assert feed_repo.list_comments_for_post(post.id) == [comment]


def test_create_comment_reply_nests_under_parent():
    problem, commitment, _ = _committed_setup()
    feed_repo = FakeFeedRepo()
    post = create_post(
        problem_id=problem.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Post body",
        feed_repo=feed_repo,
    )
    top_level = create_comment(
        post_id=post.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Top level",
        feed_repo=feed_repo,
    )
    reply = create_comment(
        post_id=post.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="A reply",
        feed_repo=feed_repo,
        parent_comment_id=top_level.id,
    )
    assert reply.parent_comment_id == top_level.id
    assert top_level.parent_comment_id is None
    # Flat list with parent pointers, not a tree.
    assert {c.id for c in feed_repo.list_comments_for_post(post.id)} == {top_level.id, reply.id}


def test_create_comment_rejects_parent_from_a_different_post():
    problem, commitment, _ = _committed_setup()
    feed_repo = FakeFeedRepo()
    post_a = create_post(
        problem_id=problem.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Post A",
        feed_repo=feed_repo,
    )
    post_b = create_post(
        problem_id=problem.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Post B",
        feed_repo=feed_repo,
    )
    comment_on_a = create_comment(
        post_id=post_a.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Comment on A",
        feed_repo=feed_repo,
    )
    with pytest.raises(InvalidParentCommentError):
        create_comment(
            post_id=post_b.id,
            author_user_id="user-1",
            author_role=commitment.role,
            body="Cross-post reply",
            feed_repo=feed_repo,
            parent_comment_id=comment_on_a.id,
        )


def test_create_comment_rejects_nonexistent_parent():
    problem, commitment, _ = _committed_setup()
    feed_repo = FakeFeedRepo()
    post = create_post(
        problem_id=problem.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Post body",
        feed_repo=feed_repo,
    )
    with pytest.raises(InvalidParentCommentError):
        create_comment(
            post_id=post.id,
            author_user_id="user-1",
            author_role=commitment.role,
            body="Reply to nothing",
            feed_repo=feed_repo,
            parent_comment_id="does-not-exist",
        )


def test_list_posts_sort_top_orders_by_like_count():
    problem, commitment, _ = _committed_setup()
    feed_repo = FakeFeedRepo()
    post1 = create_post(
        problem_id=problem.id, author_user_id="user-1", author_role=commitment.role,
        body="First", feed_repo=feed_repo,
    )
    post2 = create_post(
        problem_id=problem.id, author_user_id="user-1", author_role=commitment.role,
        body="Second", feed_repo=feed_repo,
    )
    toggle_like(post_id=post2.id, user_id="user-1", feed_repo=feed_repo)
    toggle_like(post_id=post2.id, user_id="user-2", feed_repo=feed_repo)
    toggle_like(post_id=post1.id, user_id="user-1", feed_repo=feed_repo)

    top = feed_repo.list_posts_for_problem(problem.id, sort="top")
    assert [p.id for p in top] == [post2.id, post1.id]

    newest = feed_repo.list_posts_for_problem(problem.id, sort="new")
    assert [p.id for p in newest] == [post2.id, post1.id]


def test_like_toggle_is_idempotent_per_user():
    problem, commitment, _ = _committed_setup()
    feed_repo = FakeFeedRepo()
    post = create_post(
        problem_id=problem.id,
        author_user_id="user-1",
        author_role=commitment.role,
        body="Post body",
        feed_repo=feed_repo,
    )

    count_after_first_like = toggle_like(post_id=post.id, user_id="user-1", feed_repo=feed_repo)
    assert count_after_first_like == 1

    # Liking twice from the same user unlikes (toggle), not double-counts.
    count_after_second_like = toggle_like(post_id=post.id, user_id="user-1", feed_repo=feed_repo)
    assert count_after_second_like == 0

    # A second user's like is independent.
    toggle_like(post_id=post.id, user_id="user-1", feed_repo=feed_repo)
    count_after_other_user = toggle_like(post_id=post.id, user_id="user-2", feed_repo=feed_repo)
    assert count_after_other_user == 2
