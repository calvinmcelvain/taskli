"""Shared builders and helpers for test call sites."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from taskli.models import (
    Criterion,
    Operator,
    Priority,
    Sort,
    SortBy,
    TaskliItem,
    TaskliList,
)

_RESOURCES = Path(__file__).parent / "resources"


def resource_text(name: str) -> str:
    """Return the raw text of a JSON fixture from ``tests/resources``.

    Parameters
    ----------
    name : str
        The fixture file name.

    Returns
    -------
    str
        The file contents.
    """

    return (_RESOURCES / name).read_text()


def resource_dict(name: str) -> dict[str, Any]:
    """Return a JSON fixture from ``tests/resources`` parsed to a dict.

    Parameters
    ----------
    name : str
        The fixture file name.

    Returns
    -------
    dict[str, Any]
        The parsed JSON object.
    """

    data: dict[str, Any] = json.loads(resource_text(name))

    return data


def freeze_today(monkeypatch: pytest.MonkeyPatch, value: date) -> None:
    """Pin ``models.dates.today`` and its re-bound copies to ``value``.

    ``today`` is imported by name into ``models.query`` and
    ``models.registry``, so each binding is patched independently.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        The active monkeypatch fixture.
    value : date
        The calendar day every ``today()`` call should return.
    """

    for target in (
        "taskli.models.dates.today",
        "taskli.models.query.today",
        "taskli.models.registry.today",
    ):
        monkeypatch.setattr(target, lambda: value)


def tag_criterion(name: str) -> Criterion:
    """Build a ``CONTAINS`` criterion matching ``name`` against tags.

    Parameters
    ----------
    name : str
        The tag to look for.

    Returns
    -------
    Criterion
        A criterion testing membership in an item's ``tags``.
    """

    return Criterion("tags", Operator.CONTAINS, name)


def priority_criterion(p: Priority) -> Criterion:
    """Build an ``EQ`` criterion matching ``p`` against an item's priority.

    Parameters
    ----------
    p : Priority
        The priority to match.

    Returns
    -------
    Criterion
        A criterion testing an item's ``priority`` for equality.
    """

    return Criterion("priority", Operator.EQ, p)


def sort(name: SortBy) -> Sort:
    """Build the ``Sort`` for a config ``default_sort`` mode.

    Delegates to ``Sort.from_default_sort`` so the direction rule has a
    single definition.

    Parameters
    ----------
    name : SortBy
        The sort attribute key.

    Returns
    -------
    Sort
        The sort ``Sort.from_default_sort`` produces for ``name``.
    """

    return Sort.from_default_sort(name)


def add_item(
    task_list: TaskliList,
    text: str,
    *,
    created_at: datetime | None = None,
    modified_at: datetime | None = None,
    **attrs: object,
) -> TaskliItem:
    """Add an item to ``task_list`` from keyword attributes.

    Wraps ``TaskliList.add_item`` so tests can pass ``priority=`` /
    ``tags=`` as keywords instead of assembling the ``attrs`` mapping
    at every call site.

    Parameters
    ----------
    task_list : TaskliList
        The list to append to.
    text : str
        The item text.
    created_at : datetime | None
        An explicit creation timestamp, or ``None`` for "now".
    modified_at : datetime | None
        An explicit modification timestamp, or ``None`` for "now".
    **attrs : object
        Settable item attributes, forwarded as the ``attrs`` mapping.

    Returns
    -------
    TaskliItem
        The newly added item.
    """

    return task_list.add_item(
        text, attrs or None, created_at=created_at, modified_at=modified_at
    )


def edit_item(
    task_list: TaskliList, item_id: int, **attrs: object
) -> TaskliItem:
    """Edit an item on ``task_list`` from keyword attributes.

    Wraps ``TaskliList.edit_item`` so tests can pass ``text=`` /
    ``priority=`` / ``tags=`` as keywords instead of the ``attrs``
    mapping; an empty call forwards ``{}``.

    Parameters
    ----------
    task_list : TaskliList
        The list owning the item.
    item_id : int
        The id of the item to edit.
    **attrs : object
        Field values to apply, forwarded as the ``attrs`` mapping.

    Returns
    -------
    TaskliItem
        The edited item.
    """

    return task_list.edit_item(item_id, attrs)
