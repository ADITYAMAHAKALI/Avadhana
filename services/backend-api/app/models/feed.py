"""Problem-specific feed: posts, likes, comments.

Gated by commitment (CLAUDE.md "Commitment-Gated Voice") — see
`app/services/commitment_gate.py` for the shared `require_committed_member`
dependency used by every write endpoint in `app/routers/feed.py`. GET
endpoints for all three of these are public/unauthenticated by design
(share links must work for non-members — CLAUDE.md "External Discovery &
Visitor Flow").

Polls, task board, asset uploads, and donations are explicitly out of
scope for SLC v1 (see backend-build brief's "Explicit scope boundaries").

`hidden` (issue #59, human moderation override baseline): a simple,
mutable, denormalized current-state flag — same pattern as
`Commitment.status` being mutable while its audit trail
(`CommitmentCheckpoint`) is immutable. The actual audit trail for hide/
restore actions lives in `app.models.moderation.ModerationOverrideEvent`
(insert-only); this flag is just the fast-to-query "is this currently
hidden" projection used to filter normal feed reads. Never mutate this
column directly outside `app/services/moderation_service.py` — always
go through it so a `ModerationOverrideEvent` row is written alongside
the flip.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class FeedPost(Base):
    __tablename__ = "feed_posts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    problem_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("problems.id"), nullable=False, index=True
    )
    author_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    # The author's role on THIS problem at the time of posting, snapshotted
    # so the feed's `roleLabel` stays historically accurate even if the
    # author's commitment later resolves/abandons (their voice was
    # legitimate at post time — CLAUDE.md's gating is about who CAN post,
    # not a retroactive relabeling of what they said).
    author_role: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(String(5000), nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class PostLike(Base):
    """One row per (post, user) — existence of the row IS the like.

    Liking is a toggle (see app/services/feed_service.py): calling the
    like endpoint again removes the row (unlike) rather than erroring or
    double-counting. The unique constraint is the enforcement mechanism
    for "one like per user per post" at the DB level, not just app logic.
    """

    __tablename__ = "post_likes"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_post_like_user"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    post_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("feed_posts.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    post_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("feed_posts.id"), nullable=False, index=True
    )
    author_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    author_role: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
