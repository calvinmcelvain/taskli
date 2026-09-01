"""List-name hierarchy helpers."""

__all__ = [
    "parent_list_name",
    "child_list_names",
    "descendant_list_names",
    "ancestor_chain",
]


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
