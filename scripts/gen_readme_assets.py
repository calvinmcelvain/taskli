"""Regenerate the README's SVG screenshots by running the real CLI."""

import io
import os
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from datetime import date, datetime, tzinfo
from pathlib import Path
from unittest.mock import patch

from rich.cells import cell_len
from rich.console import Console
from rich.text import Text

from taskli import render
from taskli.cli import main

ASSETS_DIR = Path(__file__).resolve().parent.parent / "docs" / "assets"

# a wednesday, so "friday" and "monday" resolve to stable dates.
FROZEN_NOW = datetime(2026, 3, 11, 9, 30)

DEMO_SETUP = [
    ["--config", "show_reminders", "false"],
    ["work", "--new", "--color", "blue"],
    ["groceries", "--new", "--color", "green"],
    ["groceries", "-a", "Oat milk", "-a", "Sourdough", "-a", "Coffee beans"],
    ["inbox", "-a", "Call the dentist", "-p", "high", "--due", "tomorrow"],
    ["inbox", "-a", "Pick up dry cleaning", "--due", "today"],
    [
        "work",
        "-a",
        "Ship v2 release",
        "-p",
        "high",
        "--tag",
        "release",
        "--due",
        "03-09-2026",
        "--desc",
        "Cut the branch, tag the build, then announce in #general.",
    ],
    ["work", "-a", "Write changelog", "--under", "1"],
    ["work", "-a", "Cut release branch", "--under", "1"],
    ["work", "-a", "Tag the build", "--under", "1", "--due", "today"],
    ["work", "-a", "Submit timesheet", "-p", "low", "--due", "friday"],
    ["work", "-a", "Draft Q2 plan", "--tag", "planning", "--due", "2 weeks"],
    ["work", "-d", "1.1"],
    ["work", "-i", "1.2"],
    ["work.meetings", "-a", "Review roadmap", "--due", "tomorrow"],
    [
        "work.meetings",
        "-a",
        "Sync with design",
        "-p",
        "high",
        "--tag",
        "urgent",
    ],
]


class FrozenDatetime(datetime):
    """A ``datetime`` whose ``now`` always returns ``FROZEN_NOW``."""

    @classmethod
    def now(cls, tz: tzinfo | None = None) -> "FrozenDatetime":
        return cls.fromtimestamp(FROZEN_NOW.timestamp(), tz)


def frozen_today() -> date:
    """Return the frozen calendar day."""

    return FROZEN_NOW.date()


def make_console(width: int) -> Console:
    """Build a recording, truecolor console that prints nowhere."""

    return Console(
        file=io.StringIO(),
        record=True,
        force_terminal=True,
        color_system="truecolor",
        width=width,
    )


def command_line(argv: list[str]) -> str:
    """Render an argv as the ``tk ...`` line a user would type."""

    parts = [f'"{arg}"' if " " in arg or not arg else arg for arg in argv]

    return " ".join(["tk", *parts])


def run(argv: list[str], console: Console) -> None:
    """Run the CLI in-process with all output routed to ``console``."""

    with ExitStack() as stack:
        stack.enter_context(patch.object(render, "_console", console))
        stack.enter_context(patch.object(render, "_err_console", console))
        main(argv)

    return None


@contextmanager
def storage(setup: list[list[str]]) -> Iterator[None]:
    """Provide a fresh storage dir and frozen clock, seeded by ``setup``."""

    with ExitStack() as stack:
        tmp = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(patch.dict(os.environ, {"TASKLI_PATH": tmp}))
        stack.enter_context(
            patch("taskli.models.tasks.datetime", FrozenDatetime)
        )
        for module in (
            "taskli.models.dates",
            "taskli.models.query",
            "taskli.models.registry",
            "taskli.render",
        ):
            stack.enter_context(patch(f"{module}.today", frozen_today))
        for argv in setup:
            run(argv, make_console(120))
        yield


def shot(name: str, commands: list[list[str]], width: int = 120) -> None:
    """Run ``commands`` and save the recorded output as ``name``.svg."""

    console = make_console(width)
    echo = len(commands) > 1
    for index, argv in enumerate(commands):
        if echo:
            if index:
                console.print()
            prompt = Text.assemble(
                ("$ ", "bold green"), (command_line(argv), "bold")
            )
            console.print(prompt)
        run(argv, console)

    title = "taskli" if echo else command_line(commands[0])
    lines = console.export_text(clear=False).splitlines()
    content = max(cell_len(line.rstrip()) for line in lines) + 1
    # the title bar needs room beside the three window buttons.
    console.width = max(content, cell_len(title) + 16)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    console.save_svg(
        str(ASSETS_DIR / f"{name}.svg"), title=title, unique_id=name
    )

    return None


def generate() -> None:
    """Write every README screenshot to ``docs/assets``."""

    with storage([]):
        shot(
            "quickstart",
            [
                ["-a", "Buy oat milk"],
                ["work", "-a", "Ship v2", "-p", "high", "--due", "friday"],
                ["work.meetings", "-a", "Review roadmap"],
                ["work", "--all"],
            ],
        )

    states_setup = [
        ["work", "-a", "Draft spec", "-a", "Review PR", "-a", "Fix typo"]
    ]
    with storage(states_setup):
        shot("states", [["work", "-i", "2"], ["work", "-d", "3"]])

    with storage(DEMO_SETUP):
        shot("hero", [["work", "--all"]])
        shot("agenda", [["--agenda"]])
        shot("filter", [["work", "--all", "-p", "high"]])
        shot("details", [["work", "-D", "1"]], width=72)
        shot("lists", [["--lists"]])

    return None


if __name__ == "__main__":
    generate()
