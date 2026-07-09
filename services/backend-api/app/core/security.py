"""Password hashing and JWT issuance/verification.

Passwords: bcrypt via `passlib[bcrypt]` — hashed, never stored plaintext,
never reversibly encrypted (per the API contract). bcrypt's built-in salt
handling means we don't manage salts ourselves.

JWTs: signed with `JWT_SECRET` (HS256), carrying the user id as `sub`.
This is the ONLY auth mechanism for SLC v1 — no refresh tokens, no
sessions table. `JWT_SECRET` must never be committed (see CLAUDE.md
"API Key & Secret Management" — the same non-negotiable rule applies to
JWT_SECRET as SARVAM keys).
"""

from datetime import timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.time import utcnow

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Note: passlib 1.7.4 logs a harmless "(trapped) error reading bcrypt
# version" warning on import with bcrypt>=4.1 (passlib probes
# `bcrypt.__about__.__version__`, which bcrypt removed). Hashing and
# verification both work correctly despite the warning — this is a
# known passlib/bcrypt version-probe incompatibility, not a functional
# bug. Tracked upstream; revisit the pin if passlib cuts a fixed release.


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(user_id: str) -> str:
    now = utcnow()
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    """Raised when a bearer token is missing, malformed, or expired.

    Kept as a distinct exception type (rather than letting PyJWT's
    exceptions leak into route handlers) so `app/core/auth_dependencies.py`
    has one thing to catch and translate into a 401.
    """


def decode_access_token(token: str) -> str:
    """Returns the user id (`sub` claim) or raises InvalidTokenError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    sub = payload.get("sub")
    if not sub:
        raise InvalidTokenError("Token missing 'sub' claim")
    return sub
