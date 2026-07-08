"""Static implementation of ServiceInfoPort."""

SERVICE_NAME = "avadhana-backend-api"
SERVICE_VERSION = "0.1.0"


class StaticServiceInfoService:
    """Reports fixed service identity (name/version) known at build time.

    Structurally satisfies `app.interfaces.service_info.ServiceInfoPort` —
    no inheritance needed; Protocols use duck typing (PEP 544).
    """

    def describe(self) -> dict[str, str]:
        return {"service": SERVICE_NAME, "version": SERVICE_VERSION}
