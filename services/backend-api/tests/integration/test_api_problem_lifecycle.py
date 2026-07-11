"""Integration tests for the problem-level resolution-status protocol
(issue #100) through the real HTTP API — CLAUDE.md "Problem Lifecycle
Protocol".

Mirrors test_api_checkpoint_flow.py's pattern for backdating a
commitment's `lock_expires_at`/`started_at` directly via `db_session`
(the same in-memory SQLite engine `client` uses) so checkpoints can be
applied without waiting 90 real days, and additionally backdates
`CommitmentCheckpoint.occurred_at` rows directly to place `resolved`
claims and objections at controlled points relative to the 7-day
objection window.
"""

from datetime import timedelta

from app.core.time import utcnow
from app.models.checkpoint import CommitmentCheckpoint
from app.models.commitment import Commitment
from app.models.resolution_objection import ResolutionObjection
from app.models.user import User


def _signup_and_auth_headers(client, email):
    resp = client.post(
        "/auth/signup",
        json={"name": "Test User", "email": email, "password": "testpass123", "location": "Bengaluru"},
    )
    token = resp.json()["token"]
    return token, {"Authorization": f"Bearer {token}"}


def _create_problem(client, headers, title="A problem"):
    resp = client.post(
        "/problems",
        json={"title": title, "summary": "Summary text", "location": "Bengaluru", "category": "civic", "tier": "C"},
        headers=headers,
    )
    return resp.json()["id"]


def _commit(client, headers, problem_id, role="thinker"):
    resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": role, "specialization": None},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _backdate_commitment(db_session, commitment_id: str, days_ago: int):
    commitment = db_session.get(Commitment, commitment_id)
    commitment.started_at = utcnow() - timedelta(days=days_ago)
    commitment.lock_expires_at = commitment.started_at + timedelta(days=90)
    db_session.commit()


def _resolve(client, headers, commitment_id):
    resp = client.post(
        f"/commitments/{commitment_id}/checkpoint",
        json={"action": "resolve", "note": "Done"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _backdate_latest_checkpoint(db_session, commitment_id: str, occurred_at):
    """Backdates the MOST RECENT checkpoint row for a commitment (the
    one `apply_checkpoint` just inserted, e.g. the `resolved` event) to
    a controlled timestamp, so tests can place resolve claims and the
    resulting 7-day objection window wherever they need relative to
    `utcnow()` — same technique as `_backdate_commitment` above, but
    targeting the checkpoint audit row instead of the commitment row.

    Also backdates every OTHER (earlier) checkpoint row for the same
    commitment (e.g. the `created` row written at commitment creation)
    to stay safely before `occurred_at`, preserving "most recent
    checkpoint" ordering — `list_latest_for_commitments` picks the
    checkpoint with the latest `occurred_at`, so without this the
    `created` row (whose real wall-clock timestamp is untouched, and
    therefore LATER than a freshly-backdated-into-the-past `resolved`
    row) would incorrectly become the "most recent" event."""
    rows = (
        db_session.query(CommitmentCheckpoint)
        .filter(CommitmentCheckpoint.commitment_id == commitment_id)
        .order_by(CommitmentCheckpoint.occurred_at.asc())
        .all()
    )
    if not rows:
        return
    latest_row = rows[-1]
    for i, row in enumerate(rows[:-1]):
        row.occurred_at = occurred_at - timedelta(days=365) + timedelta(seconds=i)
    latest_row.occurred_at = occurred_at
    db_session.commit()


def test_open_status_below_threshold(client, db_session):
    _, headers_a = _signup_and_auth_headers(client, "a@example.com")
    _, headers_b = _signup_and_auth_headers(client, "b@example.com")
    problem_id = _create_problem(client, headers_a)

    commitment_a = _commit(client, headers_a, problem_id)
    _commit(client, headers_b, problem_id)
    _backdate_commitment(db_session, commitment_a, days_ago=95)

    _resolve(client, headers_a, commitment_a)

    problem = client.get(f"/problems/{problem_id}").json()
    assert problem["resolutionStatus"] == "open"
    assert problem["resolvedCount"] == 1
    assert problem["totalCommitted"] == 2
    assert problem["resolutionThreshold"] == 2


def test_two_of_two_resolve_no_objection_flips_to_resolved_after_window(client, db_session):
    _, headers_a = _signup_and_auth_headers(client, "resolver1@example.com")
    _, headers_b = _signup_and_auth_headers(client, "resolver2@example.com")
    problem_id = _create_problem(client, headers_a)

    commitment_a = _commit(client, headers_a, problem_id)
    commitment_b = _commit(client, headers_b, problem_id)
    _backdate_commitment(db_session, commitment_a, days_ago=95)
    _backdate_commitment(db_session, commitment_b, days_ago=95)

    _resolve(client, headers_a, commitment_a)
    _resolve(client, headers_b, commitment_b)

    # Still within the 7-day window right after both claims: pending, not resolved yet.
    problem = client.get(f"/problems/{problem_id}").json()
    assert problem["resolutionStatus"] == "pending_resolution"
    assert problem["resolvedCount"] == 2
    assert problem["totalCommitted"] == 2

    # Push both resolve claims 8 days into the past -> window has elapsed.
    past = utcnow() - timedelta(days=8)
    _backdate_latest_checkpoint(db_session, commitment_a, past)
    _backdate_latest_checkpoint(db_session, commitment_b, past + timedelta(minutes=1))

    problem = client.get(f"/problems/{problem_id}").json()
    assert problem["resolutionStatus"] == "resolved"
    assert problem["objectionCount"] == 0


def test_objection_blocks_auto_resolution(client, db_session):
    _, headers_a = _signup_and_auth_headers(client, "obj-a@example.com")
    _, headers_b = _signup_and_auth_headers(client, "obj-b@example.com")
    _, headers_c = _signup_and_auth_headers(client, "obj-c@example.com")
    problem_id = _create_problem(client, headers_a)

    commitment_a = _commit(client, headers_a, problem_id)
    commitment_b = _commit(client, headers_b, problem_id)
    _commit(client, headers_c, problem_id)
    _backdate_commitment(db_session, commitment_a, days_ago=95)
    _backdate_commitment(db_session, commitment_b, days_ago=95)

    _resolve(client, headers_a, commitment_a)
    _resolve(client, headers_b, commitment_b)

    obj_resp = client.post(f"/problems/{problem_id}/objections", headers=headers_c)
    assert obj_resp.status_code == 201, obj_resp.text

    problem = client.get(f"/problems/{problem_id}").json()
    assert problem["resolutionStatus"] == "disputed"
    assert problem["objectionCount"] == 1


def test_objection_stays_disputed_after_window_elapses(client, db_session):
    """An objection raised INSIDE the window keeps the problem disputed
    even once real time moves past window_ends_at — auto-resolution
    stays blocked; the window elapsing only matters for the no-objection
    case (see test_two_of_two_resolve_no_objection_flips_to_resolved_after_window)."""
    _, headers_a = _signup_and_auth_headers(client, "obj2-a@example.com")
    _, headers_b = _signup_and_auth_headers(client, "obj2-b@example.com")
    _, headers_c = _signup_and_auth_headers(client, "obj2-c@example.com")
    problem_id = _create_problem(client, headers_a)

    commitment_a = _commit(client, headers_a, problem_id)
    commitment_b = _commit(client, headers_b, problem_id)
    _commit(client, headers_c, problem_id)
    _backdate_commitment(db_session, commitment_a, days_ago=95)
    _backdate_commitment(db_session, commitment_b, days_ago=95)

    _resolve(client, headers_a, commitment_a)
    _resolve(client, headers_b, commitment_b)

    # Move the resolve claims to 3 days ago (still inside the 7-day
    # window) before objecting, so the objection timestamp naturally
    # falls inside window_start..window_start+7d.
    claim_time = utcnow() - timedelta(days=3)
    _backdate_latest_checkpoint(db_session, commitment_a, claim_time)
    _backdate_latest_checkpoint(db_session, commitment_b, claim_time + timedelta(minutes=1))

    obj_resp = client.post(f"/problems/{problem_id}/objections", headers=headers_c)
    assert obj_resp.status_code == 201, obj_resp.text

    problem = client.get(f"/problems/{problem_id}").json()
    assert problem["resolutionStatus"] == "disputed"

    # Now push the claims (and, to keep the objection inside the
    # recomputed window, the objection row too) 8 days further back so
    # the window has elapsed relative to "now" — status must remain
    # "disputed", never flip to "resolved", since an objection was
    # raised inside its own window.
    further_past = claim_time - timedelta(days=8)
    _backdate_latest_checkpoint(db_session, commitment_a, further_past)
    _backdate_latest_checkpoint(db_session, commitment_b, further_past + timedelta(minutes=1))
    objection_row = (
        db_session.query(ResolutionObjection)
        .filter(ResolutionObjection.problem_id == problem_id)
        .first()
    )
    objection_row.raised_at = further_past + timedelta(hours=2)
    db_session.commit()

    problem = client.get(f"/problems/{problem_id}").json()
    assert problem["resolutionStatus"] == "disputed"


def test_non_committed_user_cannot_object(client, db_session):
    _, headers_a = _signup_and_auth_headers(client, "nc-a@example.com")
    _, headers_b = _signup_and_auth_headers(client, "nc-b@example.com")
    _, headers_stranger = _signup_and_auth_headers(client, "nc-stranger@example.com")
    problem_id = _create_problem(client, headers_a)

    commitment_a = _commit(client, headers_a, problem_id)
    commitment_b = _commit(client, headers_b, problem_id)
    _backdate_commitment(db_session, commitment_a, days_ago=95)
    _backdate_commitment(db_session, commitment_b, days_ago=95)

    _resolve(client, headers_a, commitment_a)
    _resolve(client, headers_b, commitment_b)

    resp = client.post(f"/problems/{problem_id}/objections", headers=headers_stranger)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_COMMITTED"


def test_cannot_object_twice_in_same_window(client, db_session):
    _, headers_a = _signup_and_auth_headers(client, "dup-a@example.com")
    _, headers_b = _signup_and_auth_headers(client, "dup-b@example.com")
    _, headers_c = _signup_and_auth_headers(client, "dup-c@example.com")
    problem_id = _create_problem(client, headers_a)

    commitment_a = _commit(client, headers_a, problem_id)
    commitment_b = _commit(client, headers_b, problem_id)
    _commit(client, headers_c, problem_id)
    _backdate_commitment(db_session, commitment_a, days_ago=95)
    _backdate_commitment(db_session, commitment_b, days_ago=95)

    _resolve(client, headers_a, commitment_a)
    _resolve(client, headers_b, commitment_b)

    first = client.post(f"/problems/{problem_id}/objections", headers=headers_c)
    assert first.status_code == 201

    second = client.post(f"/problems/{problem_id}/objections", headers=headers_c)
    assert second.status_code == 409
    assert second.json()["detail"]["error"] == "ALREADY_OBJECTED"


def test_objecting_with_no_active_window_is_409(client, db_session):
    _, headers_a = _signup_and_auth_headers(client, "noactive-a@example.com")
    problem_id = _create_problem(client, headers_a)
    _commit(client, headers_a, problem_id)

    resp = client.post(f"/problems/{problem_id}/objections", headers=headers_a)
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "NO_ACTIVE_RESOLUTION_WINDOW"


def test_objection_after_window_closed_does_not_block_resolution(client, db_session):
    _, headers_a = _signup_and_auth_headers(client, "late-a@example.com")
    _, headers_b = _signup_and_auth_headers(client, "late-b@example.com")
    problem_id = _create_problem(client, headers_a)

    commitment_a = _commit(client, headers_a, problem_id)
    commitment_b = _commit(client, headers_b, problem_id)
    _backdate_commitment(db_session, commitment_a, days_ago=95)
    _backdate_commitment(db_session, commitment_b, days_ago=95)

    _resolve(client, headers_a, commitment_a)
    _resolve(client, headers_b, commitment_b)

    # Move both resolve claims 8 days into the past (window closed) and
    # directly insert an objection row timestamped even further outside
    # the window (today, i.e. well past window_start + 7 days), simulating
    # one that arrived "late" relative to the episode it would have
    # applied to. Inserted directly via db_session (not the API) since
    # the objection endpoint itself would correctly reject this as
    # NO_ACTIVE_RESOLUTION_WINDOW — this test is specifically checking
    # the read-side status computation ignores a stray out-of-window row.
    past = utcnow() - timedelta(days=8)
    _backdate_latest_checkpoint(db_session, commitment_a, past)
    _backdate_latest_checkpoint(db_session, commitment_b, past + timedelta(minutes=1))

    user_a = db_session.query(User).filter(User.email == "late-a@example.com").first()
    late_objection = ResolutionObjection(
        problem_id=problem_id,
        objecting_user_id=user_a.id,
        raised_at=utcnow(),
    )
    db_session.add(late_objection)
    db_session.commit()

    problem = client.get(f"/problems/{problem_id}").json()
    assert problem["resolutionStatus"] == "resolved"
    assert problem["objectionCount"] == 0
