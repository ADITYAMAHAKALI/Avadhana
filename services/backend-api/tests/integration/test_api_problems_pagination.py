"""Integration tests for GET /problems pagination (issue #76) and the
batched role-count query that backs it (issue #77 N+1 fix).

No dedicated test_api_problems.py existed before this pass (list_problems
previously returned everything unbounded, so there was nothing to page
through) — this file covers both the new limit/offset behavior and
verifies the batched `count_active_by_role_for_problems` call still
produces the exact same per-problem role counts as the old N+1 path did.
"""


def _signup_and_auth_headers(client, email="creator@example.com"):
    resp = client.post(
        "/auth/signup",
        json={"name": "Test User", "email": email, "password": "testpass123", "location": "Bengaluru"},
    )
    assert resp.status_code == 201
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


def _commit(client, headers, problem_id, role="thinker"):
    resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": role, "specialization": None},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_list_problems_default_limit_caps_at_20(client):
    headers = _signup_and_auth_headers(client, "creator-many@example.com")
    for i in range(25):
        _create_problem(client, headers, title=f"Problem {i}")

    resp = client.get("/problems")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 20


def test_list_problems_limit_and_offset_page_through_results(client):
    headers = _signup_and_auth_headers(client, "creator-page@example.com")
    # Created oldest-first; the API returns newest-first (created_at desc).
    titles = [f"PageProblem {i}" for i in range(5)]
    for title in titles:
        _create_problem(client, headers, title=title)

    page1 = client.get("/problems", params={"limit": 2, "offset": 0}).json()
    page2 = client.get("/problems", params={"limit": 2, "offset": 2}).json()
    page3 = client.get("/problems", params={"limit": 2, "offset": 4}).json()

    assert [p["title"] for p in page1] == ["PageProblem 4", "PageProblem 3"]
    assert [p["title"] for p in page2] == ["PageProblem 2", "PageProblem 1"]
    assert [p["title"] for p in page3] == ["PageProblem 0"]

    # No overlap between pages.
    all_ids = [p["id"] for p in page1 + page2 + page3]
    assert len(all_ids) == len(set(all_ids)) == 5


def test_list_problems_limit_is_capped_at_100(client):
    headers = _signup_and_auth_headers(client, "creator-cap@example.com")
    _create_problem(client, headers)

    resp = client.get("/problems", params={"limit": 500})
    assert resp.status_code == 422  # FastAPI Query(le=100) validation error


def test_list_problems_offset_beyond_results_is_empty(client):
    headers = _signup_and_auth_headers(client, "creator-empty@example.com")
    _create_problem(client, headers)

    resp = client.get("/problems", params={"offset": 1000})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_problems_role_counts_correct_across_a_page(client):
    """Regression test for the issue #77 N+1 fix: the batched
    count_active_by_role_for_problems call must produce identical
    per-problem role counts to what the old one-query-per-problem path
    returned."""
    thinker_headers = _signup_and_auth_headers(client, "thinker@example.com")
    actor_headers = _signup_and_auth_headers(client, "actor@example.com")
    backer_headers = _signup_and_auth_headers(client, "backer@example.com")

    problem_a = _create_problem(client, thinker_headers, title="Problem A")
    problem_b = _create_problem(client, thinker_headers, title="Problem B")

    _commit(client, thinker_headers, problem_a, role="thinker")
    _commit(client, actor_headers, problem_a, role="actor")
    _commit(client, backer_headers, problem_a, role="backer")
    _commit(client, actor_headers, problem_b, role="actor")

    resp = client.get("/problems", params={"limit": 100})
    assert resp.status_code == 200
    by_id = {p["id"]: p for p in resp.json()}

    assert by_id[problem_a]["thinkerCount"] == 1
    assert by_id[problem_a]["actorCount"] == 1
    assert by_id[problem_a]["backerCount"] == 1

    assert by_id[problem_b]["thinkerCount"] == 0
    assert by_id[problem_b]["actorCount"] == 1
    assert by_id[problem_b]["backerCount"] == 0
