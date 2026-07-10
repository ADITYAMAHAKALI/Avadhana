"""Integration tests for the community-promotion bridge (GitHub issue
#70): `POST /marketplace/rfps/{rfp_id}/promote` — through the real HTTP
layer. Covers the happy path (Problem created, RFP.promotedProblemId
set, Problem independently readable via GET /problems/{id}),
marketplace-only rejection, double-promotion rejection, non-member
rejection, and `resolution_mode: both` success.
"""


def _signup_and_auth_headers(client, email="user@example.com"):
    resp = client.post(
        "/auth/signup",
        json={"name": "Test User", "email": email, "password": "testpass123", "location": "Bengaluru"},
    )
    assert resp.status_code == 201
    token = resp.json()["token"]
    user_id = resp.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


def _create_org(client, headers, name="Acme Corp"):
    resp = client.post("/marketplace/organizations", json={"name": name}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def _rfp_payload(org_id, **overrides):
    payload = {
        "organizationId": org_id,
        "title": "Fix the municipal pothole backlog",
        "description": "Need a coordinated effort to fix potholes across 12 wards.",
        "industry": "civic-infrastructure",
        "geography": "Bengaluru",
        "resolutionMode": "community",
        "visibility": "public",
    }
    payload.update(overrides)
    return payload


def _create_rfp(client, headers, org_id, **overrides):
    resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id, **overrides), headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_promote_community_rfp_creates_problem(client):
    headers, user_id = _signup_and_auth_headers(client, email="promoter1@example.com")
    org_id = _create_org(client, headers, name="Promoter Org 1")
    rfp_id = _create_rfp(client, headers, org_id)

    resp = client.post(
        f"/marketplace/rfps/{rfp_id}/promote", json={"tier": "B"}, headers=headers
    )
    assert resp.status_code == 201
    problem = resp.json()

    assert problem["title"] == "Fix the municipal pothole backlog"
    assert problem["summary"] == "Need a coordinated effort to fix potholes across 12 wards."
    assert problem["location"] == "Bengaluru"
    assert problem["category"] == "civic-infrastructure"
    assert problem["tier"] == "B"
    assert problem["thinkerCount"] == 0
    assert problem["actorCount"] == 0
    assert problem["backerCount"] == 0

    # RFP.promotedProblemId is now set, pointing at the new Problem.
    rfp_resp = client.get(f"/marketplace/rfps/{rfp_id}")
    assert rfp_resp.status_code == 200
    assert rfp_resp.json()["promotedProblemId"] == problem["id"]

    # The Problem is independently readable via the normal civic
    # endpoint, exactly like any other problem — it "doesn't know or
    # care it came from the Marketplace" (CLAUDE.md).
    get_resp = client.get(f"/problems/{problem['id']}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == problem["id"]
    assert fetched["title"] == problem["title"]


def test_promote_marketplace_only_rfp_rejected(client):
    headers, _ = _signup_and_auth_headers(client, email="promoter2@example.com")
    org_id = _create_org(client, headers, name="Promoter Org 2")
    rfp_id = _create_rfp(client, headers, org_id, resolutionMode="marketplace")

    resp = client.post(
        f"/marketplace/rfps/{rfp_id}/promote", json={"tier": "B"}, headers=headers
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "RFP_NOT_COMMUNITY_RESOLVABLE"


def test_promote_already_promoted_rfp_rejected(client):
    headers, _ = _signup_and_auth_headers(client, email="promoter3@example.com")
    org_id = _create_org(client, headers, name="Promoter Org 3")
    rfp_id = _create_rfp(client, headers, org_id)

    first = client.post(
        f"/marketplace/rfps/{rfp_id}/promote", json={"tier": "C"}, headers=headers
    )
    assert first.status_code == 201
    first_problem_id = first.json()["id"]

    second = client.post(
        f"/marketplace/rfps/{rfp_id}/promote", json={"tier": "C"}, headers=headers
    )
    assert second.status_code == 409
    assert second.json()["detail"]["error"] == "RFP_ALREADY_PROMOTED"

    # No duplicate Problem was created — RFP still points at the first one.
    rfp_resp = client.get(f"/marketplace/rfps/{rfp_id}")
    assert rfp_resp.json()["promotedProblemId"] == first_problem_id


def test_promote_by_non_member_rejected(client):
    headers, _ = _signup_and_auth_headers(client, email="promoter4@example.com")
    org_id = _create_org(client, headers, name="Promoter Org 4")
    rfp_id = _create_rfp(client, headers, org_id)

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-promote@example.com")
    resp = client.post(
        f"/marketplace/rfps/{rfp_id}/promote", json={"tier": "B"}, headers=outsider_headers
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_ORG_MEMBER"


def test_promote_both_mode_rfp_succeeds(client):
    headers, _ = _signup_and_auth_headers(client, email="promoter5@example.com")
    org_id = _create_org(client, headers, name="Promoter Org 5")
    rfp_id = _create_rfp(client, headers, org_id, resolutionMode="both")

    resp = client.post(
        f"/marketplace/rfps/{rfp_id}/promote", json={"tier": "A"}, headers=headers
    )
    assert resp.status_code == 201
    assert resp.json()["tier"] == "A"

    rfp_resp = client.get(f"/marketplace/rfps/{rfp_id}")
    assert rfp_resp.json()["promotedProblemId"] == resp.json()["id"]


def test_promote_requires_auth(client):
    headers, _ = _signup_and_auth_headers(client, email="promoter6@example.com")
    org_id = _create_org(client, headers, name="Promoter Org 6")
    rfp_id = _create_rfp(client, headers, org_id)

    resp = client.post(f"/marketplace/rfps/{rfp_id}/promote", json={"tier": "B"})
    assert resp.status_code == 401


def test_promote_nonexistent_rfp_is_404(client):
    headers, _ = _signup_and_auth_headers(client, email="promoter7@example.com")
    resp = client.post(
        "/marketplace/rfps/does-not-exist/promote", json={"tier": "B"}, headers=headers
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "RFP_NOT_FOUND"
