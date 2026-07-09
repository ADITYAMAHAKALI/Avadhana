"""Commitment-gated authorization dependency (GitHub issue #8).

This is THE enforcement point for CLAUDE.md's non-negotiable constraint
#3: "only users with an ACTIVE commitment on a problem can post/comment/
like on it." Built as a single reusable FastAPI dependency,
`require_committed_member`, so every current and future write endpoint
on a problem's feed (posts, comments, likes, and later polls/tasks/asset
uploads once those land) can depend on it identically rather than
reimplementing the check.

Deliberately layered on top of `get_current_user` (in
`app/core/auth_dependencies.py`) rather than duplicating auth logic, so
the 401-vs-403 distinction stays clean:
  - No/invalid token                          -> 401 (raised upstream by
                                                  get_current_user)
  - Valid token, but no ACTIVE commitment here -> 403 NOT_COMMITTED
    (raised here, with a message a frontend can show directly, per
    CLAUDE.md "explain why on hover/UX")

Lives in `app/services/` (not `app/core/`) because, unlike pure JWT
decoding, it depends on the CommitmentRepoPort — i.e. it's a business
rule, not generic auth plumbing.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyCommitmentRepo
from app.models.commitment import Commitment
from app.models.user import User


def require_committed_member(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Commitment:
    """Resolves the caller's ACTIVE commitment on `problem_id`, or raises
    403 NOT_COMMITTED. Use as a route dependency:

        @router.post("/problems/{problem_id}/posts")
        def create_post(
            problem_id: str,
            body: PostCreateRequest,
            commitment: Commitment = Depends(require_committed_member),
            ...
        ):
            ...

    FastAPI matches the `problem_id` path parameter automatically since
    this dependency's parameter name matches the route's path parameter
    name — no extra wiring needed per-route.
    """
    commitment_repo = SqlAlchemyCommitmentRepo(session)
    commitment = commitment_repo.get_active_for_user_and_problem(current_user.id, problem_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "NOT_COMMITTED",
                "message": (
                    "Only committed members can post here. Commit a focus "
                    "slot to this problem to participate."
                ),
            },
        )
    return commitment
