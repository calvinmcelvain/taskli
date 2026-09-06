"""Filter, criterion, and sort value objects for querying items."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..exceptions import InvalidConfigValueError
from . import registry
from .attributes import Operator

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

    from .tasks import TaskliItem

__all__ = ["Criterion", "Filter", "Sort"]


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


@dataclass(frozen=True)
class Sort:
    """A sort mode: an item attribute key plus direction."""

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
