"""Integration tests for problem creation, commitments, and checkpoints
through the real HTTP layer — proves the 3-slot limit and 90-day lock
are enforced end-to-end (router -> service -> ORM -> SQLite), not just
at the service-layer unit-test level.
"""


def _signup_and_auth_headers(client, email="user@example.com"):
    resp = client.post(
        "/auth/signup",
        json={"name": "Test User", "email": email, "password": "testpass123", "location": "Bengaluru"},
    )
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _create_problem(client, headers, title="A problem"):
    resp = client.post(
        "/problems",
        json={"title": title, "summary": "Summary text", "location": "Bengaluru", "category": "civic", "tier": "C"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_problem_creation_and_public_read(client):
    headers = _signup_and_auth_headers(client, email="creator@example.com")
    problem_id = _create_problem(client, headers)

    # GET is public — no auth header.
    resp = client.get(f"/problems/{problem_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["parentProblemTitle"] is None
    assert body["followingCount"] == 0
    assert body["thinkerCount"] == 0


def test_get_nonexistent_problem_is_404(client):
    resp = client.get("/problems/does-not-exist")
    assert resp.status_code == 404


def test_problem_list_is_public_and_searchable(client):
    headers = _signup_and_auth_headers(client, email="searcher@example.com")
    _create_problem(client, headers, title="Streetlight repair")
    _create_problem(client, headers, title="Water supply issue")

    resp = client.get("/problems", params={"q": "streetlight"})
    assert resp.status_code == 200
    titles = [p["title"] for p in resp.json()]
    assert "Streetlight repair" in titles
    assert "Water supply issue" not in titles


def test_exactly_three_commitments_allowed_fourth_is_409(client):
    headers = _signup_and_auth_headers(client, email="sloty@example.com")
    problem_ids = [_create_problem(client, headers, title=f"Problem {i}") for i in range(4)]

    for pid in problem_ids[:3]:
        resp = client.post(
            f"/problems/{pid}/commitments",
            json={"role": "thinker", "specialization": None},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "active"

    resp = client.get("/users/me/focus-slots", headers=headers)
    assert resp.json() == {"used": 3, "total": 3}

    # 4th commitment must be hard-blocked, not soft-discouraged.
    resp = client.post(
        f"/problems/{problem_ids[3]}/commitments",
        json={"role": "thinker", "specialization": None},
        headers=headers,
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["error"] == "SLOT_LIMIT_EXCEEDED"
    assert detail["used"] == 3
    assert detail["total"] == 3


def test_double_commit_to_same_problem_is_409(client):
    headers = _signup_and_auth_headers(client, email="double@example.com")
    problem_id = _create_problem(client, headers)

    resp1 = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "thinker", "specialization": None},
        headers=headers,
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "actor", "specialization": "Legal"},
        headers=headers,
    )
    assert resp2.status_code == 409
    assert resp2.json()["detail"]["error"] == "ALREADY_COMMITTED"


def test_commit_to_nonexistent_problem_is_404(client):
    headers = _signup_and_auth_headers(client, email="ghost@example.com")
    resp = client.post(
        "/problems/does-not-exist/commitments",
        json={"role": "thinker", "specialization": None},
        headers=headers,
    )
    assert resp.status_code == 404


def test_specialization_only_valid_for_actor_role(client):
    headers = _signup_and_auth_headers(client, email="spec@example.com")
    problem_id = _create_problem(client, headers)

    # thinker + specialization -> 422
    resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "thinker", "specialization": "Legal"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_checkpoint_before_90_days_is_409_lock_active(client):
    headers = _signup_and_auth_headers(client, email="locked@example.com")
    problem_id = _create_problem(client, headers)

    resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "thinker", "specialization": None},
        headers=headers,
    )
    commitment_id = resp.json()["id"]

    resp2 = client.post(
        f"/commitments/{commitment_id}/checkpoint",
        json={"action": "resolve", "note": "Done already?"},
        headers=headers,
    )
    assert resp2.status_code == 409
    detail = resp2.json()["detail"]
    assert detail["error"] == "LOCK_ACTIVE"
    assert detail["daysRemaining"] > 0


def test_checkpoint_owner_only(client):
    headers1 = _signup_and_auth_headers(client, email="owner1@example.com")
    headers2 = _signup_and_auth_headers(client, email="owner2@example.com")
    problem_id = _create_problem(client, headers1)

    resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "thinker", "specialization": None},
        headers=headers1,
    )
    commitment_id = resp.json()["id"]

    resp2 = client.post(
        f"/commitments/{commitment_id}/checkpoint",
        json={"action": "resolve", "note": None},
        headers=headers2,
    )
    assert resp2.status_code == 403


def test_checkpoints_list_requires_ownership(client):
    headers1 = _signup_and_auth_headers(client, email="cpowner1@example.com")
    headers2 = _signup_and_auth_headers(client, email="cpowner2@example.com")
    problem_id = _create_problem(client, headers1)

    resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": "backer", "specialization": None},
        headers=headers1,
    )
    commitment_id = resp.json()["id"]

    resp_owner = client.get(f"/commitments/{commitment_id}/checkpoints", headers=headers1)
    assert resp_owner.status_code == 200
    assert len(resp_owner.json()) == 1
    assert resp_owner.json()[0]["eventType"] == "created"

    resp_other = client.get(f"/commitments/{commitment_id}/checkpoints", headers=headers2)
    assert resp_other.status_code == 403
