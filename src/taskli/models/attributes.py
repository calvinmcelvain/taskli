"""Task & task list attributes."""

from dataclasses import dataclass
from enum import Enum, StrEnum

__all__ = ["Color", "Priority", "Status"]


@dataclass(frozen=True)
class PriorityContainer:
    label: str
    index: int
    color: str


class Priority(PriorityContainer, Enum):
    LOW = ("low", 1, "green")
    MEDIUM = ("medium", 2, "yellow")
    HIGH = ("high", 3, "red")


@dataclass(frozen=True)
class StatusContainer:
    label: str
    marker: str


class Status(StatusContainer, Enum):
    TODO = ("todo", " ")
    IN_PROGRESS = ("in_progress", "•")
    DONE = ("done", "x")


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
