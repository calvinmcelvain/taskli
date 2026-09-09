"""Taskli exceptions."""

__all__ = [
    "TaskliError",
    "ListNotFoundError",
    "ListAlreadyExistsError",
    "CorruptedListFileError",
    "OutdatedListFileError",
    "InvalidListNameError",
    "ItemNotFoundError",
    "TooManyAncestorListsError",
    "UnknownConfigKeyError",
    "InvalidConfigValueError",
    "InvalidModifierValueError",
    "InvalidReparentError",
    "CorruptedConfigFileError",
    "OutdatedConfigFileError",
]


class TaskliError(Exception):
    """Base for taskli errors."""


class ListNotFoundError(TaskliError):
    """Raised when a requested list file does not exist."""


class ListAlreadyExistsError(TaskliError):
    """Raised when creating a list whose name is already in use."""


class CorruptedListFileError(TaskliError):
    """Raised when a list file exists but cannot be parsed."""


class OutdatedListFileError(TaskliError):
    """Raised when a list file uses an outdated schema version."""


class InvalidListNameError(TaskliError):
    """Raised when a list name can't safely map to a file."""


class ItemNotFoundError(TaskliError):
    """Raised when a task item id does not exist in a list."""


class TooManyAncestorListsError(TaskliError):
    """Raised when a list name is nested more than 2 levels deep."""


class UnknownConfigKeyError(TaskliError):
    """Raised when a config key does not exist."""


class InvalidConfigValueError(TaskliError):
    """Raised when a config value fails validation."""


class InvalidModifierValueError(TaskliError):
    """Raised when a settable modifier value fails its registry parse."""


class InvalidReparentError(TaskliError):
    """Raised when re-nesting an item under itself or its own descendant."""


class CorruptedConfigFileError(TaskliError):
    """Raised when the config file exists but cannot be parsed."""


class OutdatedConfigFileError(TaskliError):
    """Raised when the config file uses an outdated schema version."""
