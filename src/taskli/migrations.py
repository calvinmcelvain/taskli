"""Versioned migrations for on-disk list and config files."""

import copy
from collections.abc import Callable
from typing import Any

# the historical label strings below ("done", "todo", "high", ...) are a
# frozen contract: each migration step captures a past on-disk shape, so
# the literals are hard-coded here rather than imported from
# models/attributes.py -- a later enum-label rename must not retroactively
# change what an old migration means.

CURRENT_LIST_VERSION = 1
CURRENT_CONFIG_VERSION = 1


def file_version(raw: dict[str, Any]) -> int:
    """Return the schema version recorded in a parsed file dict.

    Parameters
    ----------
    raw : dict[str, Any]
        The parsed JSON contents of a list or config file.

    Returns
    -------
    int
        The recorded ``version``, or 0 when the key is absent, ``null``,
        or not an integer.
    """

    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        return 0

    return version


def _list_base_to_v1(raw: dict[str, Any]) -> dict[str, Any]:
    """Bring a pre-versioned list dict up to the current v1 item shape.

    v1 was introduced in #101 and redefined by #92 (recursive subtasks)
    before any real data reached it, so this single step also stringifies
    each ``id`` into a dotted path and defaults ``children`` -- there is no
    v2. The historical label strings below stay frozen regardless.
    """

    for item in raw.get("items", []):
        if "done" in item and "status" not in item:
            item["status"] = "done" if item.pop("done") else "todo"
        if item.get("modified_at") is None and "created_at" in item:
            item["modified_at"] = item["created_at"]
        for key in ("priority", "status"):
            value = item.get(key)
            if isinstance(value, dict):
                item[key] = value.get("label")
        if "id" in item:
            item["id"] = str(item["id"])
        # base/v0 files are flat, so no recursion into children here.
        item.setdefault("children", [])

    return raw


def _config_base_to_v1(raw: dict[str, Any]) -> dict[str, Any]:
    """Bring a pre-versioned config dict up to the v1 field shape."""

    value = raw.get("default_priority")
    if isinstance(value, dict):
        raw["default_priority"] = value.get("label")

    return raw


# index i migrates a file at version i to version i + 1.
_LIST_MIGRATIONS: list[Callable[[dict[str, Any]], dict[str, Any]]] = [
    _list_base_to_v1
]
_CONFIG_MIGRATIONS: list[Callable[[dict[str, Any]], dict[str, Any]]] = [
    _config_base_to_v1
]


def migrate_list(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a list dict migrated to the current schema.

    Parameters
    ----------
    raw : dict[str, Any]
        The parsed JSON contents of a list file.

    Returns
    -------
    dict[str, Any]
        A new dict with every pending migration applied and ``version``
        stamped to ``CURRENT_LIST_VERSION``. An input already at or above
        the current version is returned unchanged.
    """

    working = copy.deepcopy(raw)
    for migration in _LIST_MIGRATIONS[file_version(working) :]:
        working = migration(working)
    if file_version(working) < CURRENT_LIST_VERSION:
        working["version"] = CURRENT_LIST_VERSION

    return working


def migrate_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a config dict migrated to the current schema.

    Parameters
    ----------
    raw : dict[str, Any]
        The parsed JSON contents of a config file.

    Returns
    -------
    dict[str, Any]
        A new dict with every pending migration applied and ``version``
        stamped to ``CURRENT_CONFIG_VERSION``. An input already at or above
        the current version is returned unchanged.
    """

    working = copy.deepcopy(raw)
    for migration in _CONFIG_MIGRATIONS[file_version(working) :]:
        working = migration(working)
    if file_version(working) < CURRENT_CONFIG_VERSION:
        working["version"] = CURRENT_CONFIG_VERSION

    return working


def list_needs_migration(raw: dict[str, Any]) -> bool:
    """Return whether a parsed list dict is on an older schema.

    Parameters
    ----------
    raw : dict[str, Any]
        The parsed JSON contents of a list file.

    Returns
    -------
    bool
        True when the file's version is below ``CURRENT_LIST_VERSION``.
    """

    return file_version(raw) < CURRENT_LIST_VERSION


def config_needs_migration(raw: dict[str, Any]) -> bool:
    """Return whether a parsed config dict is on an older schema.

    Parameters
    ----------
    raw : dict[str, Any]
        The parsed JSON contents of a config file.

    Returns
    -------
    bool
        True when the file's version is below ``CURRENT_CONFIG_VERSION``.
    """

    return file_version(raw) < CURRENT_CONFIG_VERSION
