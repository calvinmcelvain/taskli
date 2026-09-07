"""Due-date modifier value parsing."""

import re
from datetime import date, datetime, timedelta

from ..exceptions import InvalidModifierValueError

__all__ = ["parse_due_date", "today"]


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
            "N days, N weeks, or MM-DD-YYYY"
        ) from error

    return midnight(explicit)
