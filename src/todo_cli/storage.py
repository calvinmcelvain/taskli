"""List storage functions."""

import os
from pathlib import Path

from pydantic import ValidationError

from .exceptions import (
    CorruptedListFileError,
    InvalidListNameError,
    ListAlreadyExistsError,
    ListNotFoundError,
    ReservedNameError,
)
from .models import TodoList


def resolve_storage_dir() -> Path:
    """Return the directory todo lists are stored in, creating it.

    Returns
    -------
    Path
        The storage directory, guaranteed to exist.
    """

    path = Path(os.environ.get("TODOS_PATH", Path.home() / ".todos"))
    storage_dir = path.expanduser()

    storage_dir.mkdir(parents=True, exist_ok=True)

    return storage_dir


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
    """

    _reserved = {".", "..", "con", "prn", "aux", "nul"}
    lowered = name.lower()
    if lowered in _reserved or "/" in lowered or "\\" in lowered:
        raise InvalidListNameError(f"'{name}' is not a valid list name.")

    return storage_dir / f"{name}.json"


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

    return sorted(path.stem for path in storage_dir.glob("*.json"))


def create_list(
    storage_dir: Path,
    name: str,
    *,
    reserved_names: frozenset[str] = frozenset(),
) -> TodoList:
    """Create and persist a new, empty list.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The new list's name.
    reserved_names : frozenset[str], optional
        Names that may not be used for a list, by default none.

    Returns
    -------
    TodoList
        The newly created, empty list.
    """

    if name in reserved_names:
        raise ReservedNameError(f"'{name}' is a reserved name.")

    if list_exists(storage_dir, name):
        raise ListAlreadyExistsError(f"list '{name}' already exists.")

    todo_list = TodoList(name=name)
    save_list(storage_dir, todo_list)

    return todo_list


def delete_list(storage_dir: Path, name: str) -> None:
    """Delete a list's file.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.
    """

    path = list_file_path(storage_dir, name)
    if not path.exists():
        raise ListNotFoundError(f"list '{name}' does not exist.")

    path.unlink()

    return None


def load_list(storage_dir: Path, name: str) -> TodoList:
    """Load a list from disk, parsing its JSON file.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.

    Returns
    -------
    TodoList
        The loaded list.
    """

    path = list_file_path(storage_dir, name)
    if not path.exists():
        if name == "inbox":
            todo_list = TodoList(name=name)
            save_list(storage_dir, todo_list)

            return todo_list

        raise ListNotFoundError(
            f"list '{name}' does not exist. Run 'todo lists' to see "
            "available lists."
        )

    try:
        return TodoList.model_validate_json(path.read_text())
    except ValidationError as e:
        raise CorruptedListFileError(
            f"list file '{path}' is corrupted and could not be read."
        ) from e


def load_or_create_list(storage_dir: Path, name: str) -> TodoList:
    """Load a list, creating it empty if it doesn't exist yet.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    name : str
        The list name.

    Returns
    -------
    TodoList
        The loaded or newly created list.
    """

    if list_exists(storage_dir, name):
        return load_list(storage_dir, name)

    todo_list = TodoList(name=name)
    save_list(storage_dir, todo_list)

    return todo_list


def save_list(storage_dir: Path, todo_list: TodoList) -> None:
    """Persist a list to its JSON file.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.
    todo_list : TodoList
        The list to save.
    """

    path = list_file_path(storage_dir, todo_list.name)
    path.write_text(todo_list.model_dump_json(indent=2))

    return None
