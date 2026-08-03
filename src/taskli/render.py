"""CLI Taskli rendering function."""

from rich.console import Console, Group
from rich.table import Table
from rich.tree import Tree

from .models import Color, Config, TaskliItem, TaskliList
from .storage import ancestor_chain

__all__ = [
    "render_items",
    "render_list_tree",
    "render_list_names",
    "render_config",
    "render_error",
]

_console = Console()
_err_console = Console(stderr=True)


def _add_bold(name: str, color: str | Color | None) -> str:
    """Wrap a name in bold markup, adding a list color if set."""

    if color is None:
        return f"[bold]{name}[/bold]"

    return f"[bold {str(color)}]{name}[/bold {str(color)}]"


def _add_color(name: str, color: str | Color | None) -> str:
    """Wrap a name in color markup if a color is set, else leave it plain."""

    if color is None:
        return name

    return f"[{str(color)}]{name}[/{str(color)}]"


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
        text = f"[dim]{item.text}[/dim]" if item.done else item.text
        table.add_row(
            str(item.id),
            "x" if item.done else " ",
            text,
            _add_color(item.priority.label, item.priority.color),
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


def render_list_tree(
    lists: list[TaskliList],
    delimiter: str = ".",
) -> None:
    """Print item tables nested in a parent-indented tree.

    Parameters
    ----------
    lists : list[TaskliList]
        Ordered TaskliList objects, where subsequent items are decendent lists.
    delimiter : str, optional
        Display delimiter for the root section's name, by default ".".
    """

    if not lists:
        return None

    root = lists[0]
    root_node = Tree(
        Group(
            _add_bold(root.display_name(delimiter), root.color),
            _items_table(root.items, root.color),
        )
    )
    nodes: dict[str, Tree] = {root.name: root_node}

    for sublist in lists[1:]:
        parent_name = sublist.name.rsplit(".", 1)[0]
        parent = nodes.get(parent_name, root_node)
        label = sublist.name.rsplit(".", 1)[-1]
        node = parent.add(
            Group(
                _add_bold(label, sublist.color),
                _items_table(sublist.items, sublist.color),
            )
        )
        nodes[sublist.name] = node

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


def render_config(config: Config) -> None:
    """Print a table of all config keys and their current values.

    Parameters
    ----------
    config : Config
        The config to display.
    """

    table = Table()
    table.add_column("Key")
    table.add_column("Value")

    keys = config.model_dump().keys()
    for key in keys:
        table.add_row(key, str(config.get_value(key)))

    _console.print(table)

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
