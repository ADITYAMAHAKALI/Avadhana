"""Integration tests for RFP posting, requirements, and search (GitHub
issue #64) — through the real HTTP layer. Covers member-only posting,
requirement attach/list, and invite-only visibility filtering.
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
        "title": "Need a fleet management platform",
        "description": "Looking for a vendor to manage our municipal vehicle fleet.",
        "industry": "logistics",
        "geography": "Bengaluru",
        "resolutionMode": "marketplace",
        "visibility": "public",
    }
    payload.update(overrides)
    return payload


def test_org_member_can_create_rfp(client):
    headers, _ = _signup_and_auth_headers(client, email="buyer@example.com")
    org_id = _create_org(client, headers, name="Buyer Org")

    resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id), headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["organizationId"] == org_id
    assert body["status"] == "draft"
    assert body["isBillable"] is False
    assert body["promotedProblemId"] is None


def test_non_member_cannot_create_rfp(client):
    admin_headers, _ = _signup_and_auth_headers(client, email="buyer2@example.com")
    org_id = _create_org(client, admin_headers, name="Buyer Org 2")

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-rfp@example.com")
    resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id), headers=outsider_headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_ORG_MEMBER"


def test_create_rfp_requires_auth(client):
    headers, _ = _signup_and_auth_headers(client, email="buyer3@example.com")
    org_id = _create_org(client, headers, name="Buyer Org 3")

    resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id))
    assert resp.status_code == 401


def test_attach_and_list_requirements(client):
    headers, _ = _signup_and_auth_headers(client, email="buyer4@example.com")
    org_id = _create_org(client, headers, name="Buyer Org 4")
    rfp_resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id), headers=headers)
    rfp_id = rfp_resp.json()["id"]

    req_resp = client.post(
        f"/marketplace/rfps/{rfp_id}/requirements",
        json={
            "attributeKey": "certification",
            "attributeValue": "ISO27001",
            "weight": 2.0,
            "isHardConstraint": True,
        },
        headers=headers,
    )
    assert req_resp.status_code == 201
    assert req_resp.json()["isHardConstraint"] is True

    list_resp = client.get(f"/marketplace/rfps/{rfp_id}/requirements")
    assert list_resp.status_code == 200
    requirements = list_resp.json()
    assert len(requirements) == 1
    assert requirements[0]["attributeKey"] == "certification"


def test_non_member_cannot_attach_requirement(client):
    headers, _ = _signup_and_auth_headers(client, email="buyer5@example.com")
    org_id = _create_org(client, headers, name="Buyer Org 5")
    rfp_resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id), headers=headers)
    rfp_id = rfp_resp.json()["id"]

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-req@example.com")
    resp = client.post(
        f"/marketplace/rfps/{rfp_id}/requirements",
        json={"attributeKey": "k", "attributeValue": "v"},
        headers=outsider_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_ORG_MEMBER"


def test_public_rfp_visible_to_everyone(client):
    headers, _ = _signup_and_auth_headers(client, email="buyer6@example.com")
    org_id = _create_org(client, headers, name="Buyer Org 6")
    client.post("/marketplace/rfps", json=_rfp_payload(org_id, title="Public RFP"), headers=headers)

    # Unauthenticated list.
    resp = client.get("/marketplace/rfps")
    assert resp.status_code == 200
    titles = [r["title"] for r in resp.json()]
    assert "Public RFP" in titles


def test_invite_only_rfp_hidden_from_public_list_and_outsiders(client):
    headers, _ = _signup_and_auth_headers(client, email="buyer7@example.com")
    org_id = _create_org(client, headers, name="Buyer Org 7")
    create_resp = client.post(
        "/marketplace/rfps",
        json=_rfp_payload(org_id, title="Secret RFP", visibility="invite_only"),
        headers=headers,
    )
    assert create_resp.status_code == 201
    rfp_id = create_resp.json()["id"]

    # Unauthenticated list: must not appear.
    anon_list = client.get("/marketplace/rfps")
    assert "Secret RFP" not in [r["title"] for r in anon_list.json()]

    # Unauthenticated get: 404 (not leaked).
    anon_get = client.get(f"/marketplace/rfps/{rfp_id}")
    assert anon_get.status_code == 404

    # Outsider (authenticated, not a member of the posting org): also hidden.
    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-invite@example.com")
    outsider_list = client.get("/marketplace/rfps", headers=outsider_headers)
    assert "Secret RFP" not in [r["title"] for r in outsider_list.json()]
    outsider_get = client.get(f"/marketplace/rfps/{rfp_id}", headers=outsider_headers)
    assert outsider_get.status_code == 404

    # Org member: visible.
    member_list = client.get("/marketplace/rfps", headers=headers)
    assert "Secret RFP" in [r["title"] for r in member_list.json()]
    member_get = client.get(f"/marketplace/rfps/{rfp_id}", headers=headers)
    assert member_get.status_code == 200


def test_search_filters_by_industry(client):
    headers, _ = _signup_and_auth_headers(client, email="buyer8@example.com")
    org_id = _create_org(client, headers, name="Buyer Org 8")
    client.post(
        "/marketplace/rfps",
        json=_rfp_payload(org_id, title="Logistics RFP", industry="logistics"),
        headers=headers,
    )
    client.post(
        "/marketplace/rfps",
        json=_rfp_payload(org_id, title="Healthcare RFP", industry="healthcare"),
        headers=headers,
    )

    resp = client.get("/marketplace/rfps", params={"industry": "logistics"})
    titles = [r["title"] for r in resp.json()]
    assert "Logistics RFP" in titles
    assert "Healthcare RFP" not in titles


def test_get_nonexistent_rfp_is_404(client):
    resp = client.get("/marketplace/rfps/does-not-exist")
    assert resp.status_code == 404
