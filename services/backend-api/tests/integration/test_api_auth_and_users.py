"""Integration tests for signup/login and current-user endpoints,
exercised through the real HTTP layer (FastAPI TestClient) against the
in-memory SQLite database (see conftest.py)."""


def _signup(client, name="Ravi Menon", email="ravi@example.com", password="testpass123", location="Bengaluru"):
    return client.post(
        "/auth/signup",
        json={"name": name, "email": email, "password": password, "location": location},
    )


def test_signup_returns_token_and_user_shape(client):
    resp = _signup(client)
    assert resp.status_code == 201
    body = resp.json()
    assert "token" in body
    user = body["user"]
    assert user["name"] == "Ravi Menon"
    assert user["initials"] == "RM"
    assert user["reputation"] == 0
    assert user["avatarColor"].startswith("#")
    assert "memberSince" in user


def test_signup_duplicate_email_is_409(client):
    _signup(client, email="dup@example.com")
    resp2 = _signup(client, name="Other Name", email="dup@example.com")
    assert resp2.status_code == 409


def test_login_success(client):
    _signup(client, email="login@example.com", password="secretpass1")
    resp = client.post("/auth/login", json={"email": "login@example.com", "password": "secretpass1"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password_is_401(client):
    _signup(client, email="login2@example.com", password="secretpass1")
    resp = client.post("/auth/login", json={"email": "login2@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_email_is_401(client):
    resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert resp.status_code == 401


def test_get_me_requires_auth(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_get_me_with_valid_token(client):
    signup = _signup(client, name="Me User", email="me@example.com")
    token = signup.json()["token"]
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Me User"


def test_get_me_with_garbage_token_is_401(client):
    resp = client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_focus_slots_starts_at_zero_used(client):
    signup = _signup(client, email="slots@example.com")
    token = signup.json()["token"]
    resp = client.get("/users/me/focus-slots", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"used": 0, "total": 3}
