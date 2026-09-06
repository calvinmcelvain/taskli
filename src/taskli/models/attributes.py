"""Task & task list attributes."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import assert_never

__all__ = ["Color", "Operator", "Priority", "Status"]


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


class Status(StatusContainer, Enum):
    TODO = ("todo", " ")
    IN_PROGRESS = ("in_progress", "•")
    DONE = ("done", "x")

    @classmethod
    def _missing_(cls, value: object) -> "Status | None":
        if isinstance(value, str) and value.upper() in cls.__members__:
            return cls[value.upper()]

        return None


class Operator(Enum):
    EQ = "eq"
    CONTAINS = "contains"

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

        assert_never(self)


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
