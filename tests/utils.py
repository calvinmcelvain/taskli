"""Shared builders for filter and sort test call sites."""

import json
from pathlib import Path
from typing import Any

from taskli.models import Criterion, Operator, Priority, Sort, SortBy

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
