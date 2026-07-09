"""Integration tests proving the SQLAlchemy models themselves work
against a real (if SQLite, in-memory) database: inserts, foreign keys,
unique constraints. Business rules (slot limits, lock enforcement) are
NOT re-tested here — those are unit-tested against fakes in
tests/unit/. This file is purely "does the ORM layer function."
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.checkpoint import CommitmentCheckpoint
from app.models.commitment import Commitment
from app.models.feed import Comment, FeedPost, PostLike
from app.models.problem import Problem
from app.models.user import User


def test_create_and_fetch_user(db_session):
    user = User(name="Ravi Menon", email="ravi@example.com", password_hash="hashed")
    db_session.add(user)
    db_session.commit()

    fetched = db_session.get(User, user.id)
    assert fetched is not None
    assert fetched.email == "ravi@example.com"
    assert fetched.reputation == 0  # starts at 0


def test_duplicate_email_violates_unique_constraint(db_session):
    db_session.add(User(name="A", email="dup@example.com", password_hash="x"))
    db_session.commit()

    db_session.add(User(name="B", email="dup@example.com", password_hash="y"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_problem_and_commitment_relationship(db_session):
    user = User(name="Ravi Menon", email="ravi2@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()

    problem = Problem(
        title="Fix streetlights",
        summary="Broken streetlights",
        location="Bengaluru",
        category="infrastructure",
        tier="C",
        created_by_user_id=user.id,
    )
    db_session.add(problem)
    db_session.commit()

    commitment = Commitment(user_id=user.id, problem_id=problem.id, role="thinker")
    db_session.add(commitment)
    db_session.commit()

    fetched = db_session.get(Commitment, commitment.id)
    assert fetched.status == "active"
    assert fetched.lock_expires_at > fetched.started_at


def test_checkpoint_rows_are_append_only_in_practice(db_session):
    user = User(name="A", email="a@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    problem = Problem(title="T", summary="S", location="L", category="C", tier="D", created_by_user_id=user.id)
    db_session.add(problem)
    db_session.commit()
    commitment = Commitment(user_id=user.id, problem_id=problem.id, role="actor", specialization="Legal")
    db_session.add(commitment)
    db_session.commit()

    cp1 = CommitmentCheckpoint(commitment_id=commitment.id, event_type="created")
    db_session.add(cp1)
    db_session.commit()

    cp2 = CommitmentCheckpoint(commitment_id=commitment.id, event_type="continued", note="Still going")
    db_session.add(cp2)
    db_session.commit()

    rows = (
        db_session.query(CommitmentCheckpoint)
        .filter(CommitmentCheckpoint.commitment_id == commitment.id)
        .all()
    )
    assert len(rows) == 2
    assert {r.event_type for r in rows} == {"created", "continued"}


def test_post_like_unique_constraint_enforces_one_like_per_user_per_post(db_session):
    user = User(name="A", email="liker@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    problem = Problem(title="T", summary="S", location="L", category="C", tier="D", created_by_user_id=user.id)
    db_session.add(problem)
    db_session.commit()
    post = FeedPost(problem_id=problem.id, author_user_id=user.id, author_role="thinker", body="Hello")
    db_session.add(post)
    db_session.commit()

    db_session.add(PostLike(post_id=post.id, user_id=user.id))
    db_session.commit()

    db_session.add(PostLike(post_id=post.id, user_id=user.id))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_comment_attaches_to_post(db_session):
    user = User(name="A", email="commenter@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    problem = Problem(title="T", summary="S", location="L", category="C", tier="D", created_by_user_id=user.id)
    db_session.add(problem)
    db_session.commit()
    post = FeedPost(problem_id=problem.id, author_user_id=user.id, author_role="thinker", body="Hello")
    db_session.add(post)
    db_session.commit()

    comment = Comment(post_id=post.id, author_user_id=user.id, author_role="thinker", body="A reply")
    db_session.add(comment)
    db_session.commit()

    fetched = db_session.get(Comment, comment.id)
    assert fetched.post_id == post.id
