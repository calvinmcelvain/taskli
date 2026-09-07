"""CLI Taskli rendering function."""

from rich.console import Console, Group
from rich.table import Table
from rich.tree import Tree

from .hierarchy import ancestor_chain
from .models import Color, Config, TaskliItem, TaskliList, registry, walk_items

__all__ = [
    "render_items",
    "render_list_tree",
    "render_list_names",
    "render_agenda",
    "render_config",
    "render_message",
    "render_value",
    "render_error",
    "render_warning",
    "render_reminder",
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
        The top-level items; children render as their own nested rows.

    Returns
    -------
    Table
        The rendered table.
    """

    columns = registry.renderable()

    table = Table()
    for column in columns:
        table.add_column(
            _add_color(column.header, color), justify=column.justify
        )

    for item in walk_items(items):
        cells: list[str] = []
        for column in columns:
            cell = column.format(item)
            if column.style is not None:
                style = column.style(item)
                if style:
                    cell = _add_color(cell, style)
            cells.append(cell)
        table.add_row(*cells)

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
        The top-level items; children render as their own nested rows.
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


def render_agenda(
    rows: list[tuple[str, TaskliItem]], delimiter: str = "."
) -> None:
    """Print a chronological, cross-list table of due items.

    Parameters
    ----------
    rows : list[tuple[str, TaskliItem]]
        (list_name, item) pairs, in the order they should render.
    delimiter : str, optional
        Display delimiter for each row's list name, by default ".".
    """

    if not rows:
        _console.print("[dim]nothing on the agenda.[/dim]")

        return None

    table = Table()
    table.add_column("List")
    table.add_column("ID", justify="right")
    table.add_column("Text")
    table.add_column("Due")

    due_format = registry.ATTRIBUTES["due_date"].render_format
    due_style = registry.ATTRIBUTES["due_date"].render_style
    assert due_format is not None

    display_names: dict[str, str] = {}
    for name, item in rows:
        if name not in display_names:
            display_names[name] = TaskliList(name=name).display_name(delimiter)

        due = due_format(item)
        if due_style is not None:
            style = due_style(item)
            if style:
                due = _add_color(due, style)
        table.add_row(display_names[name], item.id, item.text, due)

    _console.print(table)

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


def render_message(message: str) -> None:
    """Print a plain status message.

    Parameters
    ----------
    message : str
        The message text.
    """

    _console.print(message)

    return None


def render_value(value: str) -> None:
    """Print a raw value verbatim, without markup or line wrapping.

    Parameters
    ----------
    value : str
        The value to print (e.g. a storage path or a config value).
    """

    _console.print(value, markup=False, highlight=False, soft_wrap=True)

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


def render_reminder(overdue: int, due_today: int) -> None:
    """Print a due/overdue reminder banner to stderr.

    Parameters
    ----------
    overdue : int
        The number of overdue, not-done items.
    due_today : int
        The number of items due today.
    """

    parts: list[str] = []
    if overdue:
        parts.append(f"{overdue} overdue")
    if due_today:
        parts.append(f"{due_today} due today")
    message = ", ".join(parts)

    _err_console.print(f"[bold yellow]⚠[/bold yellow]  {message}")

    return None
