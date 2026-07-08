"""Concrete implementation(s) of ServiceInfoPort."""

SERVICE_NAME = "avadhana-moderation"
SERVICE_VERSION = "0.1.0"


class StaticServiceInfoService:
    """Reports fixed service identity (name/version).

    Satisfies `app.interfaces.service_info.ServiceInfoPort` structurally.
    """

    def get_info(self) -> dict[str, str]:
        return {"service": SERVICE_NAME, "version": SERVICE_VERSION}
