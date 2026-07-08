"""Avadhana Backend API — minimal skeleton service.

This is a placeholder FastAPI app scaffolded for containerization
(GitHub issue #42). No database connection or real business logic yet —
that arrives in later issues (e.g. #6 Commitment creation flow,
#11 Problem schema).

This module is the composition root: route handlers depend on
interface types (`app.interfaces`) via `Depends(provider_fn)`, never on
concrete implementations directly. Provider functions live here since
the service is small; split them into `app/dependencies.py` once this
file gets crowded with real endpoints (commitments, problems, etc.).
"""

from fastapi import Depends, FastAPI

from app.impl.health import StaticHealthCheckService
from app.impl.service_info import SERVICE_NAME, SERVICE_VERSION, StaticServiceInfoService
from app.interfaces.health import HealthCheckPort
from app.interfaces.service_info import ServiceInfoPort

app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)


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
