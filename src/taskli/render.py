"""CLI Taskli rendering function."""

from rich.console import Console, Group
from rich.table import Table
from rich.tree import Tree

from .models import Color, Priority, TaskliItem
from .storage import ancestor_chain

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


def _add_bold(name: str, color: Color | str | None) -> str:
    """Wrap a name in bold markup, adding a list color if set."""

    if color is None:
        return f"[bold]{name}[/bold]"

    if isinstance(color, str):
        return f"[bold {color}]{name}[/bold {color}]"

    return f"[bold {color.value}]{name}[/bold {color.value}]"


def _add_color(name: str, color: Color | str | None) -> str:
    """Wrap a name in color markup if a color is set, else leave it plain."""

    if color is None:
        return name

    if isinstance(color, str):
        return f"[{color}]{name}[/{color}]"

    return f"[{color.value}]{name}[/{color.value}]"


def _items_table(items: list[TaskliItem], color: Color | None = None) -> Table:
    """Build a table of tasks.

    Parameters
    ----------
    items : list[TaskliItem]
        The items to display.

    Returns
    -------
    Table
        The rendered table.
    """

    table = Table()
    table.add_column(_add_color("ID", color), justify="right")
    table.add_column(_add_color("Done", color))
    table.add_column(_add_color("Text", color))
    table.add_column(_add_color("Priority", color))
    table.add_column(_add_color("Tags", color))

    for item in items:
        priority_color = PRIORITY_COLORS[item.priority]
        text = f"[dim]{item.text}[/dim]" if item.done else item.text
        table.add_row(
            str(item.id),
            "x" if item.done else " ",
            text,
            _add_color(item.priority.value, priority_color),
            ", ".join(item.tags),
        )

    return table


def render_items(
    list_name: str, items: list[TaskliItem], color: Color | None = None
) -> None:
    """Print a table of tasks for a list.

    Parameters
    ----------
    list_name : str
        The list's name, shown in the table title.
    items : list[TaskliItem]
        The items to display.
    color : Color | None, optional
        The list's display color, by default none.
    """

    table = _items_table(items, color)
    table.title = _add_bold(list_name, color)
    _console.print(table)

    return None


def render_grouped_items(
    sections: list[tuple[str, Color | None, list[TaskliItem]]],
) -> None:
    """Print item tables nested in a parent-indented tree.

    Parameters
    ----------
    sections : list[tuple[str, Color | None, list[TaskliItem]]]
        Ordered (list_name, color, items) triples — the first entry is
        the primary list, subsequent entries are descendant-list
        sections, each preceded by every one of its own ancestors.
    """

    if not sections:
        return None

    root_name, root_color, root_items = sections[0]
    root_node = Tree(
        Group(
            _add_bold(root_name, root_color),
            _items_table(root_items, root_color),
        )
    )
    nodes: dict[str, Tree] = {root_name: root_node}

    for name, color, items in sections[1:]:
        parent_name = name.rsplit(".", 1)[0]
        parent = nodes.get(parent_name, root_node)
        label = name.rsplit(".", 1)[-1]
        node = parent.add(
            Group(_add_bold(label, color), _items_table(items, color))
        )
        nodes[name] = node

    _console.print(root_node)

    return None


def render_list_names(entries: list[tuple[str, Color | None]]) -> None:
    """Print list names as a parent-indented tree.

    Parameters
    ----------
    entries : list[tuple[str, Color | None]]
        (list_name, color) pairs for all existing lists (flat), in
        any order.
    """

    if not entries:
        _console.print("[dim]no lists yet.[/dim]")

        return None

    colors = dict(entries)

    # create a tree for each root of a list.
    roots: dict[str, Tree] = {}
    nodes: dict[str, Tree] = {}

    for name in sorted(colors):
        parent = None
        chain = [*ancestor_chain(name), name]
        for i in chain:
            if i in nodes:
                parent = nodes[i]
                continue

            if parent is None:
                node = Tree(_add_color(i, colors.get(i)))
                roots[i] = node
            else:
                label = i.rsplit(".", 1)[-1]
                node = parent.add(_add_color(label, colors.get(i)))

            nodes[i] = node
            parent = node

    _console.print(*list(roots.values()))

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
