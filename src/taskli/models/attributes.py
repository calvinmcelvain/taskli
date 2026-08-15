"""Task & task list attributes."""

from enum import Enum, StrEnum

__all__ = ["Color", "Priority", "Status"]


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __init__(self, label: str):
        self.label = label

    @property
    def index(self) -> int:
        _index = {"low": 1, "medium": 2, "high": 3}
        return _index[self.label]

    @property
    def color(self) -> str:
        _colors = {"low": "green", "medium": "yellow", "high": "red"}
        return _colors[self.label]

    def __str__(self) -> str:
        return self.label


class Status(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


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
