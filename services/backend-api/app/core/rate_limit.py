"""Rate limiting (TODO.md Security Checklist: "Rate limiting on auth
endpoints ... to prevent brute force" and "Rate limiting on the API
generally").

Backed by `slowapi` (a thin FastAPI/Starlette wrapper over the `limits`
package), configured with its default in-memory storage — deliberately
NOT Redis-backed. This is a single-VPS solo-dev pilot
(`docker-compose.prod.yml` runs one `backend-api` process, no
multi-replica deployment planned) and Redis is currently only used by
`ai-coordinator-worker`'s job queue, a separate service; adding it here
just for rate limiting would be a disproportionate new dependency for
this stage. In-memory state is process-local and resets on restart,
which is an acceptable tradeoff for a single process — if backend-api is
ever horizontally scaled, this must move to a shared (e.g. Redis-backed)
`limits` storage backend so limits are enforced across replicas, not
per-replica.

Limits chosen:
  - Auth endpoints (signup/login): 5/minute per IP. These are the
    brute-force-sensitive endpoints (credential stuffing, account
    enumeration via signup). 5/minute is generous enough for a real user
    who mistypes a password a couple of times, tight enough to make
    scripted brute forcing impractical.
  - General API: 60/minute per IP, applied as a blanket default via
    `Limiter(default_limits=...)`. Generous enough not to interfere with
    normal interactive use (a user clicking around a problem's feed),
    but bounds worst-case load from a single client — especially
    relevant per CLAUDE.md's "Rate limiting & quotas" guidance to
    protect anything that can trigger a downstream SARVAM call (not
    wired up yet, but the general limit is cheap insurance regardless).
  - Marketplace Organization creation (`POST /marketplace/organizations`):
    10/day, keyed per authenticated user (see `_user_or_ip_key` below) —
    a partial mitigation for the free-quota-reset abuse pattern flagged
    in CLAUDE.md "Solution Marketplace Architecture" -> "Open questions":
    "nothing yet stops an Organization from creating many Organizations
    to keep resetting the 100-RFP free quota." See that router's
    docstring for the honest limits of this mitigation.

The module default (`limiter`, used as `app.state.limiter` in
`app/main.py`) is keyed by client IP (`get_remote_address`) rather than
by authenticated user, since the endpoints needing the tightest limit
(signup/login) are pre-auth by definition — there is no user to key on
yet. `_user_or_ip_key` below is a per-route `key_func` override (slowapi
supports this — `Limiter.limit(..., key_func=...)`) for routes that DO
require auth, where per-user keying is strictly more effective against
an abuser who rotates IPs/VPNs but reuses (or cheaply mints) accounts;
falls back to IP if, for any reason, the request has no valid bearer
token by the time the limiter runs (defense in depth — the route itself
still 401s via `get_current_user`, this is just what the limiter counts
against in that edge case).
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import InvalidTokenError, decode_access_token

AUTH_RATE_LIMIT = "5/minute"
GENERAL_RATE_LIMIT = "60/minute"
ORGANIZATION_CREATE_RATE_LIMIT = "10/day"

limiter = Limiter(key_func=get_remote_address, default_limits=[GENERAL_RATE_LIMIT])


def _user_or_ip_key(request: Request) -> str:
    """Per-user rate-limit key for authenticated routes: decodes the
    caller's user id straight off the raw `Authorization` header (same
    approach as `app.routers.marketplace.rfps._optional_user_id`,
    necessary because slowapi's `key_func` only receives the Starlette
    `Request`, not FastAPI's resolved `Depends(get_current_user)`).
    Falls back to IP if there's no valid token — see module docstring."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[len("bearer ") :].strip()
        try:
            return f"user:{decode_access_token(token)}"
        except InvalidTokenError:
            pass
    return f"ip:{get_remote_address(request)}"
