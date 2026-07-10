"""Integration tests for the RRF rank-fusion matching trigger/read
endpoints (GitHub issue #68) — through the real HTTP layer.

The real job-enqueue call (`app.impl.job_enqueuer.RQJobEnqueuer`, which
needs a live Redis connection) is overridden via FastAPI's
`dependency_overrides` with an in-memory fake, mirroring how
`services/ai-coordinator-worker` avoids needing live SARVAM credentials
via `SARVAM_USE_MOCK` — this test suite needs no live Redis to exercise
the trigger endpoint's behavior (auth/visibility gating, MatchRun row
creation), since the actual job execution is `ai-coordinator-worker`'s
concern, tested separately in that service.

No completed-run fixture data can be created through the HTTP API alone
(the async job that would populate `SolutionMatch` rows runs in a
different service/process) — so the "matches exist" path is exercised
by writing `MatchRun`/`SolutionMatch` rows directly via the test session,
the same direct-row-mutation pattern already used by
`test_api_marketplace_matching.py`'s `_publish_solution` helper for
state with no API surface of its own yet.
"""

from app.db.session import get_session
from app.main import app
from app.models.marketplace.matching import MatchRun, MatchRunStatus, SolutionMatch
from app.models.marketplace.solution import Solution
from app.routers.marketplace.matches import _job_enqueuer


class _FakeJobEnqueuer:
    """In-memory fake satisfying `JobEnqueuerPort` — records every
    enqueue call instead of touching real Redis."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def enqueue(self, queue_name: str, job_name: str, **kwargs) -> str:
        self.calls.append({"queue_name": queue_name, "job_name": job_name, **kwargs})
        return "fake-job-id"


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


def _with_fake_enqueuer(fake: _FakeJobEnqueuer):
    app.dependency_overrides[_job_enqueuer] = lambda: fake


def _clear_fake_enqueuer():
    app.dependency_overrides.pop(_job_enqueuer, None)


def test_trigger_creates_pending_match_run_and_enqueues_job(client):
    buyer_headers, _ = _signup_and_auth_headers(client, email="buyer-trigger@example.com")
    buyer_org_id = _create_org(client, buyer_headers, name="Trigger Org")
    rfp_resp = client.post("/marketplace/rfps", json=_rfp_payload(buyer_org_id), headers=buyer_headers)
    rfp_id = rfp_resp.json()["id"]

    fake = _FakeJobEnqueuer()
    _with_fake_enqueuer(fake)
    try:
        resp = client.post(f"/marketplace/rfps/{rfp_id}/matches/trigger", headers=buyer_headers)
    finally:
        _clear_fake_enqueuer()

    assert resp.status_code == 201
    body = resp.json()
    assert body["rfpId"] == rfp_id
    assert body["status"] == "pending"

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["queue_name"] == "marketplace-matching"
    assert call["job_name"] == "impl.marketplace_matching_job.run_matching_job"
    assert call["rfp_id"] == rfp_id
    assert call["match_run_id"] == body["id"]


def test_trigger_by_non_member_is_forbidden(client):
    buyer_headers, _ = _signup_and_auth_headers(client, email="buyer-trigger-2@example.com")
    buyer_org_id = _create_org(client, buyer_headers, name="Trigger Org 2")
    rfp_resp = client.post("/marketplace/rfps", json=_rfp_payload(buyer_org_id), headers=buyer_headers)
    rfp_id = rfp_resp.json()["id"]

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-trigger@example.com")

    fake = _FakeJobEnqueuer()
    _with_fake_enqueuer(fake)
    try:
        resp = client.post(f"/marketplace/rfps/{rfp_id}/matches/trigger", headers=outsider_headers)
    finally:
        _clear_fake_enqueuer()

    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "NOT_ORG_MEMBER"
    assert fake.calls == []


def test_trigger_requires_auth(client):
    resp = client.post("/marketplace/rfps/does-not-exist/matches/trigger")
    assert resp.status_code == 401


def test_trigger_for_nonexistent_rfp_is_404(client):
    headers, _ = _signup_and_auth_headers(client, email="trigger-404@example.com")
    fake = _FakeJobEnqueuer()
    _with_fake_enqueuer(fake)
    try:
        resp = client.post("/marketplace/rfps/does-not-exist/matches/trigger", headers=headers)
    finally:
        _clear_fake_enqueuer()

    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "RFP_NOT_FOUND"


def _write_completed_run_with_matches(rfp_id: str, solution_ids: list[str]) -> str:
    """Direct row mutation — no way to reach a "completed" MatchRun
    through the HTTP API alone, since the real computation runs in a
    different service/process (ai-coordinator-worker). Mirrors
    `test_api_marketplace_matching.py`'s `_publish_solution` pattern."""
    override = app.dependency_overrides[get_session]
    session_gen = override()
    session = next(session_gen)
    try:
        match_run = MatchRun(
            rfp_id=rfp_id,
            triggered_by="system",
            model_versions_used={"embeddings_model": "mock-embeddings-v1"},
            status=MatchRunStatus.COMPLETED.value,
        )
        session.add(match_run)
        session.commit()
        session.refresh(match_run)

        for rank, solution_id in enumerate(solution_ids, start=1):
            session.add(
                SolutionMatch(
                    match_run_id=match_run.id,
                    solution_id=solution_id,
                    final_rrf_score=1.0 / rank,
                    rank=rank,
                    signal_scores={"attribute_match": 1.0 / rank},
                    signal_ranks={"attribute_match": rank},
                )
            )
        session.commit()
        return match_run.id
    finally:
        session_gen.close()


def _create_solution(client, headers, org_id, title="Solution A"):
    resp = client.post(
        "/marketplace/solutions",
        json={
            "organizationId": org_id,
            "title": title,
            "description": "A solution.",
            "categoryTags": [],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_get_matches_returns_empty_when_no_run_completed_yet(client):
    buyer_headers, _ = _signup_and_auth_headers(client, email="buyer-read-empty@example.com")
    buyer_org_id = _create_org(client, buyer_headers, name="Read Empty Org")
    rfp_resp = client.post("/marketplace/rfps", json=_rfp_payload(buyer_org_id), headers=buyer_headers)
    rfp_id = rfp_resp.json()["id"]

    resp = client.get(f"/marketplace/rfps/{rfp_id}/matches")
    assert resp.status_code == 200
    body = resp.json()
    assert body["matchRun"] is None
    assert body["matches"] == []


def test_get_matches_returns_ranked_results_from_latest_completed_run(client):
    buyer_headers, _ = _signup_and_auth_headers(client, email="buyer-read@example.com")
    buyer_org_id = _create_org(client, buyer_headers, name="Read Org")
    rfp_resp = client.post("/marketplace/rfps", json=_rfp_payload(buyer_org_id), headers=buyer_headers)
    rfp_id = rfp_resp.json()["id"]

    provider_headers, _ = _signup_and_auth_headers(client, email="provider-read@example.com")
    provider_org_id = _create_org(client, provider_headers, name="Read Provider Org")
    sol_1 = _create_solution(client, provider_headers, provider_org_id, title="First")
    sol_2 = _create_solution(client, provider_headers, provider_org_id, title="Second")

    match_run_id = _write_completed_run_with_matches(rfp_id, [sol_1, sol_2])

    resp = client.get(f"/marketplace/rfps/{rfp_id}/matches")
    assert resp.status_code == 200
    body = resp.json()
    assert body["matchRun"]["id"] == match_run_id
    assert body["matchRun"]["status"] == "completed"
    assert [m["solution"]["title"] for m in body["matches"]] == ["First", "Second"]
    assert body["matches"][0]["rank"] == 1
    assert body["matches"][0]["finalRrfScore"] == 1.0
    # signalScores/signalRanks are dicts keyed by signal name — those
    # keys are data (e.g. "attribute_match"), not Python field names, so
    # CamelModel's alias generator does NOT transform them.
    assert body["matches"][0]["signalScores"] == {"attribute_match": 1.0}
    assert body["matches"][1]["rank"] == 2


def test_get_matches_only_returns_completed_runs_not_pending_or_failed(client):
    buyer_headers, _ = _signup_and_auth_headers(client, email="buyer-read-pending@example.com")
    buyer_org_id = _create_org(client, buyer_headers, name="Read Pending Org")
    rfp_resp = client.post("/marketplace/rfps", json=_rfp_payload(buyer_org_id), headers=buyer_headers)
    rfp_id = rfp_resp.json()["id"]

    fake = _FakeJobEnqueuer()
    _with_fake_enqueuer(fake)
    try:
        trigger_resp = client.post(
            f"/marketplace/rfps/{rfp_id}/matches/trigger", headers=buyer_headers
        )
    finally:
        _clear_fake_enqueuer()
    assert trigger_resp.json()["status"] == "pending"

    resp = client.get(f"/marketplace/rfps/{rfp_id}/matches")
    assert resp.status_code == 200
    assert resp.json()["matchRun"] is None
    assert resp.json()["matches"] == []


def test_get_matches_for_invite_only_rfp_hidden_from_outsiders(client):
    buyer_headers, _ = _signup_and_auth_headers(client, email="buyer-invite-read@example.com")
    buyer_org_id = _create_org(client, buyer_headers, name="Invite Read Org")
    rfp_resp = client.post(
        "/marketplace/rfps",
        json=_rfp_payload(buyer_org_id, title="Secret Read RFP", visibility="invite_only"),
        headers=buyer_headers,
    )
    rfp_id = rfp_resp.json()["id"]

    anon_resp = client.get(f"/marketplace/rfps/{rfp_id}/matches")
    assert anon_resp.status_code == 404

    outsider_headers, _ = _signup_and_auth_headers(client, email="outsider-read@example.com")
    outsider_resp = client.get(f"/marketplace/rfps/{rfp_id}/matches", headers=outsider_headers)
    assert outsider_resp.status_code == 404

    member_resp = client.get(f"/marketplace/rfps/{rfp_id}/matches", headers=buyer_headers)
    assert member_resp.status_code == 200


def test_get_matches_for_nonexistent_rfp_is_404(client):
    resp = client.get("/marketplace/rfps/does-not-exist/matches")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "RFP_NOT_FOUND"
