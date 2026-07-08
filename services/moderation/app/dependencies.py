"""Dependency provider functions for the Moderation service.

Kept separate from `app/main.py` so the composition root (route
declarations) stays focused on HTTP wiring rather than object
construction. Each provider returns a port (interface) type; FastAPI
route handlers depend on the interface via `Depends(provider)` and never
import/construct a concrete implementation directly.

As real moderation logic (off-topic detection, auto-block, appeals —
issues #23-26) lands, add one provider per new port here following the
same pattern.
"""

from app.impl.health import StaticHealthCheckService
from app.impl.service_info import StaticServiceInfoService
from app.interfaces.health import HealthCheckPort
from app.interfaces.service_info import ServiceInfoPort


def get_health_service() -> HealthCheckPort:
    return StaticHealthCheckService()


def get_service_info_service() -> ServiceInfoPort:
    return StaticServiceInfoService()
