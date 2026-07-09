"""Server-side presentation helpers for fields the frontend must not have
to (re)compute: initials, avatar color, and relative "time ago" strings.

Computing these server-side keeps the API contract exact (the frontend
TypeScript interfaces expect these as plain strings) and keeps the
derivation logic in one place instead of duplicated in the frontend.
"""

import hashlib
from datetime import datetime

from app.core.time import utcnow

# Fixed 6-color palette for deterministic avatar colors. Small and fixed
# so avatars stay visually consistent across the app; "deterministic"
# here means the same user id always maps to the same color (hashed, not
# random/stored), so no extra column or migration is needed if we ever
# want to change the palette.
AVATAR_COLOR_PALETTE = (
    "#F97316",  # orange
    "#0EA5E9",  # sky blue
    "#22C55E",  # green
    "#A855F7",  # purple
    "#EF4444",  # red
    "#EAB308",  # yellow
)


def initials_for_name(name: str) -> str:
    """"Ravi Menon" -> "RM"; single word -> first two letters, uppercased.

    Falls back to "?" for an empty/whitespace-only name so callers never
    get an empty string.
    """
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        word = parts[0]
        return (word[:2] if len(word) >= 2 else word[:1]).upper()
    return (parts[0][0] + parts[-1][0]).upper()


def avatar_color_for_user_id(user_id: str) -> str:
    """Deterministic pick from AVATAR_COLOR_PALETTE, hashed from the
    user id. Uses md5 purely as a fast, stable string->int hash (not for
    any security purpose) so the same id always lands on the same color
    across processes/restarts (unlike Python's salted `hash()`)."""
    digest = hashlib.md5(user_id.encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(AVATAR_COLOR_PALETTE)
    return AVATAR_COLOR_PALETTE[index]


def time_ago(moment: datetime) -> str:
    """Relative-time string, e.g. "just now", "2h ago", "3d ago"."""
    now = utcnow()
    # Normalize naive datetimes (e.g. from SQLite, which doesn't persist
    # tzinfo) to UTC-aware before subtracting, so this works identically
    # against both Postgres and the SQLite test engine.
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=now.tzinfo)
    delta = now - moment
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    if months < 12:
        return f"{months}mo ago"
    years = days // 365
    return f"{years}y ago"
