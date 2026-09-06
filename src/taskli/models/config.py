"""List, tag, task, & priority models."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_serializer,
    field_validator,
)

from ..exceptions import InvalidConfigValueError, UnknownConfigKeyError
from .attributes import Color, Priority
from .registry import sortable

__all__ = ["Config", "SortBy", "Delimters"]


# kept as a name for the models package export and call sites; the set
# of valid values now lives in the attribute registry.
type SortBy = str
type Delimters = Literal[".", "/", "-", "|"]


class Config(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    auto_prune: bool = False
    sublist_delimiter: Delimters = "."
    default_list: str = Field(default="inbox", min_length=1)
    default_sort: SortBy = "created_at"
    default_priority: Priority = Priority.MEDIUM
    default_color: Color | None = Color.WHITE

    @field_serializer("default_priority")
    def _serialize_priority(self, value: Priority) -> str:
        return value.label

    @field_validator("default_sort")
    @classmethod
    def _validate_default_sort(cls, value: str) -> str:
        if value not in sortable():
            raise ValueError(
                f"'{value}' is not a valid value for 'default_sort'."
            )

        return value

    def _has_key(self, key: str) -> None:
        if hasattr(self, key):
            return

        raise UnknownConfigKeyError(f"'{key}' is not a config key.")

    def get_value(self, key: str) -> object:
        """Return the current value of a config key.

        Parameters
        ----------
        key : str
            The config key.

        Returns
        -------
        object
            The key's current value.
        """

        self._has_key(key)
        return getattr(self, key)

    def set_value(self, key: str, raw_value: str) -> None:
        """Parse a CLI string and set a config key.

        Parameters
        ----------
        key : str
            The config key.
        raw_value : str
            The raw CLI value to parse and assign.
        """

        self._has_key(key)
        try:
            setattr(self, key, raw_value)
        except ValidationError as e:
            raise InvalidConfigValueError(
                f"'{raw_value}' is not a valid value for '{key}'."
            ) from e

        return None
