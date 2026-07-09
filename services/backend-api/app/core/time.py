"""Shared time helpers.

Centralized so every model/service uses the same "now" semantics
(timezone-aware UTC) — mixing naive and aware datetimes is a classic
source of subtle bugs in exactly the kind of date-math this service does
a lot of (90-day lock expiry, "days remaining", relative "time ago"
strings).
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
