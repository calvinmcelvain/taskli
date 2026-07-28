"""todo-cli exceptions."""

__all__ = [
    "TodoError",
    "ListNotFoundError",
    "ListAlreadyExistsError",
    "CorruptedListFileError",
    "InvalidListNameError",
    "ItemNotFoundError",
    "ReservedNameError",
    "TooManyAncestorListsError",
]


class TodoError(Exception):
    """Base for todo-cli errors."""


class ListNotFoundError(TodoError):
    """Raised when a requested list file does not exist."""


class ListAlreadyExistsError(TodoError):
    """Raised when creating a list whose name is already in use."""


class CorruptedListFileError(TodoError):
    """Raised when a list file exists but cannot be parsed."""


class InvalidListNameError(TodoError):
    """Raised when a list name can't safely map to a file."""


class ItemNotFoundError(TodoError):
    """Raised when a todo item id does not exist in a list."""


class ReservedNameError(TodoError):
    """Raised when a list name collides with a reserved command word."""


class TooManyAncestorListsError(TodoError):
    """Raised when a list name is nested more than 2 levels deep."""
