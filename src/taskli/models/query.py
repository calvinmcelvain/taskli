"""Filter, criterion, and sort value objects for querying items."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from ..exceptions import InvalidConfigValueError
from . import registry
from .attributes import Operator
from .dates import midnight, parse_agenda_window, parse_due_date, today

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

    from .tasks import TaskliItem

__all__ = [
    "Criterion",
    "Filter",
    "Sort",
    "agenda_criteria",
    "due_to_criteria",
]


@dataclass(frozen=True)
class Criterion:
    attr_key: str
    operator: Operator
    operand: object

    def matches(self, item: TaskliItem) -> bool:
        """Whether ``item`` satisfies this criterion.

        Parameters
        ----------
        item : TaskliItem
            The item to test.

        Returns
        -------
        bool
            Whether the item's ``attr_key`` value satisfies the operand.
        """

        value = getattr(item, self.attr_key)

        return self.operator.compare(value, self.operand)


@dataclass(frozen=True)
class Filter:
    criteria: tuple[Criterion, ...] = ()

    @property
    def active(self) -> bool:
        """Whether this filter carries any criteria."""

        return bool(self.criteria)

    def matches(self, item: TaskliItem) -> bool:
        """Whether ``item`` satisfies every criterion.

        An empty filter matches every item.

        Parameters
        ----------
        item : TaskliItem
            The item to test.

        Returns
        -------
        bool
            True when all criteria match, or there are none.
        """

        return all(c.matches(item) for c in self.criteria)

    def apply(self, items: Iterable[TaskliItem]) -> list[TaskliItem]:
        """Return the items that satisfy this filter, order preserved.

        Flat: each item is tested on its own, with no descent into
        ``children``. ``TaskliList.filtered_items`` is the tree-aware
        entry point that keeps an item whose descendant matches.

        Parameters
        ----------
        items : Iterable[TaskliItem]
            The items to filter.

        Returns
        -------
        list[TaskliItem]
            The matching items.
        """

        return [i for i in items if self.matches(i)]


@dataclass(frozen=True)
class Sort:
    attr_key: str
    descending: bool = False

    def __post_init__(self) -> None:
        """Reject an ``attr_key`` that names no known sort mode."""

        if self.attr_key not in registry.sortable():
            raise InvalidConfigValueError(
                f"'{self.attr_key}' is not a valid sort key."
            )

    def key(self, item: TaskliItem) -> SupportsRichComparison:
        """Return ``item``'s sort key under this sort mode.

        Parameters
        ----------
        item : TaskliItem
            The item to derive a sort key for.

        Returns
        -------
        SupportsRichComparison
            The value to sort the item by.
        """

        sort_key = registry.ATTRIBUTES[self.attr_key].sort_key
        assert sort_key is not None  # guaranteed by __post_init__.

        return sort_key(item)

    @classmethod
    def from_default_sort(cls, value: str) -> Sort:
        """Build a ``Sort`` from a config ``default_sort`` value.

        Parameters
        ----------
        value : str
            The configured default sort mode.

        Returns
        -------
        Sort
            The matching sort, using the attribute's registered default
            direction.
        """

        attr = registry.sortable().get(value)
        if attr is None:
            raise InvalidConfigValueError(
                f"'{value}' is not a valid sort key."
            )

        return cls(value, descending=attr.sort_descending)


def due_to_criteria(raw: str) -> tuple[Criterion, ...]:
    """Build the due-date view criteria for a ``--due`` token.

    ``overdue`` matches not-done items due before today; any other
    token is parsed as a single day and matched exactly.

    Parameters
    ----------
    raw : str
        The user-supplied ``--due`` value.

    Returns
    -------
    tuple[Criterion, ...]
        The criteria a due-date filter should AND together.
    """

    if raw.strip().casefold() == "overdue":
        return (
            Criterion("due_date", Operator.LT, midnight(today())),
            Criterion("done", Operator.EQ, False),
        )

    # parse_due_date midnight-normalizes its result, so this exact-datetime
    # match agrees with _due_render_style's calendar-day comparison.
    return (Criterion("due_date", Operator.EQ, parse_due_date(raw)),)


def agenda_criteria(window: str) -> tuple[Criterion, ...]:
    """Build the criteria for a ``--agenda`` window.

    ``overdue`` matches not-done items due before today; any other
    token bounds a forward-looking, inclusive window of not-done items
    due from today through ``today + N`` days (``today`` is ``N=0``,
    ``week`` is ``N=7``).

    Parameters
    ----------
    window : str
        The user-supplied ``--agenda`` value.

    Returns
    -------
    tuple[Criterion, ...]
        The criteria an agenda filter should AND together.
    """

    keyword = parse_agenda_window(window)
    if keyword == "overdue":
        return due_to_criteria("overdue")

    days = (
        0 if keyword == "today" else 7 if keyword == "week" else int(keyword)
    )
    start = midnight(today())
    end = start + timedelta(days=days + 1)

    return (
        Criterion("due_date", Operator.GTE, start),
        Criterion("due_date", Operator.LT, end),
        Criterion("done", Operator.EQ, False),
    )
