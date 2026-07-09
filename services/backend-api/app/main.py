"""Avadhana Backend API — composition root.

Now backed by a real database layer (SQLAlchemy models under
`app/models/`, Alembic migrations under `migrations/`) and the full SLC
v1 commitment/problem/feed API. Route handlers depend on interface types
(`app.interfaces`) via `Depends()`; the composition root wiring for the
original health/service-info endpoints stays inline here since it's
tiny, while the newer resource routers (auth/users/problems/commitments/
feed) live under `app/routers/` and are included below — this file
would otherwise be unreadably large if every endpoint were defined
directly here.
"""

from fastapi import Depends, FastAPI

from app.impl.health import StaticHealthCheckService
from app.impl.service_info import SERVICE_NAME, SERVICE_VERSION, StaticServiceInfoService
from app.interfaces.health import HealthCheckPort
from app.interfaces.service_info import ServiceInfoPort
from app.routers import auth, commitments, feed, problems, users

app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(problems.router)
app.include_router(commitments.router)
app.include_router(feed.router)


# --- Providers (composition root wiring) ------------------------------
# Each provider returns the interface type. Swapping an implementation
# (e.g. StaticHealthCheckService -> a real DB/Redis-probing service)
# only requires changing the provider body, never the route handlers.


def get_health_service() -> HealthCheckPort:
    return StaticHealthCheckService()


def get_service_info_service() -> ServiceInfoPort:
    return StaticServiceInfoService()


# --- Routes -------------------------------------------------------------


@app.get("/")
def root(service_info: ServiceInfoPort = Depends(get_service_info_service)) -> dict:
    """Basic service identity payload."""
    return service_info.describe()


@app.get("/healthz")
def healthz(health_service: HealthCheckPort = Depends(get_health_service)) -> dict:
    """Liveness/readiness probe for Kubernetes."""
    return health_service.check()
