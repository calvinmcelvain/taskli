"""Storage-directory resolution and a dependency-free list-name scan."""

import os
from pathlib import Path

CONFIG_FILE_NAME = ".taskli.json"


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


def scan_list_names(storage_dir: Path) -> list[str]:
    """Return the stems of all list files in the storage directory.

    Parameters
    ----------
    storage_dir : Path
        The storage directory.

    Returns
    -------
    list[str]
        Sorted list names, excluding the config file.
    """

    return sorted(
        p.stem
        for p in storage_dir.glob("*.json")
        if p.name != CONFIG_FILE_NAME
    )
