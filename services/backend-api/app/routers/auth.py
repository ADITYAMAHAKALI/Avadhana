"""Signup / login.

Passwords are bcrypt-hashed (app.core.security) — never stored or logged
plaintext. Issues a JWT on both signup and login (see
app.core.security.create_access_token); there is no separate "verify
email" step for SLC v1.

Both endpoints carry a tighter-than-default rate limit
(`app.core.rate_limit.AUTH_RATE_LIMIT`, 5/minute per IP) on top of the
general-API default — these are the brute-force-sensitive endpoints
(credential stuffing on login, account-enumeration/spam via signup). The
`request: Request` parameter is required by slowapi's `@limiter.limit`
decorator to read the caller's IP; it's otherwise unused by the handler.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import AUTH_RATE_LIMIT, limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyUserRepo
from app.models.user import User
from app.schemas import AuthResponse, LoginRequest, SignupRequest
from app.services.presenters import user_to_out

router = APIRouter(tags=["auth"])


@router.post("/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_RATE_LIMIT)
def signup(
    request: Request, body: SignupRequest, session: Session = Depends(get_session)
) -> AuthResponse:
    user_repo = SqlAlchemyUserRepo(session)

    if user_repo.get_by_email(body.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "EMAIL_TAKEN", "message": "An account with this email already exists."},
        )

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        location=body.location,
    )
    user = user_repo.add(user)
    token = create_access_token(user.id)
    return AuthResponse(token=token, user=user_to_out(user))


@router.post("/auth/login", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
def login(
    request: Request, body: LoginRequest, session: Session = Depends(get_session)
) -> AuthResponse:
    user_repo = SqlAlchemyUserRepo(session)
    user = user_repo.get_by_email(body.email)

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_CREDENTIALS", "message": "Email or password is incorrect."},
        )

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=user_to_out(user))
