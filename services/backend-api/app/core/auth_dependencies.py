"""FastAPI dependencies for resolving the authenticated user from a
Bearer JWT.

`get_current_user` is the base dependency every authenticated route
depends on. `require_committed_member` (in
`app/services/commitment_gate.py`) builds on top of this one to add the
commitment-gated-voice check — kept in `app/services/` rather than here
because it needs the CommitmentRepoPort, i.e. it's business logic, not
pure auth plumbing.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyUserRepo
from app.models.user import User

# `auto_error=False` so a missing header produces our own 401 with a
# consistent body shape, rather than FastAPI's default.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Resolves the caller's User row from `Authorization: Bearer <jwt>`.

    Raises 401 for anything auth-related (missing header, malformed
    token, expired token, unknown user) — this dependency's job stops at
    "who is this". Whether they're ALLOWED to do the thing they're
    asking for (e.g. commitment-gated voice) is a 403 decided further up
    the dependency chain (see `require_committed_member`), per the
    contract's explicit 401-vs-403 distinction.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHENTICATED", "message": "Missing or invalid Authorization header."},
        )
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_TOKEN", "message": "Token is invalid or expired."},
        )

    user = SqlAlchemyUserRepo(session).get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_TOKEN", "message": "Token does not match a known user."},
        )
    return user
