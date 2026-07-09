"""Integration tests for the full checkpoint flow (resolve/abandon/
continue) through the real HTTP layer, once the 90-day lock has expired.

Since these tests can't wait 90 real days, they use the `db_session`
fixture (bound to the SAME in-memory SQLite engine as `client`, per
conftest.py's `engine` fixture) to backdate a commitment's
`started_at`/`lock_expires_at` directly — this is the standard way to
test time-gated logic without sleeping or mocking `datetime.now`
everywhere. The HTTP layer itself is untouched: only the seed data is
manipulated, not the enforcement code path.
"""

from datetime import timedelta

from app.core.time import utcnow
from app.models.commitment import Commitment


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


def _backdate_commitment(db_session, commitment_id: str, days_ago: int):
    commitment = db_session.get(Commitment, commitment_id)
    commitment.started_at = utcnow() - timedelta(days=days_ago)
    commitment.lock_expires_at = commitment.started_at + timedelta(days=90)
    db_session.commit()


def test_resolve_after_lock_expiry_updates_status_and_reputation(client, db_session):
    _, headers = _signup_and_auth_headers(client, "resolver@example.com")
    problem_id = _create_problem(client, headers)

    commit_resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "thinker", "specialization": None},
        headers=headers,
    )
    commitment_id = commit_resp.json()["id"]
    _backdate_commitment(db_session, commitment_id, days_ago=95)

    resp = client.post(
        f"/commitments/{commitment_id}/checkpoint",
        json={"action": "resolve", "note": "Streetlights fixed"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"

    me = client.get("/users/me", headers=headers).json()
    assert me["reputation"] == 20

    # Slot freed: committed-problems no longer lists it.
    committed = client.get("/users/me/committed-problems", headers=headers).json()
    assert committed == []

    # Shows up in commitment-history with a descriptive note.
    history = client.get("/users/me/commitment-history", headers=headers).json()
    assert len(history) == 1
    assert history[0]["status"] == "resolved"
    assert "Resolved after" in history[0]["note"]


def test_abandon_after_lock_expiry_is_visible_and_penalized(client, db_session):
    _, headers = _signup_and_auth_headers(client, "abandoner@example.com")
    problem_id = _create_problem(client, headers)

    commit_resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "actor", "specialization": "Field organizing"},
        headers=headers,
    )
    commitment_id = commit_resp.json()["id"]
    _backdate_commitment(db_session, commitment_id, days_ago=91)

    resp = client.post(
        f"/commitments/{commitment_id}/checkpoint",
        json={"action": "abandon", "note": "Lost momentum"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "abandoned"

    me = client.get("/users/me", headers=headers).json()
    assert me["reputation"] == -15

    history = client.get("/users/me/commitment-history", headers=headers).json()
    assert history[0]["status"] == "abandoned"
    assert "Abandoned at day" in history[0]["note"]


def test_abandoned_commitment_cannot_be_un_abandoned_via_any_endpoint(client, db_session):
    _, headers = _signup_and_auth_headers(client, "noreverse@example.com")
    problem_id = _create_problem(client, headers)

    commit_resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "thinker", "specialization": None},
        headers=headers,
    )
    commitment_id = commit_resp.json()["id"]
    _backdate_commitment(db_session, commitment_id, days_ago=91)

    client.post(
        f"/commitments/{commitment_id}/checkpoint",
        json={"action": "abandon", "note": None},
        headers=headers,
    )

    # Try every action again — all must fail, nothing resurrects it.
    for action in ("resolve", "abandon", "continue"):
        resp = client.post(
            f"/commitments/{commitment_id}/checkpoint",
            json={"action": action, "note": None},
            headers=headers,
        )
        assert resp.status_code == 409


def test_continue_resets_lock_keeps_active_and_frees_no_slot(client, db_session):
    _, headers = _signup_and_auth_headers(client, "continuer@example.com")
    problem_id = _create_problem(client, headers)

    commit_resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "backer", "specialization": None},
        headers=headers,
    )
    commitment_id = commit_resp.json()["id"]
    _backdate_commitment(db_session, commitment_id, days_ago=95)

    resp = client.post(
        f"/commitments/{commitment_id}/checkpoint",
        json={"action": "continue", "note": None},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # Still occupies a slot.
    slots = client.get("/users/me/focus-slots", headers=headers).json()
    assert slots["used"] == 1

    # No reputation change for continuing.
    me = client.get("/users/me", headers=headers).json()
    assert me["reputation"] == 0

    # Appears in commitment-history (has a non-created checkpoint) with a
    # "continued" note, even though status is still active.
    history = client.get("/users/me/commitment-history", headers=headers).json()
    assert history[0]["status"] == "continued"

    # But also still appears in committed-problems since it's ACTIVE.
    committed = client.get("/users/me/committed-problems", headers=headers).json()
    assert len(committed) == 1
    assert committed[0]["problemId"] == problem_id
