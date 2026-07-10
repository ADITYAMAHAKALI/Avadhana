"""Attribute-match scoring endpoint (GitHub issue #66, "Structured
attribute-match scoring (no ML)"). Ships the non-ML slice of CLAUDE.md
"Solution Marketplace Architecture" -> "Matching engine" ahead of the
embeddings (#67) and RRF-fusion (#68) work, so buyers get a real ranked
shortlist immediately rather than waiting on the full pipeline.

Read-only, gated the same way `GET /marketplace/rfps/{rfp_id}` already
is: public RFPs are visible to anyone, invite-only RFPs only to members
of the posting Organization. Reuses `rfp_visible_to_caller` from
`app.services.marketplace_service` (the same function that router now
also uses) rather than re-deriving the rule, and this module's own
`_optional_user_id` dependency mirrors `app.routers.marketplace.rfps`'s
(auth is optional here — an anonymous caller can still see matches for a
public RFP).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_session
from app.impl.repositories import SqlAlchemyOrganizationRepo, SqlAlchemyRFPRepo, SqlAlchemySolutionRepo
from app.schemas_marketplace import AttributeMatchOut
from app.services.errors import RFPNotFoundError
from app.services.marketplace_service import get_attribute_matches_for_rfp
from app.services.presenters_marketplace import attribute_match_to_out

router = APIRouter(prefix="/marketplace/rfps", tags=["marketplace-matching"])

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


@router.get("/{rfp_id}/attribute-matches", response_model=list[AttributeMatchOut])
def get_attribute_matches_route(
    rfp_id: str,
    caller_user_id: str | None = Depends(_optional_user_id),
    session: Session = Depends(get_session),
) -> list[AttributeMatchOut]:
    org_repo = SqlAlchemyOrganizationRepo(session)
    rfp_repo = SqlAlchemyRFPRepo(session)
    solution_repo = SqlAlchemySolutionRepo(session)
    try:
        results = get_attribute_matches_for_rfp(
            rfp_id=rfp_id,
            caller_user_id=caller_user_id,
            org_repo=org_repo,
            rfp_repo=rfp_repo,
            solution_repo=solution_repo,
        )
    except RFPNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RFP_NOT_FOUND", "message": f"No RFP with id {rfp_id}."},
        ) from exc

    return [attribute_match_to_out(r) for r in results]
