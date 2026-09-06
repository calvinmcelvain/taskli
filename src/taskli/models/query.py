"""Filter, criterion, and sort value objects for querying items."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, assert_never

from ..exceptions import InvalidConfigValueError

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

    from .config import SortBy
    from .tasks import TaskliItem

__all__ = ["Criterion", "Filter", "Operator", "Sort"]


class Operator(Enum):
    """A comparison a criterion can apply to an attribute value."""

    EQ = "eq"
    CONTAINS = "contains"

    def compare(self, value: object, operand: object) -> bool:
        """Test ``value`` against ``operand`` under this operator.

        Parameters
        ----------
        value : object
            The item attribute value to test.
        operand : object
            The value the criterion holds to test against.

        Returns
        -------
        bool
            Whether ``value`` satisfies ``operand`` under this operator.
        """

        if self is Operator.EQ:
            return value == operand

        if self is Operator.CONTAINS:
            # case-insensitive containment: substring for a plain string,
            # exact membership for any other iterable (reproduces the old
            # ``needle in (t.lower() for t in item.tags)`` on tags).
            needle = str(operand).lower()
            if isinstance(value, str):
                return needle in value.lower()
            if isinstance(value, Iterable):
                return needle in (str(v).lower() for v in value)

            return False

        assert_never(self)


@dataclass(frozen=True)
class Criterion:
    """A single attribute test: an operator applied to ``attr_key``."""

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
    """An AND-combined set of criteria applied to items."""

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


_SORT_KEYS: dict[str, Callable[[TaskliItem], SupportsRichComparison]] = {
    "created_at": lambda item: item.created_at,
    "priority": lambda item: item.priority.index,
    "tags": lambda item: (
        "".join(item.tags) == "",
        ",".join(sorted(item.tags)),
    ),
}


@dataclass(frozen=True)
class Sort:
    """A sort mode: an item attribute key plus direction."""

    attr_key: str
    descending: bool = False

    def __post_init__(self) -> None:
        """Reject an ``attr_key`` that names no known sort mode."""

        if self.attr_key not in _SORT_KEYS:
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

        return _SORT_KEYS[self.attr_key](item)

    @classmethod
    def from_default_sort(cls, value: SortBy) -> Sort:
        """Build a ``Sort`` from a config ``default_sort`` value.

        Parameters
        ----------
        value : SortBy
            The configured default sort mode.

        Returns
        -------
        Sort
            The matching sort, descending only for ``"priority"``.
        """

        return cls(value, descending=(value == "priority"))
