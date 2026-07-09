"""Integration tests for the human moderator override baseline (issue
#59): hide/restore posts and comments, and the admin-only moderation log.

Covers:
  - 401 unauthenticated
  - 403 authenticated-but-not-admin
  - 200/204 + audit row + flag flip for an admin
  - hidden content excluded from normal (public) GET endpoints
  - moderation-log lists override events for a problem, newest first

There is no API to become a platform admin (by design — see
app/models/user.py docstring), so tests promote a user directly via the
test DB session, mirroring how tests/integration/test_api_checkpoint_flow.py
backdates commitments to simulate the passage of time.
"""

from app.models.user import User


def _signup_and_auth_headers(client, email):
    resp = client.post(
        "/auth/signup",
        json={"name": "Test User", "email": email, "password": "testpass123", "location": "Bengaluru"},
    )
    token = resp.json()["token"]
    user_id = resp.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


def _make_admin(db_session, user_id: str) -> None:
    user = db_session.get(User, user_id)
    user.is_platform_admin = True
    db_session.commit()


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
    assert resp.status_code == 201
    return resp.json()


def _setup_post_and_comment(client, db_session):
    """Creates a problem, a committed member, a post, and a comment on
    that post. Returns (problem_id, post_id, comment_id, member_headers,
    admin_headers)."""
    member_headers, member_id = _signup_and_auth_headers(client, "member@example.com")
    problem_id = _create_problem(client, member_headers)
    _commit(client, member_headers, problem_id)
    post = client.post(
        f"/problems/{problem_id}/posts", json={"body": "Original post"}, headers=member_headers
    ).json()
    comment = client.post(
        f"/problems/{problem_id}/posts/{post['id']}/comments",
        json={"body": "Original comment"},
        headers=member_headers,
    ).json()

    admin_headers, admin_id = _signup_and_auth_headers(client, "admin@example.com")
    _make_admin(db_session, admin_id)

    return problem_id, post["id"], comment["id"], member_headers, admin_headers


# --- Hide/restore post: authorization matrix -------------------------------


def test_hide_post_requires_auth_401_without_token(client, db_session):
    problem_id, post_id, _, _, _ = _setup_post_and_comment(client, db_session)
    resp = client.post(f"/problems/{problem_id}/posts/{post_id}/moderation/hide", json={"reason": None})
    assert resp.status_code == 401


def test_hide_post_requires_admin_403_for_non_admin(client, db_session):
    problem_id, post_id, _, member_headers, _ = _setup_post_and_comment(client, db_session)
    resp = client.post(
        f"/problems/{problem_id}/posts/{post_id}/moderation/hide",
        json={"reason": None},
        headers=member_headers,
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error"] == "NOT_PLATFORM_ADMIN"


def test_admin_can_hide_and_restore_post(client, db_session):
    problem_id, post_id, _, _, admin_headers = _setup_post_and_comment(client, db_session)

    resp = client.post(
        f"/problems/{problem_id}/posts/{post_id}/moderation/hide",
        json={"reason": "Spam"},
        headers=admin_headers,
    )
    assert resp.status_code == 204

    # Hidden post excluded from the public feed read.
    listing = client.get(f"/problems/{problem_id}/posts").json()
    assert post_id not in [p["id"] for p in listing]

    # Moderation log shows the hide event.
    log = client.get(f"/problems/{problem_id}/moderation-log", headers=admin_headers).json()
    assert len(log) == 1
    assert log[0]["targetType"] == "post"
    assert log[0]["targetId"] == post_id
    assert log[0]["action"] == "hidden"
    assert log[0]["reason"] == "Spam"

    # Restore brings it back.
    resp = client.post(
        f"/problems/{problem_id}/posts/{post_id}/moderation/restore",
        json={"reason": "False positive"},
        headers=admin_headers,
    )
    assert resp.status_code == 204

    listing_after_restore = client.get(f"/problems/{problem_id}/posts").json()
    assert post_id in [p["id"] for p in listing_after_restore]

    log_after_restore = client.get(f"/problems/{problem_id}/moderation-log", headers=admin_headers).json()
    assert len(log_after_restore) == 2
    # Newest first.
    assert log_after_restore[0]["action"] == "restored"
    assert log_after_restore[1]["action"] == "hidden"


def test_hide_post_404_for_unknown_post(client, db_session):
    problem_id, _, _, _, admin_headers = _setup_post_and_comment(client, db_session)
    resp = client.post(
        f"/problems/{problem_id}/posts/does-not-exist/moderation/hide",
        json={"reason": None},
        headers=admin_headers,
    )
    assert resp.status_code == 404


# --- Hide/restore comment: authorization matrix -----------------------------


def test_hide_comment_requires_auth_401_without_token(client, db_session):
    problem_id, post_id, comment_id, _, _ = _setup_post_and_comment(client, db_session)
    resp = client.post(
        f"/problems/{problem_id}/posts/{post_id}/comments/{comment_id}/moderation/hide",
        json={"reason": None},
    )
    assert resp.status_code == 401


def test_hide_comment_requires_admin_403_for_non_admin(client, db_session):
    problem_id, post_id, comment_id, member_headers, _ = _setup_post_and_comment(client, db_session)
    resp = client.post(
        f"/problems/{problem_id}/posts/{post_id}/comments/{comment_id}/moderation/hide",
        json={"reason": None},
        headers=member_headers,
    )
    assert resp.status_code == 403


def test_admin_can_hide_and_restore_comment(client, db_session):
    problem_id, post_id, comment_id, _, admin_headers = _setup_post_and_comment(client, db_session)

    resp = client.post(
        f"/problems/{problem_id}/posts/{post_id}/comments/{comment_id}/moderation/hide",
        json={"reason": "Abusive"},
        headers=admin_headers,
    )
    assert resp.status_code == 204

    comments = client.get(f"/problems/{problem_id}/posts/{post_id}/comments").json()
    assert comment_id not in [c["id"] for c in comments]

    resp = client.post(
        f"/problems/{problem_id}/posts/{post_id}/comments/{comment_id}/moderation/restore",
        json={"reason": None},
        headers=admin_headers,
    )
    assert resp.status_code == 204

    comments_after = client.get(f"/problems/{problem_id}/posts/{post_id}/comments").json()
    assert comment_id in [c["id"] for c in comments_after]


def test_hide_comment_404_for_unknown_comment(client, db_session):
    problem_id, post_id, _, _, admin_headers = _setup_post_and_comment(client, db_session)
    resp = client.post(
        f"/problems/{problem_id}/posts/{post_id}/comments/does-not-exist/moderation/hide",
        json={"reason": None},
        headers=admin_headers,
    )
    assert resp.status_code == 404


# --- Moderation log ----------------------------------------------------------


def test_moderation_log_requires_admin(client, db_session):
    problem_id, post_id, _, member_headers, _ = _setup_post_and_comment(client, db_session)
    resp = client.get(f"/problems/{problem_id}/moderation-log", headers=member_headers)
    assert resp.status_code == 403

    resp_unauth = client.get(f"/problems/{problem_id}/moderation-log")
    assert resp_unauth.status_code == 401


def test_moderation_log_empty_when_no_overrides(client, db_session):
    problem_id, _, _, _, admin_headers = _setup_post_and_comment(client, db_session)
    resp = client.get(f"/problems/{problem_id}/moderation-log", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []
