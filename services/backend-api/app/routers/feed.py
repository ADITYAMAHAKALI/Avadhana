"""Problem-specific feed: posts, likes, comments.

Write endpoints depend on `require_committed_member` (see
app.services.commitment_gate) — the reusable commitment-gated-voice
dependency built for issue #8. Read (GET) endpoints are public by design
(share links must work for non-members).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyFeedRepo, SqlAlchemyUserRepo
from app.models.commitment import Commitment
from app.models.user import User
from app.schemas import CommentCreateRequest, CommentOut, FeedPostOut, LikeOut, PostCreateRequest
from app.services.commitment_gate import require_committed_member
from app.services.feed_service import create_comment, create_post, toggle_like
from app.services.presenters import comment_to_out, post_to_out

router = APIRouter(tags=["feed"])


@router.post(
    "/problems/{problem_id}/posts",
    response_model=FeedPostOut,
    status_code=status.HTTP_201_CREATED,
)
def create_post_route(
    problem_id: str,
    body: PostCreateRequest,
    current_user: User = Depends(get_current_user),
    commitment: Commitment = Depends(require_committed_member),
    session: Session = Depends(get_session),
) -> FeedPostOut:
    feed_repo = SqlAlchemyFeedRepo(session)
    post = create_post(
        problem_id=problem_id,
        author_user_id=current_user.id,
        author_role=commitment.role,
        body=body.body,
        feed_repo=feed_repo,
    )
    return post_to_out(post, current_user, like_count=0)


@router.get("/problems/{problem_id}/posts", response_model=list[FeedPostOut])
def list_posts_route(
    problem_id: str, session: Session = Depends(get_session)
) -> list[FeedPostOut]:
    feed_repo = SqlAlchemyFeedRepo(session)
    user_repo = SqlAlchemyUserRepo(session)
    posts = feed_repo.list_posts_for_problem(problem_id)

    out: list[FeedPostOut] = []
    for post in posts:
        author = user_repo.get_by_id(post.author_user_id)
        if author is None:
            continue
        out.append(post_to_out(post, author, like_count=feed_repo.like_count(post.id)))
    return out


@router.post("/problems/{problem_id}/posts/{post_id}/like", response_model=LikeOut)
def like_post_route(
    problem_id: str,
    post_id: str,
    current_user: User = Depends(get_current_user),
    commitment: Commitment = Depends(require_committed_member),
    session: Session = Depends(get_session),
) -> LikeOut:
    feed_repo = SqlAlchemyFeedRepo(session)
    post = feed_repo.get_post(post_id)
    if post is None or post.problem_id != problem_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "POST_NOT_FOUND", "message": f"No post with id {post_id} on this problem."},
        )
    new_count = toggle_like(post_id=post_id, user_id=current_user.id, feed_repo=feed_repo)
    return LikeOut(like_count=new_count)


@router.post(
    "/problems/{problem_id}/posts/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment_route(
    problem_id: str,
    post_id: str,
    body: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    commitment: Commitment = Depends(require_committed_member),
    session: Session = Depends(get_session),
) -> CommentOut:
    feed_repo = SqlAlchemyFeedRepo(session)
    post = feed_repo.get_post(post_id)
    if post is None or post.problem_id != problem_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "POST_NOT_FOUND", "message": f"No post with id {post_id} on this problem."},
        )
    comment = create_comment(
        post_id=post_id,
        author_user_id=current_user.id,
        author_role=commitment.role,
        body=body.body,
        feed_repo=feed_repo,
    )
    return comment_to_out(comment, current_user)


@router.get("/problems/{problem_id}/posts/{post_id}/comments", response_model=list[CommentOut])
def list_comments_route(
    problem_id: str, post_id: str, session: Session = Depends(get_session)
) -> list[CommentOut]:
    feed_repo = SqlAlchemyFeedRepo(session)
    user_repo = SqlAlchemyUserRepo(session)
    comments = feed_repo.list_comments_for_post(post_id)

    out: list[CommentOut] = []
    for comment in comments:
        author = user_repo.get_by_id(comment.author_user_id)
        if author is None:
            continue
        out.append(comment_to_out(comment, author))
    return out
