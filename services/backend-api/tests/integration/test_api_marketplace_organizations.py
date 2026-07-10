"""Integration tests for Organization creation and membership management
(GitHub issue #63) — through the real HTTP layer.
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


def test_create_organization_creator_is_admin(client):
    headers, user_id = _signup_and_auth_headers(client, email="founder@example.com")
    org_id = _create_org(client, headers, name="Acme Corp")

    resp = client.get(f"/marketplace/organizations/{org_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Acme Corp"
    assert body["rfpFreeQuotaUsed"] == 0
    assert body["rfpFreeQuotaLimit"] == 100
    assert body["billingStatus"] == "active"

    members_resp = client.get(f"/marketplace/organizations/{org_id}/members", headers=headers)
    assert members_resp.status_code == 200
    members = members_resp.json()
    assert len(members) == 1
    assert members[0]["userId"] == user_id
    assert members[0]["role"] == "admin"


def test_create_organization_requires_auth(client):
    resp = client.post("/marketplace/organizations", json={"name": "No Auth Co"})
    assert resp.status_code == 401


def test_list_my_organizations(client):
    headers, _ = _signup_and_auth_headers(client, email="multi-org@example.com")
    org_a = _create_org(client, headers, name="Org A")
    org_b = _create_org(client, headers, name="Org B")

    resp = client.get("/marketplace/organizations/mine", headers=headers)
    assert resp.status_code == 200
    ids = {o["id"] for o in resp.json()}
    assert ids == {org_a, org_b}


def test_admin_can_add_member(client):
    admin_headers, _ = _signup_and_auth_headers(client, email="admin@example.com")
    org_id = _create_org(client, admin_headers, name="Acme Corp")

    _, new_user_id = _signup_and_auth_headers(client, email="new-member@example.com")

    resp = client.post(
        f"/marketplace/organizations/{org_id}/members",
        json={"userId": new_user_id, "role": "member"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["userId"] == new_user_id
    assert body["role"] == "member"

    members_resp = client.get(f"/marketplace/organizations/{org_id}/members", headers=admin_headers)
    assert len(members_resp.json()) == 2


def test_non_admin_member_cannot_add_member(client):
    admin_headers, _ = _signup_and_auth_headers(client, email="admin2@example.com")
    org_id = _create_org(client, admin_headers, name="Acme Corp 2")

    member_headers, member_user_id = _signup_and_auth_headers(client, email="member2@example.com")
    add_resp = client.post(
        f"/marketplace/organizations/{org_id}/members",
        json={"userId": member_user_id, "role": "member"},
        headers=admin_headers,
    )
    assert add_resp.status_code == 201

    _, outsider_user_id = _signup_and_auth_headers(client, email="outsider2@example.com")
    resp = client.post(
        f"/marketplace/organizations/{org_id}/members",
        json={"userId": outsider_user_id, "role": "member"},
        headers=member_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_ORG_ADMIN"


def test_non_member_cannot_add_member(client):
    admin_headers, _ = _signup_and_auth_headers(client, email="admin3@example.com")
    org_id = _create_org(client, admin_headers, name="Acme Corp 3")

    outsider_headers, outsider_user_id = _signup_and_auth_headers(client, email="outsider3@example.com")
    resp = client.post(
        f"/marketplace/organizations/{org_id}/members",
        json={"userId": outsider_user_id, "role": "member"},
        headers=outsider_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_ORG_ADMIN"


def test_get_nonexistent_organization_is_404(client):
    headers, _ = _signup_and_auth_headers(client, email="lookup@example.com")
    resp = client.get("/marketplace/organizations/does-not-exist", headers=headers)
    assert resp.status_code == 404


def test_non_member_cannot_get_organization_detail(client):
    """Regression test for issue #84 (IDOR): a real, existing
    Organization must be invisible to a user who isn't a member of it —
    same 404 as a nonexistent one, so existence isn't leaked either."""
    owner_headers, _ = _signup_and_auth_headers(client, email="org-owner@example.com")
    org_id = _create_org(client, owner_headers, name="Private Co")

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider@example.com")
    resp = client.get(f"/marketplace/organizations/{org_id}", headers=outsider_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "ORGANIZATION_NOT_FOUND"


def test_non_member_cannot_list_organization_members(client):
    """Regression test for issue #84 (IDOR): the member roster (names,
    roles) must not be readable by a non-member."""
    owner_headers, _ = _signup_and_auth_headers(client, email="org-owner2@example.com")
    org_id = _create_org(client, owner_headers, name="Private Co 2")

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider2@example.com")
    resp = client.get(f"/marketplace/organizations/{org_id}/members", headers=outsider_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "ORGANIZATION_NOT_FOUND"
