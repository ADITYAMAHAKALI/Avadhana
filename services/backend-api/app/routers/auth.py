"""Signup / login.

Passwords are bcrypt-hashed (app.core.security) — never stored or logged
plaintext. Issues a JWT on both signup and login (see
app.core.security.create_access_token); there is no separate "verify
email" step for SLC v1.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyUserRepo
from app.models.user import User
from app.schemas import AuthResponse, LoginRequest, SignupRequest
from app.services.presenters import user_to_out

router = APIRouter(tags=["auth"])


@router.post("/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, session: Session = Depends(get_session)) -> AuthResponse:
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
def login(body: LoginRequest, session: Session = Depends(get_session)) -> AuthResponse:
    user_repo = SqlAlchemyUserRepo(session)
    user = user_repo.get_by_email(body.email)

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_CREDENTIALS", "message": "Email or password is incorrect."},
        )

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=user_to_out(user))
