"""Deterministic local-time cadence planning for Codex Scheduled tasks."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_WEEKDAYS = {
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}
_TIMEZONE = re.compile(r"\s+(?P<timezone>local(?:\s+time)?|UTC|[A-Za-z_+-]+(?:/[A-Za-z_+-]+)+)$", re.IGNORECASE)
_TIME = re.compile(
    r"^(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>a\.?m\.?|p\.?m\.?)?$",
    re.IGNORECASE,
)


def _parse_time_and_timezone(value: str) -> tuple[int, int, str]:
    """Parse a user-approved clock time and optional named timezone."""
    candidate = value.strip()
    timezone = "local"
    match = _TIMEZONE.search(candidate)
    if match:
        timezone = match.group("timezone")
        candidate = candidate[: match.start()].strip()

    time_match = _TIME.fullmatch(candidate)
    if not time_match:
        raise ValueError("cadence must specify a valid time such as 8:00 AM")

    hour = int(time_match.group("hour"))
    minute = int(time_match.group("minute") or 0)
    meridiem = (time_match.group("meridiem") or "").replace(".", "").lower()
    if minute > 59:
        raise ValueError("cadence minute must be between 0 and 59")
    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError("12-hour cadence time must use an hour from 1 through 12")
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12
    elif not 0 <= hour <= 23:
        raise ValueError("24-hour cadence time must use an hour from 0 through 23")

    normalized_timezone = "local" if timezone.lower().startswith("local") else timezone
    if normalized_timezone != "local":
        try:
            ZoneInfo(normalized_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown timezone: {normalized_timezone}") from exc
    return hour, minute, normalized_timezone


def _result(*, frequency: str, hour: int, minute: int, timezone: str, byday: str = "", bymonthday: int = 0) -> dict[str, object]:
    fields = [f"FREQ={frequency}", "INTERVAL=1"]
    if byday:
        fields.append(f"BYDAY={byday}")
    if bymonthday:
        fields.append(f"BYMONTHDAY={bymonthday}")
    fields.extend([f"BYHOUR={hour}", f"BYMINUTE={minute}", "BYSECOND=0"])
    return {
        "frequency": frequency.lower(),
        "timezone": timezone,
        "scheduler_timezone": "local",
        "requires_local_timezone_confirmation": timezone != "local",
        "rrule": "RRULE:" + ";".join(fields),
    }


def plan(cadence: str) -> dict[str, object]:
    """Convert an explicit supported Retriever cadence into a Codex wall-clock RRULE.

    Supported forms are ``Daily at 8:00 AM [timezone]``, ``Weekly on Monday at
    8:00 AM [timezone]``, and ``Monthly on day 15 at 8:00 AM [timezone]``.
    Codex Scheduled receives an RFC 5545 rule without a timezone field, so a
    plan that names a timezone must be explicitly reconfirmed as the Codex
    machine's local time before it can create or update a task.
    """
    value = cadence.strip().rstrip(".")
    if not value:
        raise ValueError("cadence must specify daily, weekly, or monthly timing")

    daily = re.fullmatch(r"(?:daily|every day)(?:\s+at)?\s+(.+)", value, re.IGNORECASE)
    if daily:
        hour, minute, timezone = _parse_time_and_timezone(daily.group(1))
        return _result(frequency="DAILY", hour=hour, minute=minute, timezone=timezone)

    weekly = re.fullmatch(
        r"(?:weekly|every week)\s+on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+(.+)",
        value,
        re.IGNORECASE,
    )
    if weekly:
        hour, minute, timezone = _parse_time_and_timezone(weekly.group(2))
        weekday = _WEEKDAYS[weekly.group(1).lower()]
        return _result(frequency="WEEKLY", hour=hour, minute=minute, timezone=timezone, byday=weekday)

    monthly = re.fullmatch(r"(?:monthly|every month)\s+on\s+(?:day\s+)?(\d{1,2})\s+at\s+(.+)", value, re.IGNORECASE)
    if monthly:
        day = int(monthly.group(1))
        if not 1 <= day <= 31:
            raise ValueError("monthly cadence day must be between 1 and 31")
        hour, minute, timezone = _parse_time_and_timezone(monthly.group(2))
        return _result(frequency="MONTHLY", hour=hour, minute=minute, timezone=timezone, bymonthday=day)

    raise ValueError(
        "cadence must specify daily at a time, weekly on a weekday at a time, or monthly on a day at a time"
    )


def require_local_time(cadence: str) -> dict[str, object]:
    """Return a schedulable plan, never silently converting a named timezone.

    The Codex automation interface currently accepts an RRULE but exposes no
    separate timezone value. A user who says ``America/New_York`` may not mean
    the same thing as the local timezone of the machine that will run the task,
    so Retriever asks for a local-time confirmation instead of guessing.
    """
    planned = plan(cadence)
    if planned["requires_local_timezone_confirmation"]:
        raise ValueError(
            "Codex Scheduled runs this task at the machine's local time; confirm the cadence in local time, "
            "for example: Daily at 8:00 AM local time"
        )
    return planned
