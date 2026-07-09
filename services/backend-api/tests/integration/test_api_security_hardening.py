"""Integration tests for the security-hardening pass (TODO.md Security
Checklist): rate limiting on auth endpoints and CORS configuration.

Rate limiting: `tests/integration/conftest.py` disables the limiter on
the default `client` fixture (since most tests call /auth/signup many
times per module, all appearing to come from the same TestClient "IP").
This file uses the separate `rate_limited_client` fixture, which leaves
the limiter enabled, to exercise the real 429 behavior in isolation.

CORS: `CORS_ALLOWED_ORIGIN` is unset in the test environment (see
conftest.py's os.environ.setdefault calls — it only sets DATABASE_URL
and JWT_SECRET), so `Settings.cors_allowed_origins` falls back to its
local-dev default (`http://localhost:5173`, Vite's default dev port).
"""


def test_login_rate_limited_after_repeated_requests(rate_limited_client):
    # Seed a real user so the requests exercise the actual login path
    # (wrong-password branch) rather than an unrelated 404/422 short
    # circuit before the rate limiter even gets a chance to reject.
    rate_limited_client.post(
        "/auth/signup",
        json={
            "name": "Rate Limited User",
            "email": "ratelimited@example.com",
            "password": "testpass123",
            "location": "Bengaluru",
        },
    )

    payload = {"email": "ratelimited@example.com", "password": "wrong-password"}
    statuses = [
        rate_limited_client.post("/auth/login", json=payload).status_code for _ in range(5)
    ]
    # First 5/minute requests go through to the real handler (401 for bad
    # credentials); the limit is on request count, not outcome.
    assert all(s == 401 for s in statuses)

    # The 6th request within the same minute is rejected by the limiter,
    # not by the login handler.
    resp = rate_limited_client.post("/auth/login", json=payload)
    assert resp.status_code == 429


def test_signup_rate_limited_after_repeated_requests(rate_limited_client):
    statuses = []
    for i in range(5):
        resp = rate_limited_client.post(
            "/auth/signup",
            json={
                "name": "User",
                "email": f"burst{i}@example.com",
                "password": "testpass123",
                "location": "Bengaluru",
            },
        )
        statuses.append(resp.status_code)
    assert all(s == 201 for s in statuses)

    resp = rate_limited_client.post(
        "/auth/signup",
        json={
            "name": "User",
            "email": "burst-over-limit@example.com",
            "password": "testpass123",
            "location": "Bengaluru",
        },
    )
    assert resp.status_code == 429


def test_general_api_not_rate_limited_at_auth_endpoint_thresholds(rate_limited_client):
    # The general default limit (60/minute) is far looser than the auth
    # limit (5/minute) — a handful of reads against a public GET endpoint
    # should never trip it.
    for _ in range(10):
        resp = rate_limited_client.get("/problems")
        assert resp.status_code == 200


def test_cors_headers_reflect_configured_dev_origin(client):
    resp = client.get(
        "/problems",
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unlisted_origin(client):
    # A preflight request from an origin NOT in the allowed list should
    # not receive an Access-Control-Allow-Origin header for that origin.
    resp = client.options(
        "/problems",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example.com"
