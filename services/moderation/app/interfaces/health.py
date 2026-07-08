"""Interface for the liveness/readiness health check port."""

from typing import Protocol


class HealthCheckPort(Protocol):
    """Port for reporting service liveness/readiness.

    Concrete implementations live in `app/impl/health.py`. Real
    implementations may eventually check downstream dependencies
    (DB, queue, etc.) — this port intentionally stays generic so
    route handlers never need to change when that logic is added.
    """

    def check(self) -> dict[str, str]:
        """Return a liveness/readiness payload, e.g. {"status": "ok"}."""
        ...
