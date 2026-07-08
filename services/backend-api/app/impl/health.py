"""Static implementation of HealthCheckPort.

Sufficient for a liveness/readiness probe today (no dependencies to
check). If the service later gains real dependencies (DB, Redis, job
queue), replace or extend this with an implementation that actually
probes them — callers depend on HealthCheckPort, so that swap requires
no changes outside app/impl/health.py and the provider wiring.
"""

class StaticHealthCheckService:
    """Always reports healthy. No external dependencies to check yet.

    Structurally satisfies `app.interfaces.health.HealthCheckPort` — no
    inheritance needed; Protocols use duck typing (PEP 544).
    """

    def check(self) -> dict[str, str]:
        return {"status": "ok"}
