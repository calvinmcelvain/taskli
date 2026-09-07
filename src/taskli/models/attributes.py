"""Task & task list attributes."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import assert_never

__all__ = ["Color", "Operator", "Priority", "Status"]


class Color(StrEnum):
    WHITE = "#F8FAFC"
    RED = "#FF4D6D"
    CORAL = "#FF6B6B"
    ORANGE = "#FF8A3D"
    YELLOW = "#FFD60A"
    LIME = "#A3E635"
    GREEN = "#22C55E"
    TEAL = "#14D8B4"
    CYAN = "#00D9FF"
    SKY = "#38BDF8"
    BLUE = "#3B82F6"
    INDIGO = "#6366F1"
    VIOLET = "#8B5CF6"
    PURPLE = "#A855F7"
    MAGENTA = "#D946EF"
    PINK = "#FF4FCB"

    @classmethod
    def _missing_(cls, value: object) -> "Color | None":
        if isinstance(value, str) and value.upper() in cls.__members__:
            return cls[value.upper()]

        return None


@dataclass(frozen=True)
class PriorityContainer:
    label: str
    index: int
    color: str


class Priority(PriorityContainer, Enum):
    LOW = ("low", 1, "green")
    MEDIUM = ("medium", 2, "yellow")
    HIGH = ("high", 3, "red")

    @classmethod
    def _missing_(cls, value: object) -> "Priority | None":
        if isinstance(value, str) and value.upper() in cls.__members__:
            return cls[value.upper()]

        return None


@dataclass(frozen=True)
class StatusContainer:
    label: str
    marker: str
    color: str


class Status(StatusContainer, Enum):
    TODO = ("todo", "☐", Color.WHITE.value)
    IN_PROGRESS = ("in_progress", "■", Color.CYAN.value)
    DONE = ("done", "■", Color.WHITE.value)

    @property
    def marker_style(self) -> str:
        """Rich style for this status's marker glyph.

        Returns
        -------
        str
            ``"dim"`` for a done item, else the status's marker color.
        """

        return "dim" if self is Status.DONE else self.color

    @classmethod
    def _missing_(cls, value: object) -> "Status | None":
        if isinstance(value, str) and value.upper() in cls.__members__:
            return cls[value.upper()]

        return None


class Operator(Enum):
    EQ = "eq"
    CONTAINS = "contains"
    LT = "lt"
    GTE = "gte"

    def compare(self, value: object, operand: object) -> bool:
        """Test ``value`` against ``operand`` under this operator.

        Parameters
        ----------
        value : object
            The item attribute value to test.
        operand : object
            The value the criterion holds to test against.

        Returns
        -------
        bool
            Whether ``value`` satisfies ``operand`` under this operator.
        """

        if self is Operator.EQ:
            return value == operand

        if self is Operator.CONTAINS:
            # case-insensitive containment: substring for a plain string,
            # exact membership for any other iterable (reproduces the old
            # ``needle in (t.lower() for t in item.tags)`` on tags).
            needle = str(operand).lower()
            if isinstance(value, str):
                return needle in value.lower()
            if isinstance(value, Iterable):
                return needle in (str(v).lower() for v in value)

            return False

        if self is Operator.LT:
            if value is None or operand is None:
                return False

            # object carries no ordering, so operand compatibility rests
            # on the caller pairing the criterion, not on a check here.
            return bool(value < operand)  # type: ignore[operator]

        if self is Operator.GTE:
            if value is None or operand is None:
                return False

            return bool(value >= operand)  # type: ignore[operator]

        assert_never(self)
