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
    "render_warning",
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
    table.add_column(_add_color("State", color), justify="center")
    table.add_column(_add_color("Text", color), justify="left")
    table.add_column(_add_color("Priority", color), justify="left")
    table.add_column(_add_color("Tags", color), justify="left")

    for item in items:
        text = f"[dim]{item.text}[/dim]" if item.done else item.text
        table.add_row(
            str(item.id),
            item.status.marker,
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

    table = Group(_add_bold(list_name, color), _items_table(items, color))
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
        Ordered TaskliList objects, where subsequent items are descendant
        lists.
    delimiter : str, optional
        Display delimiter for the root section's name, by default ".".
    """

    if not lists:
        return None

    head = lists[0]
    head_node = Tree(
        Group(
            _add_bold(head.display_name(delimiter), head.color),
            _items_table(head.items, head.color),
        )
    )
    nodes: dict[str, Tree] = {head.name: head_node}

    for sublist in lists[1:]:
        parent_name = sublist.name.rsplit(".", 1)[0]
        parent = nodes.get(parent_name, head_node)
        label = sublist.name.rsplit(".", 1)[-1]
        node = parent.add(
            Group(
                _add_bold(label, sublist.color),
                _items_table(sublist.items, sublist.color),
            )
        )
        nodes[sublist.name] = node

    _console.print(head_node)

    return None


def render_list_names(
    entries: list[tuple[str, Color | None]],
    default_name: str | None = None,
) -> None:
    """Print list names as a parent-indented tree.

    Parameters
    ----------
    entries : list[tuple[str, Color | None]]
        (list_name, color) pairs for all existing lists (flat), in
        any order.
    default_name : str | None, optional
        Dot-normalized name of the configured default list, bolded in
        the tree if present, by default none.
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

            style = _add_bold if i == default_name else _add_color

            if parent is None:
                node = Tree(style(i, colors.get(i)))
                roots[i] = node
            else:
                label = i.rsplit(".", 1)[-1]
                node = parent.add(style(label, colors.get(i)))

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


def render_warning(message: str) -> None:
    """Print a non-fatal warning message in yellow.

    Parameters
    ----------
    message : str
        The warning text.
    """

    _console.print(f"[bold yellow]warning:[/bold yellow] {message}")

    return None
