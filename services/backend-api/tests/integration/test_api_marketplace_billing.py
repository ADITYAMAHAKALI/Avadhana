"""Integration tests for the RFP free-quota tracking + billing paywall
gate (GitHub issue #71) and the Organization-creation rate limit (GitHub
issue #73) — through the real HTTP layer.

Rate limiting: uses the `rate_limited_client` fixture (see
tests/integration/conftest.py and test_api_security_hardening.py for the
established pattern) — the default `client` fixture disables the limiter
so most tests aren't sensitive to burst request counts.
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


def _set_quota_used(org_id, used):
    """Directly mutates Organization.rfp_free_quota_used via the test
    session override — same technique already used by
    test_api_marketplace_solutions.py::test_publishing_always_succeeds_regardless_of_quota_state
    to seed quota state without needing 100+ real RFP creations."""
    from app.db.session import get_session
    from app.main import app
    from app.models.marketplace.organization import Organization

    override = app.dependency_overrides[get_session]
    session_gen = override()
    session = next(session_gen)
    try:
        org = session.get(Organization, org_id)
        org.rfp_free_quota_used = used
        session.commit()
    finally:
        session_gen.close()


# --- Quota tracking + paywall gate (issue #71) -----------------------------


def test_rfp_creation_under_quota_logs_free_event_and_is_not_billable(client):
    headers, _ = _signup_and_auth_headers(client, email="billing-under@example.com")
    org_id = _create_org(client, headers, name="Under Quota Org")

    resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id), headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["isBillable"] is False

    org_resp = client.get(f"/marketplace/organizations/{org_id}", headers=headers)
    assert org_resp.json()["rfpFreeQuotaUsed"] == 1

    events_resp = client.get(f"/marketplace/organizations/{org_id}/billing-events", headers=headers)
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) == 1
    assert events[0]["eventType"] == "free_rfp_posted"
    assert events[0]["rfpId"] == body["id"]
    assert events[0]["organizationId"] == org_id


def test_rfp_creation_over_quota_sets_billable_and_logs_billable_event(client):
    headers, _ = _signup_and_auth_headers(client, email="billing-over@example.com")
    org_id = _create_org(client, headers, name="Over Quota Org")

    # Seed the counter at the limit so the very next RFP crosses it,
    # rather than creating 100+ real RFPs.
    _set_quota_used(org_id, 100)

    resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id), headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["isBillable"] is True

    org_resp = client.get(f"/marketplace/organizations/{org_id}", headers=headers)
    assert org_resp.json()["rfpFreeQuotaUsed"] == 101

    events_resp = client.get(f"/marketplace/organizations/{org_id}/billing-events", headers=headers)
    events = events_resp.json()
    assert len(events) == 1
    assert events[0]["eventType"] == "billable_rfp_posted"


def test_quota_increments_across_multiple_rfps_and_events_are_newest_first(client):
    headers, _ = _signup_and_auth_headers(client, email="billing-multi@example.com")
    org_id = _create_org(client, headers, name="Multi RFP Org")

    first = client.post(
        "/marketplace/rfps", json=_rfp_payload(org_id, title="First RFP"), headers=headers
    )
    second = client.post(
        "/marketplace/rfps", json=_rfp_payload(org_id, title="Second RFP"), headers=headers
    )
    assert first.status_code == 201
    assert second.status_code == 201

    org_resp = client.get(f"/marketplace/organizations/{org_id}", headers=headers)
    assert org_resp.json()["rfpFreeQuotaUsed"] == 2

    events_resp = client.get(f"/marketplace/organizations/{org_id}/billing-events", headers=headers)
    events = events_resp.json()
    assert len(events) == 2
    # Newest first.
    assert events[0]["rfpId"] == second.json()["id"]
    assert events[1]["rfpId"] == first.json()["id"]


def test_rfp_creation_is_never_blocked_by_quota(client):
    """CLAUDE.md 'Monetization': this phase only needs quota tracking and
    the paywall flag — no payment processor exists to actually charge
    anyone, so RFP creation past the free quota must still succeed
    (201), just flagged billable."""
    headers, _ = _signup_and_auth_headers(client, email="billing-never-blocked@example.com")
    org_id = _create_org(client, headers, name="Never Blocked Org")
    _set_quota_used(org_id, 500)

    resp = client.post("/marketplace/rfps", json=_rfp_payload(org_id), headers=headers)
    assert resp.status_code == 201
    assert resp.json()["isBillable"] is True


def test_solution_creation_never_touches_quota_or_logs_billing_event(client):
    """Explicit non-goal per CLAUDE.md 'Monetization': Solution publishing
    is ALWAYS free. Regression guard alongside
    test_api_marketplace_solutions.py::test_publishing_always_succeeds_regardless_of_quota_state
    — this asserts the billing-event side specifically."""
    headers, _ = _signup_and_auth_headers(client, email="billing-solution@example.com")
    org_id = _create_org(client, headers, name="Solution Only Org")
    _set_quota_used(org_id, 100)

    resp = client.post(
        "/marketplace/solutions",
        json={
            "organizationId": org_id,
            "title": "Fleet Management Suite",
            "description": "Vehicle tracking and maintenance scheduling.",
            "categoryTags": ["logistics"],
        },
        headers=headers,
    )
    assert resp.status_code == 201

    org_resp = client.get(f"/marketplace/organizations/{org_id}", headers=headers)
    # Unchanged from the seeded value — Solution creation must not
    # increment the RFP quota counter.
    assert org_resp.json()["rfpFreeQuotaUsed"] == 100

    events_resp = client.get(f"/marketplace/organizations/{org_id}/billing-events", headers=headers)
    assert events_resp.json() == []


# --- Billing-events endpoint admin gate ------------------------------------


def test_billing_events_endpoint_is_admin_gated(client):
    admin_headers, _ = _signup_and_auth_headers(client, email="billing-admin@example.com")
    org_id = _create_org(client, admin_headers, name="Gated Org")
    client.post("/marketplace/rfps", json=_rfp_payload(org_id), headers=admin_headers)

    member_headers, member_user_id = _signup_and_auth_headers(
        client, email="billing-member@example.com"
    )
    add_resp = client.post(
        f"/marketplace/organizations/{org_id}/members",
        json={"userId": member_user_id, "role": "member"},
        headers=admin_headers,
    )
    assert add_resp.status_code == 201

    member_resp = client.get(
        f"/marketplace/organizations/{org_id}/billing-events", headers=member_headers
    )
    assert member_resp.status_code == 403
    assert member_resp.json()["detail"]["error"] == "NOT_ORG_ADMIN"

    outsider_headers, _ = _signup_and_auth_headers(client, email="billing-outsider@example.com")
    outsider_resp = client.get(
        f"/marketplace/organizations/{org_id}/billing-events", headers=outsider_headers
    )
    assert outsider_resp.status_code == 403
    assert outsider_resp.json()["detail"]["error"] == "NOT_ORG_ADMIN"

    admin_resp = client.get(
        f"/marketplace/organizations/{org_id}/billing-events", headers=admin_headers
    )
    assert admin_resp.status_code == 200
    assert len(admin_resp.json()) == 1


def test_billing_events_requires_auth(client):
    headers, _ = _signup_and_auth_headers(client, email="billing-auth@example.com")
    org_id = _create_org(client, headers, name="Auth Required Org")

    resp = client.get(f"/marketplace/organizations/{org_id}/billing-events")
    assert resp.status_code == 401


def test_billing_events_for_nonexistent_organization_is_404(client):
    headers, _ = _signup_and_auth_headers(client, email="billing-404@example.com")
    resp = client.get(
        "/marketplace/organizations/does-not-exist/billing-events", headers=headers
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "ORGANIZATION_NOT_FOUND"


# --- Organization-creation rate limit (issue #73) --------------------------


def test_organization_creation_rate_limited_after_repeated_requests(rate_limited_client):
    headers, _ = _signup_and_auth_headers(rate_limited_client, email="abuse-user@example.com")

    statuses = [
        rate_limited_client.post(
            "/marketplace/organizations", json={"name": f"Org {i}"}, headers=headers
        ).status_code
        for i in range(10)
    ]
    assert all(s == 201 for s in statuses)

    resp = rate_limited_client.post(
        "/marketplace/organizations", json={"name": "Org 11"}, headers=headers
    )
    assert resp.status_code == 429


def test_organization_creation_rate_limit_is_per_user_not_global(rate_limited_client):
    """Keyed per authenticated user (app.core.rate_limit._user_or_ip_key):
    a second user's requests must not be blocked by the first user's
    burst, proving this isn't a single shared IP-wide bucket in the test
    client (which would make the mitigation useless the moment two real
    users share a NAT/office IP)."""
    headers_a, _ = _signup_and_auth_headers(rate_limited_client, email="abuse-user-a@example.com")
    for i in range(10):
        resp = rate_limited_client.post(
            "/marketplace/organizations", json={"name": f"A Org {i}"}, headers=headers_a
        )
        assert resp.status_code == 201
    exhausted = rate_limited_client.post(
        "/marketplace/organizations", json={"name": "A Org Over"}, headers=headers_a
    )
    assert exhausted.status_code == 429

    headers_b, _ = _signup_and_auth_headers(rate_limited_client, email="abuse-user-b@example.com")
    resp_b = rate_limited_client.post(
        "/marketplace/organizations", json={"name": "B Org"}, headers=headers_b
    )
    assert resp_b.status_code == 201
