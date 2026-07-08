"""Interface for the service identity info port."""

from typing import Protocol


class ServiceInfoPort(Protocol):
    """Port for reporting basic service identity (name/version).

    Concrete implementations live in `app/impl/service_info.py`.
    """

    def get_info(self) -> dict[str, str]:
        """Return a service identity payload, e.g. {"service": ..., "version": ...}."""
        ...
