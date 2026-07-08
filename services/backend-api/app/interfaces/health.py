"""Port for liveness/readiness health checks."""

from typing import Protocol


class HealthCheckPort(Protocol):
    """Abstract interface for reporting service health."""

    def check(self) -> dict[str, str]:
        """Return a health status payload, e.g. {"status": "ok"}."""
        ...
