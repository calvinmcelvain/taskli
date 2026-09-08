"""List storage functions."""

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from . import migrations
from .exceptions import (
    CorruptedConfigFileError,
    CorruptedListFileError,
    InvalidListNameError,
    ListAlreadyExistsError,
    ListNotFoundError,
    OutdatedConfigFileError,
    OutdatedListFileError,
    TaskliError,
    TooManyAncestorListsError,
)
from .hierarchy import ancestor_chain, descendant_list_names
from .models import Color, Config, Sort, TaskliList


def resolve_storage_dir() -> Path:
    """Return the directory task lists are stored in, creating it.

    Returns
    -------
    Path
        The storage directory, guaranteed to exist.
    """

    path = Path(os.environ.get("TASKLI_PATH", Path.home() / ".taskli"))
    storage_dir = path.expanduser()

    storage_dir.mkdir(parents=True, exist_ok=True)

    return storage_dir


def config_file_path(storage_dir: Path) -> Path:
    """Return the config file path within the storage directory.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.

    Returns
    -------
    Path
        Path to the config file, `.taskli.json`.
    """

    return storage_dir / ".taskli.json"


def load_config(storage_dir: Path) -> Config:
    """Load the config from disk, creating it with defaults if missing.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.

    Returns
    -------
    Config
        The loaded, or newly created and saved, config.
    """

    path = config_file_path(storage_dir)
    if not path.exists():
        config = Config()
        save_config(storage_dir, config)

        return config

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise CorruptedConfigFileError(
            f"config file '{path}' is corrupted and could not be read."
        ) from e

    if not isinstance(raw, dict):
        raise CorruptedConfigFileError(
            f"config file '{path}' is corrupted and could not be read."
        )

    if migrations.config_needs_migration(raw):
        raise OutdatedConfigFileError(
            f"config file '{path}' is on an older schema; run 'tk --migrate'."
        )

    try:
        return Config.model_validate(raw)
    except ValidationError as e:
        raise CorruptedConfigFileError(
            f"config file '{path}' is corrupted and could not be read."
        ) from e


def save_config(storage_dir: Path, config: Config) -> None:
    """Persist the config to its JSON file.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    config : Config
        The config to save.
    """

    path = config_file_path(storage_dir)
    raw = config.model_dump(mode="json")
    raw["version"] = migrations.CURRENT_CONFIG_VERSION
    path.write_text(json.dumps(raw, indent=2))

    return None


def list_file_path(storage_dir: Path, name: str) -> Path:
    """Return the JSON file path for a given list name.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.

    Returns
    -------
    Path
        Path to the list's JSON file.

    Notes
    -----
    Cannot have descendant lists with a depth greater than 2.
    """

    _reserved = {".", "..", "con", "prn", "aux", "nul"}
    lowered = name.lower()
    if lowered in _reserved or "/" in lowered or "\\" in lowered:
        raise InvalidListNameError(f"'{name}' is not a valid list name.")

    # reject empty segments in a nested name.
    segments = name.split(".")
    if len(segments) > 1 and any(not segment for segment in segments):
        raise InvalidListNameError(f"'{name}' is not a valid list name.")

    # restrict depth to 2.
    if len(ancestor_chain(name)) > 2:
        raise TooManyAncestorListsError(
            f"'{name}' is nested too deep (max 2 sublist levels)."
        )

    return storage_dir / f"{name}.json"


def _inherited_color(storage_dir: Path, name: str) -> Color | None:
    """Return the nearest existing ancestor list's color, or None.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name whose ancestor colors to inspect.

    Returns
    -------
    Color | None
        The color of the nearest existing ancestor list, or None when
        no ancestor exists or the nearest ones cannot be loaded.
    """

    for ancestor in reversed(ancestor_chain(name)):
        if not list_exists(storage_dir, ancestor):
            continue
        try:
            return load_list(storage_dir, ancestor).color
        except TaskliError:
            continue

    return None


def _new_list_color(
    storage_dir: Path,
    name: str,
    explicit: Color | None,
    config: Config | None,
) -> Color | None:
    """Resolve a new list's color: explicit > inherited > default.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The new list's name.
    explicit : Color | None
        A caller-supplied color, which always wins when set.
    config : Config | None
        The active config, or None to keep the pre-inheritance behavior
        (an explicit color, else None).

    Returns
    -------
    Color | None
        The resolved color for the new list.
    """

    if explicit is not None:
        return explicit
    if config is None:
        return None
    if config.inherit_sublist_color:
        inherited = _inherited_color(storage_dir, name)
        if inherited is not None:
            return inherited

    return config.default_color


def ensure_ancestors(
    storage_dir: Path,
    name: str,
    *,
    config: Config | None = None,
) -> None:
    """Create any missing ancestor lists in `name`'s dot-chain.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name whose ancestors should exist.
    config : Config | None, optional
        When given, each auto-created ancestor resolves its color via
        `_new_list_color`; when None (the default), ancestors are
        created with the bare model default, byte-identical to the
        pre-inheritance behavior.
    """

    for ancestor in ancestor_chain(name):
        if not list_exists(storage_dir, ancestor):
            if config is None:
                save_list(storage_dir, TaskliList(name=ancestor))
            else:
                save_list(
                    storage_dir,
                    TaskliList(
                        name=ancestor,
                        color=_new_list_color(
                            storage_dir, ancestor, None, config
                        ),
                    ),
                )

    return None


def list_exists(storage_dir: Path, name: str) -> bool:
    """Return whether a list file already exists.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.

    Returns
    -------
    bool
        True if the list's file exists.
    """

    return list_file_path(storage_dir, name).exists()


def list_all_lists(storage_dir: Path) -> list[str]:
    """Return the names of all existing lists, sorted.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.

    Returns
    -------
    list[str]
        Sorted list names.
    """

    config_path = config_file_path(storage_dir)

    return sorted(
        path.stem for path in storage_dir.glob("*.json") if path != config_path
    )


def create_list(
    storage_dir: Path,
    name: str,
    *,
    color: Color | None = None,
    config: Config | None = None,
) -> TaskliList:
    """Create and persist a new, empty list.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The new list's name.
    color : Color | None, optional
        The list's display color, by default none.
    config : Config | None, optional
        When given, an unset `color` is resolved via `_new_list_color`
        (nearest existing ancestor's color, else `config.default_color`);
        when None (the default), an unset `color` stays None.

    Returns
    -------
    TaskliList
        The newly created, empty list.
    """

    if list_exists(storage_dir, name):
        raise ListAlreadyExistsError(f"list '{name}' already exists.")

    # if a descendant list (e.g., sublist), ensure all lists before it have
    # already been created.
    ensure_ancestors(storage_dir, name, config=config)

    task_list = TaskliList(
        name=name,
        color=_new_list_color(storage_dir, name, color, config),
    )
    save_list(storage_dir, task_list)

    return task_list


def delete_list(storage_dir: Path, name: str) -> list[str]:
    """Delete a list's file and all of its descendant lists.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.

    Returns
    -------
    list[str]
        Names of descendant lists that were also deleted.
    """

    path = list_file_path(storage_dir, name)
    if not path.exists():
        raise ListNotFoundError(f"list '{name}' does not exist.")

    # delete all descendants of list, if exist.
    descendants = descendant_list_names(name, list_all_lists(storage_dir))
    for descendant in descendants:
        list_file_path(storage_dir, descendant).unlink()

    path.unlink()

    return descendants


def rename_list(
    storage_dir: Path, old_name: str, new_name: str
) -> list[tuple[str, str]]:
    """Rename a list's file and all of its descendant lists.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    old_name : str
        The list's current name.
    new_name : str
        The list's new name.

    Returns
    -------
    list[tuple[str, str]]
        (old, new) name pairs for the list and every renamed descendant,
        in old-name-ascending order. Empty if `old_name` == `new_name`.
    """

    if old_name == new_name:
        return []

    path = list_file_path(storage_dir, old_name)
    if not path.exists():
        raise ListNotFoundError(f"list '{old_name}' does not exist.")

    descendants = descendant_list_names(old_name, list_all_lists(storage_dir))
    renames = [(old_name, new_name)] + [
        (descendant, new_name + descendant[len(old_name) :])
        for descendant in descendants
    ]

    # validate every target before touching any file, so a colliding
    # descendant target doesn't leave a partial rename on disk.
    for _, target in renames:
        if list_exists(storage_dir, target):
            raise ListAlreadyExistsError(f"list '{target}' already exists.")

    ensure_ancestors(storage_dir, new_name)

    for old, new in renames:
        task_list = load_list(storage_dir, old)
        task_list.name = new

        save_list(storage_dir, task_list)
        list_file_path(storage_dir, old).unlink()

    return renames


def load_list(storage_dir: Path, name: str) -> TaskliList:
    """Load a list from disk, parsing its JSON file.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.

    Returns
    -------
    TaskliList
        The loaded list.
    """

    path = list_file_path(storage_dir, name)
    if not path.exists():
        config = load_config(storage_dir)
        canonical_default = config.default_list.replace(
            config.sublist_delimiter, "."
        )
        if name == canonical_default:
            task_list = TaskliList(name=name)
            save_list(storage_dir, task_list)

            return task_list

        raise ListNotFoundError(
            f"list '{name}' does not exist. Run 'task --lists' to see "
            "available lists."
        )

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise CorruptedListFileError(
            f"list file '{path}' is corrupted and could not be read."
        ) from e

    if not isinstance(raw, dict):
        raise CorruptedListFileError(
            f"list file '{path}' is corrupted and could not be read."
        )

    if migrations.list_needs_migration(raw):
        raise OutdatedListFileError(
            f"list file '{path}' is on an older schema; run 'tk --migrate'."
        )

    try:
        task_list = TaskliList.model_validate(raw)
    except ValidationError as e:
        raise CorruptedListFileError(
            f"list file '{path}' is corrupted and could not be read."
        ) from e

    task_list.reindex()

    return task_list


def load_or_create_list(
    storage_dir: Path,
    name: str,
    *,
    config: Config | None = None,
) -> TaskliList:
    """Load a list, creating it empty if it doesn't exist yet.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.
    config : Config | None, optional
        When given, a newly created list resolves its color via
        `_new_list_color`; when None (the default), it is created with
        the bare model default.

    Returns
    -------
    TaskliList
        The loaded or newly created list.
    """

    if list_exists(storage_dir, name):
        return load_list(storage_dir, name)

    ensure_ancestors(storage_dir, name, config=config)

    # `config is None` is the legacy path (bare model default); every
    # current caller in `logic` passes a config.
    if config is None:
        task_list = TaskliList(name=name)
    else:
        task_list = TaskliList(
            name=name,
            color=_new_list_color(storage_dir, name, None, config),
        )
    save_list(storage_dir, task_list)

    return task_list


def save_list(storage_dir: Path, task_list: TaskliList) -> None:
    """Persist a list to its JSON file.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    task_list : TaskliList
        The list to save.
    """

    if task_list.view_only:
        raise RuntimeError("refusing to save a view-only (filtered) list")

    task_list.sort_by_index()
    path = list_file_path(storage_dir, task_list.name)
    raw = task_list.model_dump(mode="json")
    raw["version"] = migrations.CURRENT_LIST_VERSION
    path.write_text(json.dumps(raw, indent=2))

    return None


def resort_all_lists(storage_dir: Path, sort: Sort) -> None:
    """Resort and reindex every list on disk by ``sort``.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    sort : Sort
        The sort mode to apply.
    """

    for name in list_all_lists(storage_dir):
        try:
            task_list = load_list(storage_dir, name)
        except TaskliError:
            continue

        task_list.resort(sort)
        save_list(storage_dir, task_list)

    return None


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` via a sibling temp file and rename."""

    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)

    return None


def _migrate_file(
    path: Path,
    needs_migration: Callable[[dict[str, Any]], bool],
    migrate: Callable[[dict[str, Any]], dict[str, Any]],
    validate: Callable[[dict[str, Any]], object],
) -> str:
    """Migrate one file in place, returning its outcome string.

    Parameters
    ----------
    path : Path
        The file to migrate.
    needs_migration : Callable[[dict[str, Any]], bool]
        Predicate telling whether the parsed dict is on an older schema.
    migrate : Callable[[dict[str, Any]], dict[str, Any]]
        The migration to apply when it is.
    validate : Callable[[dict[str, Any]], object]
        A model validator run on the migrated dict before it is written;
        its return value is ignored, only a raised ``ValidationError``
        matters.

    Returns
    -------
    str
        ``"current"`` when nothing was pending, ``"migrated"`` when a
        migration was applied and written, or ``"unreadable"`` when the
        file could not be read or parsed, its structure was too malformed
        for the migration to run, or the migrated form failed to validate
        (the file is left untouched in every failing case).
    """

    try:
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict):
            return "unreadable"
        if not needs_migration(raw):
            return "current"
        migrated = migrate(raw)
        validate(migrated)
        _atomic_write(path, json.dumps(migrated, indent=2))
    except Exception:
        # any failure on one file is reported and skipped rather than
        # aborting the whole --migrate walk.
        return "unreadable"

    return "migrated"


def migrate_all(storage_dir: Path) -> list[tuple[str, str]]:
    """Migrate every on-disk file to the current schema, in place.

    Walks the config file first, then every list, migrating any that is
    on an older schema and leaving current ones untouched. Idempotent: a
    second call over an already-migrated directory reports every file as
    ``"current"``.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.

    Returns
    -------
    list[tuple[str, str]]
        One ``(name, outcome)`` pair per file, config first then lists in
        name order. ``outcome`` is ``"migrated"``, ``"current"``, or
        ``"unreadable"`` (see ``_migrate_file``).
    """

    results: list[tuple[str, str]] = []

    config_path = config_file_path(storage_dir)
    if config_path.exists():
        results.append(
            (
                "config",
                _migrate_file(
                    config_path,
                    migrations.config_needs_migration,
                    migrations.migrate_config,
                    Config.model_validate,
                ),
            )
        )

    for name in list_all_lists(storage_dir):
        try:
            path = list_file_path(storage_dir, name)
        except TaskliError:
            # e.g. a legacy file nested too deep to be a valid list name;
            # report it and keep walking rather than aborting the run.
            results.append((name, "unreadable"))
            continue

        results.append(
            (
                name,
                _migrate_file(
                    path,
                    migrations.list_needs_migration,
                    migrations.migrate_list,
                    TaskliList.model_validate,
                ),
            )
        )

    return results
