from rich.console import Console
from rich.table import Table

from .models import Priority, TodoItem

__all__ = ["render_items", "render_list_names", "render_error"]

_console = Console()
_err_console = Console(stderr=True)

PRIORITY_COLORS = {
    Priority.LOW: "green",
    Priority.MEDIUM: "yellow",
    Priority.HIGH: "red",
}


def render_items(list_name: str, items: list[TodoItem]) -> None:
    """Print a table of todo items for a list.

    Parameters
    ----------
    list_name : str
        The list's name, shown in the table title.
    items : list[TodoItem]
        The items to display.
    """

    table = Table(title=f"[bold]{list_name}[/bold]")
    table.add_column("ID", justify="right")
    table.add_column("Done")
    table.add_column("Text")
    table.add_column("Priority")
    table.add_column("Tags")

    for item in items:
        color = PRIORITY_COLORS[item.priority]
        text = f"[dim]{item.text}[/dim]" if item.done else item.text
        table.add_row(
            str(item.id),
            "x" if item.done else " ",
            text,
            f"[{color}]{item.priority.value}[/{color}]",
            ", ".join(item.tags),
        )

    _console.print(table)

    return None


def render_list_names(names: list[str]) -> None:
    """Print the names of all existing lists.

    Parameters
    ----------
    names : list[str]
        The list names to display.
    """

    if not names:
        _console.print("[dim]no lists yet.[/dim]")

        return None

    for name in names:
        _console.print(name)

    return None


def render_error(message: str) -> None:
    """Print an error message in red.

    Parameters
    ----------
    message : str
        The error text.
    """

    _err_console.print(f"[bold red]error:[/bold red] {message}")

    return None
