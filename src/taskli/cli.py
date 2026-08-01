"""Command-line interface and argument routing."""

import argparse
import functools
import sys
from collections.abc import Callable
from pathlib import Path

from .exceptions import TodoError
from .models import Color, Priority, TaskliItem, TaskliList
from .render import (
    render_error,
    render_grouped_items,
    render_items,
    render_list_names,
)
from .storage import (
    create_list,
    delete_list,
    descendant_list_names,
    list_all_lists,
    load_list,
    load_or_create_list,
    resolve_storage_dir,
    save_list,
)

TOP_LEVEL_COMMANDS: frozenset[str] = frozenset(
    {"lists", "new-list", "rm-list", "edit-list", "all"}
)


def _handle_errors(func: Callable[..., int]) -> Callable[..., int]:
    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> int:
        try:
            return func(*args, **kwargs)
        except TodoError as e:
            render_error(str(e))

            return 1

    return wrapper


def _build_top_level_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("lists", help="Show all list names.")
    subparsers.add_parser("all", help="Show every list's items.")

    new_list_parser = subparsers.add_parser(
        "new-list", help="Create a new, empty list."
    )
    new_list_parser.add_argument("name", help="Name of the list to create.")

    colors_str = ", ".join(c.name.lower() for c in Color) + "."
    new_list_parser.add_argument(
        "-c",
        "--color",
        choices=[c.name.lower() for c in Color],
        default=None,
        help=f"List color. Choices: {colors_str}",
    )

    rm_list_parser = subparsers.add_parser(
        "rm-list", help="Delete a whole list and all its items."
    )
    rm_list_parser.add_argument("name", help="Name of the list to delete.")

    edit_list_parser = subparsers.add_parser(
        "edit-list", help="Change an existing list's color."
    )
    edit_list_parser.add_argument("name", help="Name of the list to edit.")
    edit_list_parser.add_argument(
        "-c",
        "--color",
        choices=[c.name.lower() for c in Color],
        required=True,
        help=f"New list color. Choices: {colors_str}",
    )

    return parser


def _build_list_action_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="todo",
        description=(
            "Manage items in a list. LIST defaults to 'inbox' when " "omitted."
        ),
        epilog=(
            "Top-level commands run as `todo COMMAND ...`:\n"
            "  lists              Show all list names.\n"
            "  all                Show every list's items.\n"
            "  new-list NAME      Create a new, empty list.\n"
            "  rm-list NAME       Delete a whole list and all its "
            "items.\n"
            "  edit-list NAME     Change an existing list's color.\n\n"
            "Run `todo COMMAND --help` for a command's full options.\n\n"
            "Example: todo new-list groceries -c teal"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "list_name",
        nargs="?",
        default="inbox",
        metavar="LIST",
        help="Name of the list to act on (default: inbox).",
    )

    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "-a",
        "--add",
        dest="add",
        nargs="+",
        action="append",
        metavar="TEXT",
        help="Add an item to LIST. Repeatable for multiple items.",
    )
    action.add_argument(
        "-l",
        "--list",
        dest="show",
        action="store_true",
        help="Show items in LIST (default action).",
    )
    action.add_argument(
        "-d",
        "--done",
        dest="done",
        type=int,
        metavar="ID",
        help="Mark an item as done.",
    )
    action.add_argument(
        "-u",
        "--undone",
        dest="undone",
        type=int,
        metavar="ID",
        help="Mark an item as not done.",
    )
    action.add_argument(
        "-r",
        "--rm",
        dest="rm",
        type=int,
        metavar="ID",
        help="Remove an item from LIST.",
    )
    action.add_argument(
        "-e",
        "--edit",
        dest="edit",
        type=int,
        metavar="ID",
        help="Edit an item's text, priority, or tags.",
    )
    action.add_argument(
        "--tags",
        dest="tags_action",
        action="store_true",
        help="Show all distinct tags used in LIST.",
    )
    action.add_argument(
        "--prune",
        dest="prune",
        action="store_true",
        help="Remove all done items from LIST.",
    )

    parser.add_argument(
        "-p",
        "--priority",
        choices=[p.value for p in Priority],
        default=None,
        help="Item priority for -a/-e (default: medium on add).",
    )
    parser.add_argument(
        "-t",
        "--tag",
        dest="tags",
        action="append",
        default=[],
        metavar="TAG",
        help="Tag to set on -a/-e. Repeatable.",
    )
    parser.add_argument(
        "-f",
        "--filter-tag",
        dest="filter_tag",
        default=None,
        metavar="TAG",
        help="Only show items with this tag (default view only).",
    )
    parser.add_argument(
        "--text",
        dest="text",
        default=None,
        help="Replace an item's text (-e only).",
    )

    return parser


def _resolve_action(namespace: argparse.Namespace) -> str:
    if namespace.add is not None:
        return "add"
    if namespace.done is not None:
        return "done"
    if namespace.undone is not None:
        return "undone"
    if namespace.rm is not None:
        return "rm"
    if namespace.edit is not None:
        return "edit"
    if namespace.tags_action:
        return "tags"
    if namespace.prune:
        return "prune"

    return "view"


def _validate_list_action_flags(
    namespace: argparse.Namespace,
    action: str,
    parser: argparse.ArgumentParser,
) -> None:
    add_or_edit = action in {"add", "edit"}
    if namespace.tags and not add_or_edit:
        parser.error("-t/--tag is only valid with -a/--add or -e/--edit.")
    if namespace.priority is not None and not add_or_edit:
        parser.error("-p/--priority is only valid with -a/--add or -e/--edit.")
    if namespace.filter_tag is not None and action != "view":
        parser.error("-f/--filter-tag is only valid with the default view.")
    if namespace.text is not None and action != "edit":
        parser.error("--text is only valid with -e/--edit.")


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ")

    return answer.strip().lower() in {"y", "yes"}


def _print_list(list_name: str, todo_list: TaskliList) -> None:
    render_items(list_name, todo_list.items, todo_list.color)


@_handle_errors
def _lists_cmd() -> int:
    storage_dir = resolve_storage_dir()

    entries: list[tuple[str, Color | None]] = []
    for name in list_all_lists(storage_dir):
        try:
            entries.append((name, load_list(storage_dir, name).color))
        except TodoError:
            entries.append((name, None))

    render_list_names(entries)

    return 0


@_handle_errors
def _new_list_cmd(name: str, color: str | None) -> int:
    storage_dir = resolve_storage_dir()

    todo_list = create_list(
        storage_dir,
        name,
        reserved_names=TOP_LEVEL_COMMANDS,
        color=Color[color.upper()] if color is not None else None,
    )

    print(f"created list '{name}'.")
    _print_list(name, todo_list)

    return 0


@_handle_errors
def _edit_list_cmd(name: str, color: str) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, name)
    todo_list.set_color(Color[color.upper()])

    save_list(storage_dir, todo_list)

    print(f"updated color of '{name}' to '{color}'.")
    _print_list(name, todo_list)

    return 0


@_handle_errors
def _rm_list_cmd(name: str) -> int:
    storage_dir = resolve_storage_dir()
    descendants = descendant_list_names(name, list_all_lists(storage_dir))

    prompt = f"delete list '{name}' and all its items?"
    if descendants:
        prompt = (
            f"delete list '{name}' and its {len(descendants)} "
            f"sublist(s) ({', '.join(descendants)}) and all their items?"
        )

    if not _confirm(prompt):
        print("aborted.")

        return 1

    deleted_descendants = delete_list(storage_dir, name)

    # no list left to print back after deletion.
    if deleted_descendants:
        print(
            f"deleted list '{name}' and {len(deleted_descendants)} "
            "sublist(s)."
        )
    else:
        print(f"deleted list '{name}'.")

    return 0


@_handle_errors
def _add_cmd(
    list_name: str, texts: list[str], tags: list[str], priority: str
) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_or_create_list(
        storage_dir, list_name, reserved_names=TOP_LEVEL_COMMANDS
    )

    for text in texts:
        item = todo_list.add_item(
            text, priority=Priority(priority), tags=list(tags)
        )
        print(f"added #{item.id} to '{list_name}'.")

    save_list(storage_dir, todo_list)
    _print_list(list_name, todo_list)

    return 0


def _grouped_sections(
    storage_dir: Path,
    list_name: str,
    all_names: list[str],
    tag: str | None,
) -> list[tuple[str, Color | None, list[TaskliItem]]]:
    todo_list = load_list(storage_dir, list_name)

    sections = [
        (list_name, todo_list.color, todo_list.filtered_items(tag=tag))
    ]

    # filter each decendent list by tag if given to parent.
    for child_name in descendant_list_names(list_name, all_names):
        child_list = load_list(storage_dir, child_name)
        child_items = child_list.filtered_items(tag=tag)

        if tag is not None and not child_items:
            continue

        sections.append((child_name, child_list.color, child_items))

    return sections


@_handle_errors
def _list_cmd(list_name: str, tag: str | None) -> int:
    storage_dir = resolve_storage_dir()
    all_names = list_all_lists(storage_dir)

    render_grouped_items(
        _grouped_sections(storage_dir, list_name, all_names, tag)
    )

    return 0


@_handle_errors
def _all_cmd() -> int:
    storage_dir = resolve_storage_dir()
    all_names = list_all_lists(storage_dir)

    if not all_names:
        render_list_names([])

        return 0

    roots = [name for name in all_names if "." not in name]
    for root in roots:
        render_grouped_items(
            _grouped_sections(storage_dir, root, all_names, None)
        )

    return 0


@_handle_errors
def _done_cmd(list_name: str, item_id: int) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    todo_list.mark_done(item_id)

    save_list(storage_dir, todo_list)

    print(f"marked #{item_id} done in '{list_name}'.")
    _print_list(list_name, todo_list)

    return 0


@_handle_errors
def _undone_cmd(list_name: str, item_id: int) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    todo_list.mark_undone(item_id)

    save_list(storage_dir, todo_list)

    print(f"marked #{item_id} not done in '{list_name}'.")
    _print_list(list_name, todo_list)

    return 0


@_handle_errors
def _rm_cmd(list_name: str, item_id: int) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    todo_list.remove_item(item_id)

    save_list(storage_dir, todo_list)

    print(f"removed #{item_id} from '{list_name}'.")
    _print_list(list_name, todo_list)

    return 0


@_handle_errors
def _prune_cmd(list_name: str) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    removed = todo_list.remove_done_items()

    save_list(storage_dir, todo_list)

    print(f"pruned {len(removed)} item(s) from '{list_name}'.")
    _print_list(list_name, todo_list)

    return 0


@_handle_errors
def _edit_cmd(
    list_name: str,
    item_id: int,
    text: str | None,
    priority: str | None,
    tags: list[str],
) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    todo_list.edit_item(
        item_id,
        text=text,
        priority=Priority(priority) if priority is not None else None,
        tags=list(tags) if tags else None,
    )

    save_list(storage_dir, todo_list)

    print(f"updated #{item_id} in '{list_name}'.")
    _print_list(list_name, todo_list)

    return 0


@_handle_errors
def _tags_cmd(list_name: str) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)

    tags = sorted({t for item in todo_list.items for t in item.tags})
    for tag in tags:
        print(tag)

    return 0


def _dispatch_top_level(namespace: argparse.Namespace) -> int:
    if namespace.command == "lists":
        return _lists_cmd()
    if namespace.command == "all":
        return _all_cmd()
    if namespace.command == "new-list":
        return _new_list_cmd(namespace.name, namespace.color)
    if namespace.command == "edit-list":
        return _edit_list_cmd(namespace.name, namespace.color)

    return _rm_list_cmd(namespace.name)


def _dispatch_list_action(namespace: argparse.Namespace, action: str) -> int:
    list_name: str = namespace.list_name
    if action == "add":
        texts = [" ".join(words) for words in namespace.add]
        priority = namespace.priority or Priority.MEDIUM.value

        return _add_cmd(list_name, texts, namespace.tags, priority)
    if action == "done":
        return _done_cmd(list_name, namespace.done)
    if action == "undone":
        return _undone_cmd(list_name, namespace.undone)
    if action == "rm":
        return _rm_cmd(list_name, namespace.rm)
    if action == "edit":
        return _edit_cmd(
            list_name,
            namespace.edit,
            namespace.text,
            namespace.priority,
            namespace.tags,
        )
    if action == "tags":
        return _tags_cmd(list_name)
    if action == "prune":
        return _prune_cmd(list_name)

    return _list_cmd(list_name, namespace.filter_tag)


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)

    if raw_argv and raw_argv[0] in TOP_LEVEL_COMMANDS:
        parser = _build_top_level_parser()
        try:
            namespace = parser.parse_args(raw_argv)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1

        return _dispatch_top_level(namespace)

    parser = _build_list_action_parser()
    try:
        namespace = parser.parse_args(raw_argv)
        action = _resolve_action(namespace)
        _validate_list_action_flags(namespace, action, parser)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    return _dispatch_list_action(namespace, action)


if __name__ == "__main__":
    sys.exit(main())
