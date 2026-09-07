"""CLI Taskli rendering function."""

from collections.abc import Iterator
from datetime import datetime

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .hierarchy import ancestor_chain
from .models import Color, Config, TaskliItem, TaskliList, registry, today

__all__ = [
    "render_items",
    "render_list_tree",
    "render_list_names",
    "render_agenda",
    "render_item_details",
    "render_config",
    "render_message",
    "render_value",
    "render_error",
    "render_warning",
    "render_reminder",
]

_console = Console()
_err_console = Console(stderr=True)


def _span(text: str, style: str = "") -> Text:
    """Build a Text whose style is span-scoped, not painting cell padding."""

    result = Text()
    result.append(text, style=style)

    return result


def _label(
    name: str, color: str | Color | None, *, bold: bool = False
) -> Text:
    """Build a Text label, bold and/or list-colored per the flags."""

    parts: list[str] = []
    if bold:
        parts.append("bold")
    if color is not None:
        parts.append(str(color))

    return _span(name, " ".join(parts))


def _task_rows(
    items: list[TaskliItem], prefix: str = "", top: bool = True
) -> Iterator[tuple[TaskliItem, str]]:
    """Yield each item with its tree-branch prefix, pre-order DFS."""

    for item in items:
        is_last = item is items[-1]
        if top:
            yield item, ""
            yield from _task_rows(item.children, "", top=False)
            continue

        connector = "└── " if is_last else "├── "
        yield item, prefix + connector
        ext = "    " if is_last else "│   "
        yield from _task_rows(item.children, prefix + ext, top=False)


def _task_cell(item: TaskliItem, prefix: str) -> Text:
    """Build the Task cell: branch prefix, state marker, id, and text."""

    result = Text()
    result.append(prefix, style="dim")
    result.append(f"{item.status.marker} ", style=item.status.marker_style)
    dim = "dim" if item.done else ""
    # trailing dot at every level: "2" -> "2.", "2.1" -> "2.1."
    result.append(f"{item.id}. ", style=dim)
    result.append(item.text, style="dim strike" if item.done else "")

    return result


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
    table.add_column(_label("Task", color), justify="left")
    for column in columns:
        table.add_column(_label(column.header, color), justify=column.justify)

    for item, prefix in _task_rows(items):
        cells: list[str | Text] = [_task_cell(item, prefix)]
        for column in columns:
            cell = column.format(item)
            style = column.style(item) if column.style is not None else None
            cells.append(_span(cell, style) if style else cell)
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

    table = Group(
        _label(list_name, color, bold=True), _items_table(items, color)
    )
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
            _label(head.display_name(delimiter), head.color, bold=True),
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
                _label(label, sublist.color, bold=True),
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
        _console.print(Text("no lists yet.", style="dim"))

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

            node_bold = i == default_name

            if parent is None:
                node = Tree(_label(i, colors.get(i), bold=node_bold))
                roots[i] = node
            else:
                label = i.rsplit(".", 1)[-1]
                node = parent.add(_label(label, colors.get(i), bold=node_bold))

            nodes[i] = node
            parent = node

    _console.print(*list(roots.values()))

    return None


def _due_display(item: TaskliItem) -> tuple[str, str | None]:
    """Return an item's formatted due date and its rich style.

    Parameters
    ----------
    item : TaskliItem
        The item whose due-date cell to build.

    Returns
    -------
    tuple[str, str | None]
        The formatted date string and the style name (``None`` when the
        cell should render plain), both from the ``due_date`` registry
        entry -- shared by ``render_agenda`` and ``render_item_details``.
    """

    attr = registry.ATTRIBUTES["due_date"]
    assert attr.render_format is not None
    style = attr.render_style(item) if attr.render_style is not None else None

    return attr.render_format(item), style


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
        _console.print(Text("nothing on the agenda.", style="dim"))

        return None

    table = Table()
    table.add_column("List")
    table.add_column("ID", justify="right")
    table.add_column("Text")
    table.add_column("Due")

    display_names: dict[str, str] = {}
    for name, item in rows:
        if name not in display_names:
            display_names[name] = TaskliList(name=name).display_name(delimiter)

        formatted, style = _due_display(item)
        due = _span(formatted, style) if style else formatted
        table.add_row(display_names[name], item.id, item.text, due)

    _console.print(table)

    return None


def _relative_due(due: datetime) -> str:
    """Return a human phrase for a due date relative to today."""

    delta = (due.date() - today()).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if delta == -1:
        return "yesterday"
    if delta > 1:
        return f"in {delta} days"

    return f"{-delta} days ago"


def render_item_details(
    task_list: TaskliList, item: TaskliItem, delimiter: str = "."
) -> None:
    """Print a single task's full detail as a bordered panel.

    Parameters
    ----------
    task_list : TaskliList
        The list holding the item, named in the panel title.
    item : TaskliItem
        The item to show.
    delimiter : str, optional
        Display delimiter for the panel title's list name, by default ".".
    """

    header = Text()
    header.append(f"{item.status.marker} ", style=item.status.marker_style)
    header.append(item.text, style="bold strike" if item.done else "bold")

    metadata = Table.grid(padding=(0, 2))
    metadata.add_column()
    metadata.add_column()

    meta_rows: list[tuple[str, str | Text]] = [
        ("status", item.status.label),
        ("priority", _span(item.priority.label, item.priority.color)),
    ]
    if item.tags:
        meta_rows.append(("tags", ", ".join(item.tags)))
    if item.due_date is not None:
        formatted, due_style = _due_display(item)
        due_value = f"{formatted} ({_relative_due(item.due_date)})"
        meta_rows.append(
            ("due", _span(due_value, due_style) if due_style else due_value)
        )
    meta_rows.append(("created", item.created_at.strftime("%Y-%m-%d %H:%M")))
    if item.modified_at is not None:
        meta_rows.append(
            ("modified", item.modified_at.strftime("%Y-%m-%d %H:%M"))
        )

    for label, value in meta_rows:
        metadata.add_row(_span(label, "dim"), value)

    parts: list[RenderableType] = [header, "", metadata]

    if item.description:
        description = Text()
        description.append("description", style="dim")
        for line in item.description.splitlines():
            description.append(f"\n  {line}")
        parts += ["", description]

    if item.children:
        subtasks = Text()
        subtasks.append("subtasks", style="dim")
        subtasks.append("\n")
        for child, prefix in _task_rows(item.children):
            subtasks.append_text(_task_cell(child, prefix))
            subtasks.append("\n")
        parts += ["", subtasks]

    panel = Panel(
        Group(*parts),
        title=f"{task_list.display_name(delimiter)} / {item.id}",
        title_align="left",
        border_style="dim",
        padding=(0, 1),
    )
    _console.print(panel)

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
        table.add_row(_span(key), _span(str(config.get_value(key))))

    _console.print(table)

    return None


def render_message(message: str) -> None:
    """Print a plain status message.

    Parameters
    ----------
    message : str
        The message text.
    """

    _console.print(Text(message))

    return None


def render_value(value: str) -> None:
    """Print a raw value verbatim, without markup or line wrapping.

    Parameters
    ----------
    value : str
        The value to print (e.g. a storage path or a config value).
    """

    _console.print(Text(value), highlight=False, soft_wrap=True)

    return None


def render_error(message: str) -> None:
    """Print an error message in red.

    Parameters
    ----------
    message : str
        The error text.
    """

    _err_console.print(Text.assemble(("error:", "bold red"), f" {message}"))

    return None


def render_warning(message: str) -> None:
    """Print a non-fatal warning message in yellow.

    Parameters
    ----------
    message : str
        The warning text.
    """

    _console.print(Text.assemble(("warning:", "bold yellow"), f" {message}"))

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

    _err_console.print(Text.assemble(("⚠", "bold yellow"), f"  {message}"))

    return None
