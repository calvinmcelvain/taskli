"""List, tag, task, & priority models."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from ..exceptions import InvalidConfigValueError, UnknownConfigKeyError
from .attributes import Color, Priority

__all__ = ["Config", "SortBy", "Delimters"]


type SortBy = Literal["tags", "priority", "created_at"]
type Delimters = Literal[".", "/", "-", "|"]


class Config(BaseModel):
    """Taskli config."""

    model_config = ConfigDict(validate_assignment=True)

    auto_prune: bool = False
    sublist_delimiter: Delimters = "."
    default_list: str = Field(default="inbox", min_length=1)
    default_sort: SortBy = "created_at"
    default_priority: Priority = Priority.MEDIUM
    default_color: Color | None = Color.WHITE

    @field_validator("default_color", mode="before")
    @classmethod
    def _resolve_color_name(cls, value: object) -> object:
        if isinstance(value, str) and value.upper() in Color.__members__:
            return Color[value.upper()]

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
