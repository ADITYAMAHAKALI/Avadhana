"""Integration tests for Solution publishing, attributes, and search
(GitHub issue #65) — through the real HTTP layer. Covers member-only
publishing (always free, regardless of any quota state) and
attribute attach/list.
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


def _solution_payload(org_id, **overrides):
    payload = {
        "organizationId": org_id,
        "title": "Fleet Management Suite",
        "description": "Comprehensive vehicle tracking and maintenance scheduling.",
        "categoryTags": ["logistics", "fleet"],
    }
    payload.update(overrides)
    return payload


def test_org_member_can_publish_solution(client):
    headers, _ = _signup_and_auth_headers(client, email="provider@example.com")
    org_id = _create_org(client, headers, name="Provider Org")

    resp = client.post("/marketplace/solutions", json=_solution_payload(org_id), headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["organizationId"] == org_id
    assert body["categoryTags"] == ["logistics", "fleet"]
    assert body["status"] == "draft"


def test_publishing_always_succeeds_regardless_of_quota_state(client):
    """Solution publishing has NO quota/billing gate — simulate an org
    whose rfp_free_quota_used has been exhausted (via direct row
    mutation, since no API sets this yet) and verify solution publishing
    is completely unaffected."""
    headers, _ = _signup_and_auth_headers(client, email="provider-quota@example.com")
    org_id = _create_org(client, headers, name="Quota-Exhausted Org")

    from app.db.session import get_session
    from app.main import app
    from app.models.marketplace.organization import Organization

    override = app.dependency_overrides[get_session]
    session_gen = override()
    session = next(session_gen)
    try:
        org = session.get(Organization, org_id)
        org.rfp_free_quota_used = org.rfp_free_quota_limit  # fully exhausted
        session.commit()
    finally:
        session_gen.close()

    resp = client.post("/marketplace/solutions", json=_solution_payload(org_id), headers=headers)
    assert resp.status_code == 201


def test_non_member_cannot_publish_solution(client):
    admin_headers, _ = _signup_and_auth_headers(client, email="provider2@example.com")
    org_id = _create_org(client, admin_headers, name="Provider Org 2")

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-sol@example.com")
    resp = client.post(
        "/marketplace/solutions", json=_solution_payload(org_id), headers=outsider_headers
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_ORG_MEMBER"


def test_publish_solution_requires_auth(client):
    headers, _ = _signup_and_auth_headers(client, email="provider3@example.com")
    org_id = _create_org(client, headers, name="Provider Org 3")

    resp = client.post("/marketplace/solutions", json=_solution_payload(org_id))
    assert resp.status_code == 401


def test_attach_and_list_attributes(client):
    headers, _ = _signup_and_auth_headers(client, email="provider4@example.com")
    org_id = _create_org(client, headers, name="Provider Org 4")
    sol_resp = client.post("/marketplace/solutions", json=_solution_payload(org_id), headers=headers)
    solution_id = sol_resp.json()["id"]

    attr_resp = client.post(
        f"/marketplace/solutions/{solution_id}/attributes",
        json={"attributeKey": "certification", "attributeValue": "ISO27001"},
        headers=headers,
    )
    assert attr_resp.status_code == 201

    list_resp = client.get(f"/marketplace/solutions/{solution_id}/attributes")
    assert list_resp.status_code == 200
    attributes = list_resp.json()
    assert len(attributes) == 1
    assert attributes[0]["attributeKey"] == "certification"


def test_non_member_cannot_attach_attribute(client):
    headers, _ = _signup_and_auth_headers(client, email="provider5@example.com")
    org_id = _create_org(client, headers, name="Provider Org 5")
    sol_resp = client.post("/marketplace/solutions", json=_solution_payload(org_id), headers=headers)
    solution_id = sol_resp.json()["id"]

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-attr@example.com")
    resp = client.post(
        f"/marketplace/solutions/{solution_id}/attributes",
        json={"attributeKey": "k", "attributeValue": "v"},
        headers=outsider_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_ORG_MEMBER"


def test_search_by_category_tag(client):
    headers, _ = _signup_and_auth_headers(client, email="provider6@example.com")
    org_id = _create_org(client, headers, name="Provider Org 6")
    client.post(
        "/marketplace/solutions",
        json=_solution_payload(org_id, title="Logistics Tool", categoryTags=["logistics"]),
        headers=headers,
    )
    client.post(
        "/marketplace/solutions",
        json=_solution_payload(org_id, title="Health Tool", categoryTags=["healthcare"]),
        headers=headers,
    )

    resp = client.get("/marketplace/solutions", params={"categoryTag": "logistics"})
    titles = [s["title"] for s in resp.json()]
    assert "Logistics Tool" in titles
    assert "Health Tool" not in titles


def test_search_by_organization(client):
    headers, _ = _signup_and_auth_headers(client, email="provider7@example.com")
    org_a = _create_org(client, headers, name="Org A Solutions")
    org_b = _create_org(client, headers, name="Org B Solutions")
    client.post(
        "/marketplace/solutions", json=_solution_payload(org_a, title="A Solution"), headers=headers
    )
    client.post(
        "/marketplace/solutions", json=_solution_payload(org_b, title="B Solution"), headers=headers
    )

    resp = client.get("/marketplace/solutions", params={"organizationId": org_a})
    titles = [s["title"] for s in resp.json()]
    assert titles == ["A Solution"]


def test_get_nonexistent_solution_is_404(client):
    resp = client.get("/marketplace/solutions/does-not-exist")
    assert resp.status_code == 404


def test_search_solutions_default_limit_caps_at_20(client):
    headers, _ = _signup_and_auth_headers(client, email="provider-many@example.com")
    org_id = _create_org(client, headers, name="Provider Org Many")
    for i in range(25):
        client.post(
            "/marketplace/solutions",
            json=_solution_payload(org_id, title=f"Solution {i}"),
            headers=headers,
        )

    resp = client.get("/marketplace/solutions")
    assert resp.status_code == 200
    assert len(resp.json()) == 20


def test_search_solutions_limit_and_offset_page_through_results(client):
    headers, _ = _signup_and_auth_headers(client, email="provider-page@example.com")
    org_id = _create_org(client, headers, name="Provider Org Page")
    for i in range(5):
        client.post(
            "/marketplace/solutions",
            json=_solution_payload(org_id, title=f"PageSolution {i}"),
            headers=headers,
        )

    page1 = client.get("/marketplace/solutions", params={"limit": 2, "offset": 0}).json()
    page2 = client.get("/marketplace/solutions", params={"limit": 2, "offset": 2}).json()

    assert [s["title"] for s in page1] == ["PageSolution 4", "PageSolution 3"]
    assert [s["title"] for s in page2] == ["PageSolution 2", "PageSolution 1"]
    assert not set(s["id"] for s in page1) & set(s["id"] for s in page2)


def test_search_solutions_limit_is_capped_at_100(client):
    resp = client.get("/marketplace/solutions", params={"limit": 500})
    assert resp.status_code == 422


def test_search_solutions_category_tag_pagination_is_consistent(client):
    """category_tag filtering happens in Python (JSON column, no
    cross-DB containment operator — see SqlAlchemySolutionRepo.search),
    so this proves limit/offset still behave correctly against the
    FILTERED set, not the raw unfiltered query — i.e. a page never comes
    back short because non-matching rows consumed the SQL-level window."""
    headers, _ = _signup_and_auth_headers(client, email="provider-tagpage@example.com")
    org_id = _create_org(client, headers, name="Provider Org TagPage")

    # Interleave matching and non-matching solutions so a naive
    # SQL-first-then-filter approach would produce a short/wrong page.
    for i in range(6):
        tag = "logistics" if i % 2 == 0 else "unrelated"
        client.post(
            "/marketplace/solutions",
            json=_solution_payload(org_id, title=f"Tagged {i}", categoryTags=[tag]),
            headers=headers,
        )

    resp_all = client.get("/marketplace/solutions", params={"categoryTag": "logistics", "limit": 10})
    assert resp_all.status_code == 200
    all_matches = resp_all.json()
    assert len(all_matches) == 3
    assert all("logistics" in s["categoryTags"] for s in all_matches)

    page1 = client.get(
        "/marketplace/solutions", params={"categoryTag": "logistics", "limit": 2, "offset": 0}
    ).json()
    page2 = client.get(
        "/marketplace/solutions", params={"categoryTag": "logistics", "limit": 2, "offset": 2}
    ).json()

    assert len(page1) == 2
    assert len(page2) == 1
    assert not set(s["id"] for s in page1) & set(s["id"] for s in page2)
    combined_ids = {s["id"] for s in page1} | {s["id"] for s in page2}
    assert combined_ids == {s["id"] for s in all_matches}
