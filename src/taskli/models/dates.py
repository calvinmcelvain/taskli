"""Due-date modifier value parsing."""

import re
from datetime import date, datetime, timedelta

from ..exceptions import InvalidModifierValueError

__all__ = ["parse_agenda_window", "parse_due_date", "today"]

# both the full and 3-letter forms, keyed to date.weekday() (mon=0).
WEEKDAY_INDEX = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


def today() -> date:
    """Return the current calendar day.

    A thin seam over ``datetime.now`` so tests can pin "now".

    Returns
    -------
    date
        The local date at the moment of the call.
    """

    return datetime.now().date()


def midnight(value: date) -> datetime:
    """Return ``value`` as a datetime at that calendar day's midnight.

    Parameters
    ----------
    value : date
        The calendar day to normalize (a ``datetime`` is also accepted;
        its time component is dropped).

    Returns
    -------
    datetime
        ``value`` with hour, minute, second, and microsecond zeroed.
    """

    return datetime(value.year, value.month, value.day)


def parse_due_date(raw: str) -> datetime:
    """Parse a due-date modifier value to a midnight datetime.

    Parameters
    ----------
    raw : str
        The user-supplied value, e.g. ``"tomorrow"``, ``"3 days"``, or
        ``"04-15-2026"``.

    Returns
    -------
    datetime
        The resolved calendar day at midnight (no time component).
    """

    text = raw.strip()
    keyword = text.casefold()

    if keyword == "today":
        return midnight(today())
    if keyword == "tomorrow":
        return midnight(today() + timedelta(days=1))
    if keyword == "next week":
        return midnight(today() + timedelta(days=7))

    if keyword in WEEKDAY_INDEX:
        current = today()
        delta = (WEEKDAY_INDEX[keyword] - current.weekday()) % 7
        # a named weekday that is today resolves to the following week.
        if delta == 0:
            delta = 7

        return midnight(current + timedelta(days=delta))

    relative = re.match(r"^(\d+)\s+(days?|weeks?)$", keyword)
    if relative is not None:
        count = int(relative.group(1))
        if count > 0:
            span = 7 if relative.group(2).startswith("week") else 1
            return midnight(today() + timedelta(days=count * span))

    try:
        explicit = datetime.strptime(text, "%m-%d-%Y")
    except ValueError as error:
        raise InvalidModifierValueError(
            "due date must be one of: today, tomorrow, next week, "
            "N days, N weeks, a weekday name (e.g. monday), or "
            "MM-DD-YYYY"
        ) from error

    return midnight(explicit)


def parse_agenda_window(raw: str) -> str:
    """Validate and normalize an agenda window token.

    Parameters
    ----------
    raw : str
        The user-supplied value, e.g. ``"today"``, ``"week"``,
        ``"overdue"``, or a positive integer of days as a string.

    Returns
    -------
    str
        The normalized token: ``"today"``, ``"week"``, ``"overdue"``,
        or the digit string unchanged.
    """

    keyword = raw.strip().casefold()
    if keyword in {"today", "week", "overdue"}:
        return keyword
    if keyword.isdigit() and int(keyword) > 0:
        return keyword

    raise InvalidModifierValueError(
        "agenda window must be one of: today, week, overdue, or N (days)."
    )
