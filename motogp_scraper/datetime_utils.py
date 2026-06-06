from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo


UTC_PLUS_8 = timezone(timedelta(hours=8))


def parse_datetime(value: str | None, *, default_timezone: str = "UTC") -> datetime | None:
    if not value:
        return None

    cleaned = " ".join(value.split())

    try:
        return ensure_timezone(
            parsedate_to_datetime(cleaned),
            default_timezone=default_timezone,
        )
    except (TypeError, ValueError):
        pass

    try:
        return ensure_timezone(
            datetime.fromisoformat(cleaned.replace("Z", "+00:00")),
            default_timezone=default_timezone,
        )
    except ValueError:
        pass

    try:
        import dateparser

        parsed = dateparser.parse(
            cleaned,
            settings={"RETURN_AS_TIMEZONE_AWARE": True, "TIMEZONE": default_timezone},
        )
        if parsed:
            return ensure_timezone(parsed, default_timezone=default_timezone)
    except Exception:
        pass

    return None


def ensure_timezone(value: datetime, *, default_timezone: str = "UTC") -> datetime:
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=ZoneInfo(default_timezone))


def to_utc_plus_8(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(UTC_PLUS_8)
