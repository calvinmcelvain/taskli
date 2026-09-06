"""Per-attribute domain and render metadata, collected into one table."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Literal

from .attributes import Operator

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

    from .tasks import TaskliItem

_Justify = Literal["default", "left", "center", "right", "full"]

__all__ = [
    "ATTRIBUTES",
    "Attribute",
    "RenderColumn",
    "filterable",
    "renderable",
    "sortable",
]


@dataclass(frozen=True)
class Attribute:
    """Domain and render facets of one item or list attribute.

    Every facet is independently optional: an attribute may be
    filterable, sortable, renderable, any combination, or none. The
    ``render_*`` callables take the whole ``TaskliItem`` (matching
    ``sort_key``); ``render_style`` returns a rich style or color name
    (``"red"``, ``"dim"``) and never imports rich.
    """

    name: str
    filter_operators: tuple[Operator, ...] = ()
    filter_default_operator: Operator | None = None
    sort_key: Callable[[TaskliItem], SupportsRichComparison] | None = None
    sort_descending: bool = False
    column_header: str | None = None
    column_justify: _Justify = "left"
    render_format: Callable[[TaskliItem], str] | None = None
    render_style: Callable[[TaskliItem], str | None] | None = None


@dataclass(frozen=True)
class RenderColumn:
    """A resolved table column: the render facets, none optional.

    Built by :func:`renderable` from an :class:`Attribute` that carries
    both a ``column_header`` and a ``render_format``, so callers iterate
    columns without re-checking that invariant per cell.
    """

    header: str
    justify: _Justify
    format: Callable[[TaskliItem], str]
    style: Callable[[TaskliItem], str | None] | None


# insertion order is the render column order.
ATTRIBUTES: dict[str, Attribute] = {
    "id": Attribute(
        name="id",
        column_header="ID",
        column_justify="right",
        render_format=lambda item: str(item.id),
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
        render_format=lambda item: item.text,
        render_style=lambda item: "dim" if item.done else None,
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
    ),
    "created_at": Attribute(
        name="created_at",
        sort_key=lambda item: item.created_at,
    ),
    # a list attribute, not an item one: no filter/sort/render facets.
    # kept here only so every cli.MODIFIER_FLAGS key resolves to a
    # registry entry (the parity test). cli._validate uses hard-coded
    # dest sets, not the registry.
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
