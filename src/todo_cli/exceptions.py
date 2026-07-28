"""todo-cli exceptions."""

__all__ = [
    "ListNotFoundError",
    "ListAlreadyExistsError",
    "CorruptedListFileError",
    "InvalidListNameError",
    "ItemNotFoundError",
    "ReservedNameError",
    "TooManyAncestorListsError",
]


class ListNotFoundError(Exception):
    """Raised when a requested list file does not exist."""


class ListAlreadyExistsError(Exception):
    """Raised when creating a list whose name is already in use."""


class CorruptedListFileError(Exception):
    """Raised when a list file exists but cannot be parsed."""


class InvalidListNameError(Exception):
    """Raised when a list name can't safely map to a file."""


class ItemNotFoundError(Exception):
    """Raised when a todo item id does not exist in a list."""


class ReservedNameError(Exception):
    """Raised when a list name collides with a reserved command word."""


class TooManyAncestorListsError(Exception):
    """Raised when a list name is nested more than 2 levels deep."""
