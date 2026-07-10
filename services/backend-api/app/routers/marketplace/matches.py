"""RRF rank-fusion matching trigger + read endpoints (GitHub issue #68,
"Matching engine: rank fusion (RRF)"). Ships the async, multi-signal
half of CLAUDE.md "Solution Marketplace Architecture" -> "Matching
engine" — the deterministic attribute-only MVP already lives in
`app/routers/marketplace/matching.py` (issue #66); this module is a
distinct file (not an extension of that one) because it's a genuinely
different shape of feature: a POST that enqueues async work plus a GET
that reads back a persisted, versioned result, vs. #66's synchronous
compute-on-every-request endpoint.

`POST /marketplace/rfps/{rfp_id}/matches/trigger` — member-of-org gate
(same `require_org_member` rule `add_rfp_requirement` already uses),
creates a `MatchRun` row and enqueues the real computation onto
`services/ai-coordinator-worker`'s `marketplace-matching` queue. Mirrors
CLAUDE.md's "invoked on-demand" pattern already established for the AI
coordinator elsewhere.

`GET /marketplace/rfps/{rfp_id}/matches` — same invite-only visibility
gate as reading the RFP itself and as #66's attribute-matches endpoint.
Read-only, no auth required for a public RFP.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.config import settings
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_session
from app.impl.job_enqueuer import RQJobEnqueuer
from app.impl.repositories import (
    SqlAlchemyMatchRepo,
    SqlAlchemyOrganizationRepo,
    SqlAlchemyRFPRepo,
    SqlAlchemySolutionRepo,
)
from app.interfaces.job_enqueuer import JobEnqueuerPort
from app.models.user import User
from app.schemas_marketplace import MatchRunTriggerOut, RFPMatchesOut
from app.services.errors import NotOrgMemberError, RFPNotFoundError
from app.services.marketplace_service import get_matches_for_rfp, trigger_match_run
from app.services.presenters_marketplace import match_run_to_out, rfp_matches_to_out

router = APIRouter(prefix="/marketplace/rfps", tags=["marketplace-matches"])

_bearer_scheme = HTTPBearer(auto_error=False)


def _optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    if credentials is None or not credentials.credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except InvalidTokenError:
        return None


def _job_enqueuer() -> JobEnqueuerPort:
    # Constructed per-request (like `get_session`) rather than a
    # module-level singleton — a fresh `Redis.from_url` connection is
    # cheap (lazy TCP connect, not established until first use) and this
    # keeps the dependency overridable in tests the same way
    # `get_session` is (see tests/integration/conftest.py's
    # `app.dependency_overrides` pattern).
    return RQJobEnqueuer(redis_url=settings.redis_url)


@router.post(
    "/{rfp_id}/matches/trigger",
    response_model=MatchRunTriggerOut,
    status_code=status.HTTP_201_CREATED,
)
def trigger_match_run_route(
    rfp_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    job_enqueuer: JobEnqueuerPort = Depends(_job_enqueuer),
) -> MatchRunTriggerOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp_repo = SqlAlchemyRFPRepo(session)
    match_repo = SqlAlchemyMatchRepo(session)
    try:
        match_run = trigger_match_run(
            rfp_id=rfp_id,
            caller_user_id=current_user.id,
            org_repo=org_repo,
            rfp_repo=rfp_repo,
            match_repo=match_repo,
            job_enqueuer=job_enqueuer,
            queue_name=settings.marketplace_matching_queue_name,
        )
    except RFPNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RFP_NOT_FOUND", "message": str(exc)},
        ) from exc
    except NotOrgMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_ORG_MEMBER", "message": str(exc)},
        ) from exc

    return match_run_to_out(match_run)


@router.get("/{rfp_id}/matches", response_model=RFPMatchesOut)
def get_rfp_matches_route(
    rfp_id: str,
    caller_user_id: str | None = Depends(_optional_user_id),
    session: Session = Depends(get_session),
) -> RFPMatchesOut:
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp_repo = SqlAlchemyRFPRepo(session)
    solution_repo = SqlAlchemySolutionRepo(session)
    match_repo = SqlAlchemyMatchRepo(session)
    try:
        match_run, matches = get_matches_for_rfp(
            rfp_id=rfp_id,
            caller_user_id=caller_user_id,
            org_repo=org_repo,
            rfp_repo=rfp_repo,
            solution_repo=solution_repo,
            match_repo=match_repo,
        )
    except RFPNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RFP_NOT_FOUND", "message": f"No RFP with id {rfp_id}."},
        ) from exc

    return rfp_matches_to_out(match_run, matches)
