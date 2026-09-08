from __future__ import annotations

from datetime import date, datetime, time

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d/%m/%y",
    "%m/%d/%y",
]

TIME_FORMATS = [
    "%H:%M",
    "%H:%M:%S",
    "%I:%M %p",
    "%I:%M%p",
    "%I %p",
]

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def parse_date(value) -> str | None:
    """Parse a variety of human date formats into an ISO 'YYYY-MM-DD' string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    # Try ISO datetime e.g. "2026-09-08T14:30:00"
    try:
        return datetime.fromisoformat(text.split(" ")[0]).date().isoformat()
    except ValueError:
        return None


def parse_time(value) -> str | None:
    """Parse a variety of human time formats into a 24h 'HH:MM' string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.time().strftime("%H:%M")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    text = str(value).strip()
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).time().strftime("%H:%M")
        except ValueError:
            continue
    return None


def time_bucket(hhmm: str | None) -> str | None:
    """Categorize an HH:MM time string into a period of day."""
    if not hhmm:
        return None
    try:
        hour = int(hhmm.split(":")[0])
    except (ValueError, IndexError):
        return None
    if 6 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    if 21 <= hour < 24:
        return "Night"
    return "Late Night"


def weekday_name(iso_date: str) -> str:
    return WEEKDAY_NAMES[date.fromisoformat(iso_date).weekday()]


def is_weekend(iso_date: str) -> bool:
    return date.fromisoformat(iso_date).weekday() >= 5
