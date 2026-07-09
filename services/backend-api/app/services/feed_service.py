"""Problem feed business logic: creating posts/comments and toggling
likes. Authorization (commitment-gated voice) happens one layer up, via
the `require_committed_member` dependency on the router — by the time
these functions run, the caller's ACTIVE commitment has already been
verified and is passed in as `author_role`.

`roleLabel` presentation (Thinker/Actor/Backer, capitalized) and
`timeAgo` are computed at read time in the router/presenter step (see
`app/services/presenters.py`), not stored — so if the label format ever
changes, it changes for historical posts too without a backfill.
"""

from app.interfaces.repositories import FeedRepoPort
from app.models.feed import Comment, FeedPost


def create_post(
    *, problem_id: str, author_user_id: str, author_role: str, body: str, feed_repo: FeedRepoPort
) -> FeedPost:
    post = FeedPost(
        problem_id=problem_id,
        author_user_id=author_user_id,
        author_role=author_role,
        body=body,
    )
    return feed_repo.add_post(post)


def create_comment(
    *, post_id: str, author_user_id: str, author_role: str, body: str, feed_repo: FeedRepoPort
) -> Comment:
    comment = Comment(
        post_id=post_id,
        author_user_id=author_user_id,
        author_role=author_role,
        body=body,
    )
    return feed_repo.add_comment(comment)


def toggle_like(*, post_id: str, user_id: str, feed_repo: FeedRepoPort) -> int:
    """Idempotent toggle: first call likes, second call by the same user
    unlikes. See app/models/feed.py PostLike docstring for why this is
    enforced at the DB level too (unique constraint), not just here."""
    return feed_repo.toggle_like(post_id, user_id)
