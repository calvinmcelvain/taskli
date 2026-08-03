"""Taskli exceptions."""

__all__ = [
    "TaskliError",
    "ListNotFoundError",
    "ListAlreadyExistsError",
    "CorruptedListFileError",
    "InvalidListNameError",
    "ItemNotFoundError",
    "ReservedNameError",
    "TooManyAncestorListsError",
    "UnknownConfigKeyError",
    "InvalidConfigValueError",
    "CorruptedConfigFileError",
]


class TaskliError(Exception):
    """Base for taskli errors."""


class ListNotFoundError(TaskliError):
    """Raised when a requested list file does not exist."""


class ListAlreadyExistsError(TaskliError):
    """Raised when creating a list whose name is already in use."""


class CorruptedListFileError(TaskliError):
    """Raised when a list file exists but cannot be parsed."""


class InvalidListNameError(TaskliError):
    """Raised when a list name can't safely map to a file."""


class ItemNotFoundError(TaskliError):
    """Raised when a task item id does not exist in a list."""


class ReservedNameError(TaskliError):
    """Raised when a list name collides with a reserved command word."""


class TooManyAncestorListsError(TaskliError):
    """Raised when a list name is nested more than 2 levels deep."""


class UnknownConfigKeyError(TaskliError):
    """Raised when a config key does not exist."""


class InvalidConfigValueError(TaskliError):
    """Raised when a config value fails validation."""


class CorruptedConfigFileError(TaskliError):
    """Raised when the config file exists but cannot be parsed."""
