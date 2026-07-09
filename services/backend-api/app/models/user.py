"""User ORM model.

`reputation` starts at 0 and only ever moves via commitment checkpoint
events (resolve/abandon) applied in `app/services/checkpoint_service.py`
— never from posts/likes/comments. This is a hard product rule (CLAUDE.md
"Gamification & Reputation": "Should move on resolution/abandonment
events, not on likes/comments/post volume"). There is deliberately no
code path anywhere that increments reputation from feed activity.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    reputation: Mapped[int] = mapped_column(nullable=False, default=0)

    # created_at doubles as the "member since" date exposed in the API —
    # no separate column needed. Uses a portable default (Python-side)
    # rather than a server-side `now()` so it behaves identically against
    # both Postgres (prod/dev) and SQLite (integration tests).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
