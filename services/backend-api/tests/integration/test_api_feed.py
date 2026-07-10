"""Integration tests for commitment-gated voice on the problem feed
(posts/comments/likes) — CLAUDE.md constraint #3: "only users with an
ACTIVE commitment on a problem can post/comment/like on it."

Covers the full 401-vs-403-vs-200 matrix:
  - unauthenticated -> 401
  - authenticated but not committed -> 403 NOT_COMMITTED
  - authenticated and committed -> 200/201
  - GET endpoints -> 200 with no auth at all (share-link / visitor flow)
"""


def _signup_and_auth_headers(client, email):
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
    return resp.json()["id"]


def _commit(client, headers, problem_id, role="thinker", specialization=None):
    resp = client.post(
        f"/problems/{problem_id}/commitments",
        json={"role": role, "specialization": specialization},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_post_requires_auth_401_without_token(client):
    headers = _signup_and_auth_headers(client, "creator1@example.com")
    problem_id = _create_problem(client, headers)

    resp = client.post(f"/problems/{problem_id}/posts", json={"body": "hello"})
    assert resp.status_code == 401


def test_post_requires_commitment_403_for_authenticated_non_member(client):
    creator_headers = _signup_and_auth_headers(client, "creator2@example.com")
    problem_id = _create_problem(client, creator_headers)

    visitor_headers = _signup_and_auth_headers(client, "visitor@example.com")
    resp = client.post(f"/problems/{problem_id}/posts", json={"body": "hello"}, headers=visitor_headers)
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error"] == "NOT_COMMITTED"
    # Message must be explicit enough for a frontend to show directly.
    assert "committed members" in detail["message"].lower()


def test_committed_member_can_post(client):
    headers = _signup_and_auth_headers(client, "member1@example.com")
    problem_id = _create_problem(client, headers)
    _commit(client, headers, problem_id, role="actor", specialization="Legal")

    resp = client.post(f"/problems/{problem_id}/posts", json={"body": "Filed the RTI"}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["roleLabel"] == "Actor"
    assert body["timeAgo"] == "just now"
    assert body["likeCount"] == 0


def test_get_posts_is_public_no_auth_needed(client):
    headers = _signup_and_auth_headers(client, "member2@example.com")
    problem_id = _create_problem(client, headers)
    _commit(client, headers, problem_id)
    client.post(f"/problems/{problem_id}/posts", json={"body": "Visible to all"}, headers=headers)

    resp = client.get(f"/problems/{problem_id}/posts")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["body"] == "Visible to all"


def test_like_requires_commitment(client):
    creator_headers = _signup_and_auth_headers(client, "creator3@example.com")
    problem_id = _create_problem(client, creator_headers)
    _commit(client, creator_headers, problem_id)
    post = client.post(f"/problems/{problem_id}/posts", json={"body": "Post"}, headers=creator_headers).json()

    visitor_headers = _signup_and_auth_headers(client, "visitor2@example.com")
    resp = client.post(f"/problems/{problem_id}/posts/{post['id']}/like", headers=visitor_headers)
    assert resp.status_code == 403

    resp_unauth = client.post(f"/problems/{problem_id}/posts/{post['id']}/like")
    assert resp_unauth.status_code == 401


def test_like_toggle_via_api(client):
    headers = _signup_and_auth_headers(client, "liker@example.com")
    problem_id = _create_problem(client, headers)
    _commit(client, headers, problem_id)
    post = client.post(f"/problems/{problem_id}/posts", json={"body": "Post"}, headers=headers).json()

    resp1 = client.post(f"/problems/{problem_id}/posts/{post['id']}/like", headers=headers)
    assert resp1.json() == {"likeCount": 1}

    resp2 = client.post(f"/problems/{problem_id}/posts/{post['id']}/like", headers=headers)
    assert resp2.json() == {"likeCount": 0}


def test_comment_requires_commitment_and_public_read(client):
    creator_headers = _signup_and_auth_headers(client, "creator4@example.com")
    problem_id = _create_problem(client, creator_headers)
    _commit(client, creator_headers, problem_id)
    post = client.post(f"/problems/{problem_id}/posts", json={"body": "Post"}, headers=creator_headers).json()

    visitor_headers = _signup_and_auth_headers(client, "visitor3@example.com")
    resp = client.post(
        f"/problems/{problem_id}/posts/{post['id']}/comments",
        json={"body": "off-topic comment"},
        headers=visitor_headers,
    )
    assert resp.status_code == 403

    resp_ok = client.post(
        f"/problems/{problem_id}/posts/{post['id']}/comments",
        json={"body": "on-topic comment"},
        headers=creator_headers,
    )
    assert resp_ok.status_code == 201
    assert resp_ok.json()["roleLabel"] == "Thinker"

    # Public read, no auth.
    resp_read = client.get(f"/problems/{problem_id}/posts/{post['id']}/comments")
    assert resp_read.status_code == 200
    assert len(resp_read.json()) == 1


def test_list_posts_default_limit_caps_at_20(client):
    headers = _signup_and_auth_headers(client, "poster-many@example.com")
    problem_id = _create_problem(client, headers)
    _commit(client, headers, problem_id)
    for i in range(25):
        client.post(f"/problems/{problem_id}/posts", json={"body": f"Post {i}"}, headers=headers)

    resp = client.get(f"/problems/{problem_id}/posts")
    assert resp.status_code == 200
    assert len(resp.json()) == 20


def test_list_posts_limit_and_offset_page_through_results(client):
    headers = _signup_and_auth_headers(client, "poster-page@example.com")
    problem_id = _create_problem(client, headers)
    _commit(client, headers, problem_id)
    for i in range(5):
        client.post(f"/problems/{problem_id}/posts", json={"body": f"PagePost {i}"}, headers=headers)

    page1 = client.get(f"/problems/{problem_id}/posts", params={"limit": 2, "offset": 0}).json()
    page2 = client.get(f"/problems/{problem_id}/posts", params={"limit": 2, "offset": 2}).json()

    assert [p["body"] for p in page1] == ["PagePost 4", "PagePost 3"]
    assert [p["body"] for p in page2] == ["PagePost 2", "PagePost 1"]
    assert not set(p["id"] for p in page1) & set(p["id"] for p in page2)


def test_list_posts_batched_authors_and_like_counts_are_correct(client):
    """Regression test for the issue #77 N+1 fix: batching the author
    lookup (UserRepoPort.get_by_ids) and like-count lookup
    (FeedRepoPort.like_counts_for_posts) must produce identical
    per-post author names / like counts to what the old
    one-query-per-post path returned."""
    alice_headers = _signup_and_auth_headers(client, "alice-batch@example.com")
    bob_headers = _signup_and_auth_headers(client, "bob-batch@example.com")
    problem_id = _create_problem(client, alice_headers)
    _commit(client, alice_headers, problem_id, role="thinker")
    _commit(client, bob_headers, problem_id, role="actor")

    post_a = client.post(
        f"/problems/{problem_id}/posts", json={"body": "Alice's post"}, headers=alice_headers
    ).json()
    post_b = client.post(
        f"/problems/{problem_id}/posts", json={"body": "Bob's post"}, headers=bob_headers
    ).json()

    # Two likes on post_a (from both members), none on post_b.
    client.post(f"/problems/{problem_id}/posts/{post_a['id']}/like", headers=alice_headers)
    client.post(f"/problems/{problem_id}/posts/{post_a['id']}/like", headers=bob_headers)

    resp = client.get(f"/problems/{problem_id}/posts")
    assert resp.status_code == 200
    by_id = {p["id"]: p for p in resp.json()}

    assert by_id[post_a["id"]]["authorName"] == "Test User"
    assert by_id[post_a["id"]]["roleLabel"] == "Thinker"
    assert by_id[post_a["id"]]["likeCount"] == 2

    assert by_id[post_b["id"]]["authorName"] == "Test User"
    assert by_id[post_b["id"]]["roleLabel"] == "Actor"
    assert by_id[post_b["id"]]["likeCount"] == 0


def test_list_comments_default_limit_caps_at_20(client):
    headers = _signup_and_auth_headers(client, "commenter-many@example.com")
    problem_id = _create_problem(client, headers)
    _commit(client, headers, problem_id)
    post = client.post(f"/problems/{problem_id}/posts", json={"body": "Post"}, headers=headers).json()
    for i in range(25):
        client.post(
            f"/problems/{problem_id}/posts/{post['id']}/comments",
            json={"body": f"Comment {i}"},
            headers=headers,
        )

    resp = client.get(f"/problems/{problem_id}/posts/{post['id']}/comments")
    assert resp.status_code == 200
    assert len(resp.json()) == 20


def test_list_comments_limit_and_offset_page_through_results(client):
    headers = _signup_and_auth_headers(client, "commenter-page@example.com")
    problem_id = _create_problem(client, headers)
    _commit(client, headers, problem_id)
    post = client.post(f"/problems/{problem_id}/posts", json={"body": "Post"}, headers=headers).json()
    for i in range(5):
        client.post(
            f"/problems/{problem_id}/posts/{post['id']}/comments",
            json={"body": f"PageComment {i}"},
            headers=headers,
        )

    # Comments are returned oldest-first (see list_comments_for_post).
    page1 = client.get(
        f"/problems/{problem_id}/posts/{post['id']}/comments", params={"limit": 2, "offset": 0}
    ).json()
    page2 = client.get(
        f"/problems/{problem_id}/posts/{post['id']}/comments", params={"limit": 2, "offset": 2}
    ).json()

    assert [c["body"] for c in page1] == ["PageComment 0", "PageComment 1"]
    assert [c["body"] for c in page2] == ["PageComment 2", "PageComment 3"]
    assert not set(c["id"] for c in page1) & set(c["id"] for c in page2)


def test_list_comments_batched_authors_are_correct(client):
    """Regression test for the issue #77 N+1 fix on comment authors."""
    alice_headers = _signup_and_auth_headers(client, "alice-comment@example.com")
    bob_headers = _signup_and_auth_headers(client, "bob-comment@example.com")
    problem_id = _create_problem(client, alice_headers)
    _commit(client, alice_headers, problem_id, role="thinker")
    _commit(client, bob_headers, problem_id, role="backer")
    post = client.post(
        f"/problems/{problem_id}/posts", json={"body": "Post"}, headers=alice_headers
    ).json()

    client.post(
        f"/problems/{problem_id}/posts/{post['id']}/comments",
        json={"body": "Alice comment"},
        headers=alice_headers,
    )
    client.post(
        f"/problems/{problem_id}/posts/{post['id']}/comments",
        json={"body": "Bob comment"},
        headers=bob_headers,
    )

    resp = client.get(f"/problems/{problem_id}/posts/{post['id']}/comments")
    assert resp.status_code == 200
    comments = {c["body"]: c for c in resp.json()}

    assert comments["Alice comment"]["roleLabel"] == "Thinker"
    assert comments["Bob comment"]["roleLabel"] == "Backer"


def test_abandoned_member_loses_posting_rights(client, db_session):
    from datetime import timedelta

    from app.core.time import utcnow
    from app.models.commitment import Commitment

    headers = _signup_and_auth_headers(client, "formermember@example.com")
    problem_id = _create_problem(client, headers)
    commitment = _commit(client, headers, problem_id)

    # Backdate + abandon.
    row = db_session.get(Commitment, commitment["id"])
    row.started_at = utcnow() - timedelta(days=95)
    row.lock_expires_at = row.started_at + timedelta(days=90)
    db_session.commit()

    resp = client.post(
        f"/commitments/{commitment['id']}/checkpoint",
        json={"action": "abandon", "note": None},
        headers=headers,
    )
    assert resp.status_code == 200

    # Now posting should be rejected — no ACTIVE commitment anymore.
    resp_post = client.post(f"/problems/{problem_id}/posts", json={"body": "still here?"}, headers=headers)
    assert resp_post.status_code == 403
    assert resp_post.json()["detail"]["error"] == "NOT_COMMITTED"
