from rich.console import Console
from rich.table import Table

from .models import Priority, TodoItem
from .storage import child_list_names, parent_list_name

__all__ = [
    "render_items",
    "render_grouped_items",
    "render_list_names",
    "render_error",
]

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


def render_grouped_items(sections: list[tuple[str, list[TodoItem]]]) -> None:
    """Print one table per (list_name, items) section, in order.

    Parameters
    ----------
    sections : list[tuple[str, list[TodoItem]]]
        Ordered (list_name, items) pairs — the first entry is the
        primary list, subsequent entries are child-list sections.
    """

    for name, items in sections:
        render_items(name, items)

    return None


def render_list_names(names: list[str]) -> None:
    """Print list names as a parent-indented tree.

    Parameters
    ----------
    names : list[str]
        All existing list names (flat), in any order.
    """

    if not names:
        _console.print("[dim]no lists yet.[/dim]")

        return None

    # find the roots of all names (if multiple decendents) to properly indent.
    name_set = set(names)
    roots = sorted(
        n
        for n in names
        if parent_list_name(n) is None or parent_list_name(n) not in name_set
    )

    def _print_subtree(name: str, depth: int) -> None:
        label = name.rsplit(".", 1)[-1] if depth > 0 else name

        # indentation linear to the depth.
        _console.print(f"{'  ' * depth}{label}")
        for child in child_list_names(name, names):  # RECURSION BITTTTCHHH.
            _print_subtree(child, depth + 1)

    # create a tree for each root of a list.
    for root in roots:
        _print_subtree(root, 0)

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
