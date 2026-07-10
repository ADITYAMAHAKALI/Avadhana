"""Integration tests for GET /marketplace/rfps/{rfp_id}/attribute-matches
(GitHub issue #66) — through the real HTTP layer.

Covers the happy path (hard-constraint filtering + weighted ranking
against real published Solutions) and the invite-only visibility gate,
which must behave identically to `GET /marketplace/rfps/{rfp_id}` (same
`rfp_visible_to_caller` gate, reused rather than reimplemented — see
`app.services.marketplace_service`).

There is no publish-toggle endpoint yet (Solutions are always created
with `status="draft"` — see `app/routers/marketplace/solutions.py`), so
tests here flip a Solution's `status` to "published" via a direct
session mutation, the same pattern already used in
`tests/integration/test_api_marketplace_solutions.py`'s
`test_publishing_always_succeeds_regardless_of_quota_state` for
mutating org quota state with no API surface of its own yet.
"""

from app.db.session import get_session
from app.main import app
from app.models.marketplace.solution import Solution


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


def _solution_payload(org_id, **overrides):
    payload = {
        "organizationId": org_id,
        "title": "Fleet Management Suite",
        "description": "Comprehensive vehicle tracking and maintenance scheduling.",
        "categoryTags": ["logistics", "fleet"],
    }
    payload.update(overrides)
    return payload


def _publish_solution(solution_id: str) -> None:
    """Direct row mutation — no publish endpoint exists yet. Mirrors the
    org-quota mutation pattern in test_api_marketplace_solutions.py."""
    override = app.dependency_overrides[get_session]
    session_gen = override()
    session = next(session_gen)
    try:
        solution = session.get(Solution, solution_id)
        solution.status = "published"
        session.commit()
    finally:
        session_gen.close()


def _add_requirement(client, headers, rfp_id, key, value, weight=1.0, hard=False):
    resp = client.post(
        f"/marketplace/rfps/{rfp_id}/requirements",
        json={
            "attributeKey": key,
            "attributeValue": value,
            "weight": weight,
            "isHardConstraint": hard,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _add_attribute(client, headers, solution_id, key, value):
    resp = client.post(
        f"/marketplace/solutions/{solution_id}/attributes",
        json={"attributeKey": key, "attributeValue": value},
        headers=headers,
    )
    assert resp.status_code == 201


def test_attribute_matches_happy_path_ranks_and_filters(client):
    buyer_headers, _ = _signup_and_auth_headers(client, email="buyer-match@example.com")
    buyer_org_id = _create_org(client, buyer_headers, name="Buyer Match Org")
    rfp_resp = client.post("/marketplace/rfps", json=_rfp_payload(buyer_org_id), headers=buyer_headers)
    rfp_id = rfp_resp.json()["id"]

    _add_requirement(client, buyer_headers, rfp_id, "certification", "ISO-27001", weight=1.0, hard=True)
    _add_requirement(client, buyer_headers, rfp_id, "industry", "logistics", weight=3.0)

    provider_headers, _ = _signup_and_auth_headers(client, email="provider-match@example.com")
    provider_org_id = _create_org(client, provider_headers, name="Provider Match Org")

    # Full match: has the hard constraint + the soft requirement. Published.
    full_match_resp = client.post(
        "/marketplace/solutions",
        json=_solution_payload(provider_org_id, title="Full Match Solution"),
        headers=provider_headers,
    )
    full_match_id = full_match_resp.json()["id"]
    _add_attribute(client, provider_headers, full_match_id, "certification", "ISO-27001")
    _add_attribute(client, provider_headers, full_match_id, "industry", "logistics")
    _publish_solution(full_match_id)

    # Fails the hard constraint entirely — must be excluded from results.
    no_cert_resp = client.post(
        "/marketplace/solutions",
        json=_solution_payload(provider_org_id, title="No Cert Solution"),
        headers=provider_headers,
    )
    no_cert_id = no_cert_resp.json()["id"]
    _add_attribute(client, provider_headers, no_cert_id, "industry", "logistics")
    _publish_solution(no_cert_id)

    # Has the hard constraint but not the soft one — survives, scores lower.
    partial_resp = client.post(
        "/marketplace/solutions",
        json=_solution_payload(provider_org_id, title="Partial Match Solution"),
        headers=provider_headers,
    )
    partial_id = partial_resp.json()["id"]
    _add_attribute(client, provider_headers, partial_id, "certification", "ISO-27001")
    _publish_solution(partial_id)

    # Matches everything but is still a draft — must be excluded.
    draft_resp = client.post(
        "/marketplace/solutions",
        json=_solution_payload(provider_org_id, title="Draft Solution"),
        headers=provider_headers,
    )
    draft_id = draft_resp.json()["id"]
    _add_attribute(client, provider_headers, draft_id, "certification", "ISO-27001")
    _add_attribute(client, provider_headers, draft_id, "industry", "logistics")
    # Deliberately NOT publishing this one.

    resp = client.get(f"/marketplace/rfps/{rfp_id}/attribute-matches")
    assert resp.status_code == 200
    body = resp.json()

    titles = [m["solution"]["title"] for m in body]
    assert "No Cert Solution" not in titles
    assert "Draft Solution" not in titles
    assert titles == ["Full Match Solution", "Partial Match Solution"]

    full_match = body[0]
    assert full_match["score"] == 1.0
    assert len(full_match["matchedRequirementIds"]) == 2

    partial = body[1]
    assert partial["score"] == 0.25  # 1.0 / (1.0 + 3.0)
    assert len(partial["matchedRequirementIds"]) == 1


def test_attribute_matches_for_invite_only_rfp_hidden_from_outsiders(client):
    buyer_headers, buyer_user_id = _signup_and_auth_headers(client, email="buyer-invite-match@example.com")
    buyer_org_id = _create_org(client, buyer_headers, name="Invite Match Org")
    rfp_resp = client.post(
        "/marketplace/rfps",
        json=_rfp_payload(buyer_org_id, title="Secret Matching RFP", visibility="invite_only"),
        headers=buyer_headers,
    )
    assert rfp_resp.status_code == 201
    rfp_id = rfp_resp.json()["id"]
    _add_requirement(client, buyer_headers, rfp_id, "industry", "logistics", weight=1.0)

    # Anonymous caller: 404, not leaked.
    anon_resp = client.get(f"/marketplace/rfps/{rfp_id}/attribute-matches")
    assert anon_resp.status_code == 404

    # Authenticated outsider (no membership in the posting org): also 404.
    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-match@example.com")
    outsider_resp = client.get(
        f"/marketplace/rfps/{rfp_id}/attribute-matches", headers=outsider_headers
    )
    assert outsider_resp.status_code == 404

    # Org member: allowed through (empty result list is fine — the point
    # is a 200, not a 404).
    member_resp = client.get(f"/marketplace/rfps/{rfp_id}/attribute-matches", headers=buyer_headers)
    assert member_resp.status_code == 200
    assert member_resp.json() == []


def test_attribute_matches_for_nonexistent_rfp_is_404(client):
    resp = client.get("/marketplace/rfps/does-not-exist/attribute-matches")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "RFP_NOT_FOUND"
