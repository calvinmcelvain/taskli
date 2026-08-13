"""List storage functions."""

import os
from pathlib import Path

from pydantic import ValidationError

from .exceptions import (
    CorruptedConfigFileError,
    CorruptedListFileError,
    InvalidListNameError,
    ListAlreadyExistsError,
    ListNotFoundError,
    TaskliError,
    TooManyAncestorListsError,
)
from .models import Color, Config, SortBy, TaskliList


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
        return Config.model_validate_json(path.read_text())
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
    path.write_text(config.model_dump_json(indent=2))

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


def parent_list_name(name: str) -> str | None:
    """Return the immediate parent list name, or None if top-level.

    Parameters
    ----------
    name : str
        The list name.

    Returns
    -------
    str | None
        The text before the last '.', or None if `name` has no '.'.
    """

    if "." not in name:
        return None

    return name.rsplit(".", 1)[0]


def child_list_names(name: str, all_names: list[str]) -> list[str]:
    """Return the immediate children of `name` from `all_names`.

    Parameters
    ----------
    name : str
        The candidate parent list name.
    all_names : list[str]
        The full set of existing list names to search.

    Returns
    -------
    list[str]
        Names in `all_names` whose immediate parent is `name`, sorted.
    """

    return sorted(n for n in all_names if parent_list_name(n) == name)


def descendant_list_names(name: str, all_names: list[str]) -> list[str]:
    """Return all descendants (any depth) of `name` from `all_names`.

    Parameters
    ----------
    name : str
        The ancestor list name.
    all_names : list[str]
        The full set of existing list names to search.

    Returns
    -------
    list[str]
        Names in `all_names` nested under `name`, sorted.
    """

    prefix = f"{name}."

    return sorted(n for n in all_names if n.startswith(prefix))


def ancestor_chain(name: str) -> list[str]:
    """Return all ancestor names of `name`, nearest-root first.

    Parameters
    ----------
    name : str
        The list name (may or may not exist).

    Returns
    -------
    list[str]
        E.g. for "a.b.c" returns ["a", "a.b"]. Empty if `name` has no
        '.'.
    """

    segments = name.split(".")

    return [".".join(segments[:i]) for i in range(1, len(segments))]


def ensure_ancestors(storage_dir: Path, name: str) -> None:
    """Create any missing ancestor lists in `name`'s dot-chain.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name whose ancestors should exist.
    """

    for ancestor in ancestor_chain(name):
        if not list_exists(storage_dir, ancestor):
            save_list(storage_dir, TaskliList(name=ancestor))

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

    Returns
    -------
    TaskliList
        The newly created, empty list.
    """

    if list_exists(storage_dir, name):
        raise ListAlreadyExistsError(f"list '{name}' already exists.")

    # if a descendant list (e.g., sublist), ensure all lists before it have
    # already been created.
    ensure_ancestors(storage_dir, name)

    task_list = TaskliList(name=name, color=color)
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
        task_list = TaskliList.model_validate_json(path.read_text())
    except ValidationError as e:
        raise CorruptedListFileError(
            f"list file '{path}' is corrupted and could not be read."
        ) from e

    task_list.reindex()
    task_list.backfill_modified_at()

    return task_list


def load_or_create_list(storage_dir: Path, name: str) -> TaskliList:
    """Load a list, creating it empty if it doesn't exist yet.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.

    Returns
    -------
    TaskliList
        The loaded or newly created list.
    """

    if list_exists(storage_dir, name):
        return load_list(storage_dir, name)

    ensure_ancestors(storage_dir, name)

    task_list = TaskliList(name=name)
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

    task_list.sort_by_index()
    path = list_file_path(storage_dir, task_list.name)
    path.write_text(task_list.model_dump_json(indent=2))

    return None


def resort_all_lists(storage_dir: Path, sort: SortBy) -> None:
    """Resort and reindex every list on disk by ``sort``.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    sort : SortBy
        The attribute to sort by.
    """

    for name in list_all_lists(storage_dir):
        try:
            task_list = load_list(storage_dir, name)
        except TaskliError:
            continue

        task_list.resort(sort)
        save_list(storage_dir, task_list)

    return None
