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

Keyed by client IP (`get_remote_address`) rather than by authenticated
user, since the endpoints needing the tightest limit (signup/login) are
pre-auth by definition.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

AUTH_RATE_LIMIT = "5/minute"
GENERAL_RATE_LIMIT = "60/minute"

limiter = Limiter(key_func=get_remote_address, default_limits=[GENERAL_RATE_LIMIT])
