"""Concrete implementation(s) of HealthCheckPort."""


class StaticHealthCheckService:
    """Always-healthy liveness/readiness check.

    Satisfies `app.interfaces.health.HealthCheckPort` structurally (no
    inheritance required — see that module for why Protocol is used).

    This is a placeholder: it always reports "ok". When the service grows
    real dependencies (DB, queue, SARVAM API reachability, etc.), replace
    or extend this with an implementation that actually probes them —
    route handlers in `app/main.py` won't need to change, only the
    provider function's return value.
    """

    def check(self) -> dict[str, str]:
        return {"status": "ok"}
