from rich.console import Console, Group
from rich.table import Table
from rich.tree import Tree

from .models import Priority, TodoItem
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


def _items_table(items: list[TodoItem]) -> Table:
    """Build a table of todo items.

    Parameters
    ----------
    items : list[TodoItem]
        The items to display.

    Returns
    -------
    Table
        The rendered table.
    """

    table = Table()
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

    return table


def render_items(list_name: str, items: list[TodoItem]) -> None:
    """Print a table of todo items for a list.

    Parameters
    ----------
    list_name : str
        The list's name, shown in the table title.
    items : list[TodoItem]
        The items to display.
    """

    table = _items_table(items)
    table.title = f"[bold]{list_name}[/bold]"
    _console.print(table)

    return None


def render_grouped_items(sections: list[tuple[str, list[TodoItem]]]) -> None:
    """Print item tables nested in a parent-indented tree.

    Parameters
    ----------
    sections : list[tuple[str, list[TodoItem]]]
        Ordered (list_name, items) pairs — the first entry is the
        primary list, subsequent entries are descendant-list sections,
        each preceded by every one of its own ancestors.
    """

    if not sections:
        return None

    root_name, root_items = sections[0]
    root_node = Tree(
        Group(f"[bold]{root_name}[/bold]", _items_table(root_items))
    )
    nodes: dict[str, Tree] = {root_name: root_node}

    for name, items in sections[1:]:
        parent_name = name.rsplit(".", 1)[0]
        parent = nodes.get(parent_name, root_node)
        label = name.rsplit(".", 1)[-1]
        node = parent.add(Group(f"[bold]{label}[/bold]", _items_table(items)))
        nodes[name] = node

    _console.print(root_node)

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

    # create a tree for each root of a list.
    roots: dict[str, Tree] = {}
    nodes: dict[str, Tree] = {}

    for name in sorted(set(names)):
        parent = None
        chain = [*ancestor_chain(name), name]
        for i in chain:
            if i in nodes:
                parent = nodes[i]
                continue

            if parent is None:
                node = Tree(i)
                roots[i] = node
            else:
                label = i.rsplit(".", 1)[-1]
                node = parent.add(label)

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
