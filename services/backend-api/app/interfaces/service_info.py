"""Port for basic service identity information."""

from typing import Protocol


class ServiceInfoPort(Protocol):
    """Abstract interface for reporting service identity (name/version)."""

    def describe(self) -> dict[str, str]:
        """Return a service identity payload, e.g. {"service": ..., "version": ...}."""
        ...
