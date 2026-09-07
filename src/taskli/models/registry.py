"""Per-attribute domain and render metadata, collected into one table."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from typing import TYPE_CHECKING, Literal

from .attributes import Operator, Priority
from .dates import parse_due_date, today

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

    from .tasks import TaskliItem

_Justify = Literal["default", "left", "center", "right", "full"]

__all__ = [
    "ATTRIBUTES",
    "Attribute",
    "RenderColumn",
    "filterable",
    "modifiable",
    "renderable",
    "sortable",
]


@dataclass(frozen=True)
class Attribute:
    name: str
    filter_operators: tuple[Operator, ...] = ()
    filter_default_operator: Operator | None = None
    sort_key: Callable[[TaskliItem], SupportsRichComparison] | None = None
    sort_descending: bool = False
    column_header: str | None = None
    column_justify: _Justify = "left"
    render_format: Callable[[TaskliItem], str] | None = None
    render_style: Callable[[TaskliItem], str | None] | None = None
    parse: Callable[[str], object] | None = None
    modifier_ops: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RenderColumn:
    header: str
    justify: _Justify
    format: Callable[[TaskliItem], str]
    style: Callable[[TaskliItem], str | None] | None


def _due_render_style(item: TaskliItem) -> str | None:
    """Return the rich style for an item's due-date cell."""

    if item.due_date is None or item.done:
        return None
    due, now = item.due_date.date(), today()
    if due < now:
        return "red"
    if due == now:
        return "yellow"

    return None


# insertion order is the render column order.
ATTRIBUTES: dict[str, Attribute] = {
    "id": Attribute(
        name="id",
        column_header="ID",
        column_justify="right",
        render_format=lambda item: item.id,
    ),
    "status": Attribute(
        name="status",
        column_header="State",
        column_justify="center",
        render_format=lambda item: item.status.marker,
    ),
    "text": Attribute(
        name="text",
        column_header="Text",
        # indent nested rows by depth; depth is the dot count in the path.
        render_format=lambda item: "  " * item.id.count(".") + item.text,
        render_style=lambda item: "dim" if item.done else None,
        modifier_ops=frozenset({"edit"}),
    ),
    "description": Attribute(
        name="description",
        # empty string is a real (blank-headed) column; None is skipped.
        column_header="",
        column_justify="center",
        render_format=lambda item: "*" if item.description else "",
        parse=lambda s: s or None,
        modifier_ops=frozenset({"add", "edit"}),
    ),
    "priority": Attribute(
        name="priority",
        column_header="Priority",
        column_justify="left",
        render_format=lambda item: item.priority.label,
        render_style=lambda item: item.priority.color,
        filter_operators=(Operator.EQ,),
        filter_default_operator=Operator.EQ,
        sort_key=lambda item: item.priority.index,
        sort_descending=True,
        parse=lambda s: Priority[s.upper()],
        modifier_ops=frozenset({"add", "edit"}),
    ),
    "tags": Attribute(
        name="tags",
        column_header="Tags",
        column_justify="left",
        render_format=lambda item: ", ".join(item.tags),
        filter_operators=(Operator.CONTAINS,),
        filter_default_operator=Operator.CONTAINS,
        sort_key=lambda item: (
            "".join(item.tags) == "",
            ",".join(sorted(item.tags)),
        ),
        modifier_ops=frozenset({"add", "edit"}),
    ),
    "due_date": Attribute(
        name="due_date",
        column_header="Due",
        column_justify="left",
        render_format=lambda item: (
            item.due_date.date().isoformat() if item.due_date else ""
        ),
        render_style=_due_render_style,
        # the operators due_to_criteria emits; the view path routes
        # --due through that, not the generic single-operator filter.
        filter_operators=(Operator.EQ, Operator.LT),
        filter_default_operator=Operator.EQ,
        sort_key=lambda item: (
            item.due_date is None,
            item.due_date or datetime.max,
        ),
        sort_descending=False,
        parse=parse_due_date,
        modifier_ops=frozenset({"add", "edit"}),
    ),
    "created_at": Attribute(
        name="created_at",
        sort_key=lambda item: item.created_at,
    ),
    "color": Attribute(name="color"),
}


@cache
def sortable() -> dict[str, Attribute]:
    """Return the attributes that define a sort key, keyed by name.

    Returns
    -------
    dict[str, Attribute]
        Every entry whose ``sort_key`` is set, in ``ATTRIBUTES`` order.
    """

    return {name: attr for name, attr in ATTRIBUTES.items() if attr.sort_key}


@cache
def renderable() -> list[RenderColumn]:
    """Return the resolved table columns, in column order.

    Returns
    -------
    list[RenderColumn]
        One column per attribute carrying both a ``column_header`` and a
        ``render_format``, in ``ATTRIBUTES`` order.
    """

    columns: list[RenderColumn] = []
    for attr in ATTRIBUTES.values():
        if attr.column_header is None or attr.render_format is None:
            continue
        columns.append(
            RenderColumn(
                attr.column_header,
                attr.column_justify,
                attr.render_format,
                attr.render_style,
            )
        )

    return columns


@cache
def filterable() -> dict[str, Attribute]:
    """Return the attributes that can be filtered, keyed by name.

    Returns
    -------
    dict[str, Attribute]
        Every entry whose ``filter_operators`` is non-empty, in
        ``ATTRIBUTES`` order.
    """

    return {
        name: attr
        for name, attr in ATTRIBUTES.items()
        if attr.filter_operators
    }


@cache
def modifiable(op: str) -> dict[str, Attribute]:
    """Return the attributes settable as an item modifier on ``op``.

    Parameters
    ----------
    op : str
        The item-action op name, e.g. ``"add"`` or ``"edit"``.

    Returns
    -------
    dict[str, Attribute]
        Every entry whose ``modifier_ops`` contains ``op``, in
        ``ATTRIBUTES`` order.
    """

    return {
        name: attr
        for name, attr in ATTRIBUTES.items()
        if op in attr.modifier_ops
    }
