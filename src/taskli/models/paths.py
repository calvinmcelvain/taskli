"""Dotted item-path helpers."""

__all__ = ["path_key"]


def path_key(path: str) -> tuple[int, ...]:
    """Return the positional sort key for a dotted item path.

    Parameters
    ----------
    path : str
        A dotted positional path such as ``"1"`` or ``"1.10"``.

    Returns
    -------
    tuple of int
        One integer per path segment, so ``"1.10"`` yields ``(1, 10)``
        and orders after ``"1.2"`` -> ``(1, 2)``.
    """

    return tuple(int(segment) for segment in path.split("."))
