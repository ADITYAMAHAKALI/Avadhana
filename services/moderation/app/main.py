"""Avadhana Moderation service — minimal skeleton service.

This is a placeholder FastAPI app scaffolded for containerization
(GitHub issue #44). It exists as its own standalone service already,
even though real moderation logic still lives in the Backend API
process for now — see CLAUDE.md ("Local Development Environment"):
each service gets its own Containerfile from day one so the
image-build path stays consistent and we avoid a rework later when
Moderation is actually split out.

No off-topic detection, auto-blocking, or appeal handling yet —
that arrives in later issues (#23-26).

This module is the composition root: route handlers depend on
interface (Protocol) types from `app/interfaces/` via `Depends()`,
resolved to concrete implementations from `app/impl/` through the
provider functions in `app/dependencies.py`. Handlers never construct
or import a concrete implementation directly — this keeps the pattern
consistent as real business logic replaces these static placeholders.
"""

from fastapi import Depends, FastAPI

from app.dependencies import get_health_service, get_service_info_service
from app.impl.service_info import SERVICE_NAME, SERVICE_VERSION
from app.interfaces.health import HealthCheckPort
from app.interfaces.service_info import ServiceInfoPort

app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)


@app.get("/")
def root(service_info: ServiceInfoPort = Depends(get_service_info_service)) -> dict:
    """Basic service identity payload."""
    return service_info.get_info()


@app.get("/healthz")
def healthz(health_service: HealthCheckPort = Depends(get_health_service)) -> dict:
    """Liveness/readiness probe for Kubernetes."""
    return health_service.check()
