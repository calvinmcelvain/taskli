"""Command-line interface and argument routing."""

import argparse
import functools
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from .exceptions import TaskliError
from .models import Color, Config, Priority, TaskliList
from .render import (
    render_config,
    render_error,
    render_items,
    render_list_names,
    render_list_tree,
)
from .storage import (
    create_list,
    delete_list,
    descendant_list_names,
    list_all_lists,
    load_config,
    load_list,
    load_or_create_list,
    resolve_storage_dir,
    resort_all_lists,
    save_config,
    save_list,
)


class ListOp(StrEnum):
    NEW_LIST = "new_list"
    RM_LIST = "rm_list"
    EDIT_LIST = "edit_list"
    CONFIG = "config"
    LISTS = "lists"


class ItemAction(StrEnum):
    ADD = "add"
    DONE = "done"
    UNDONE = "undone"
    RM = "rm"
    EDIT = "edit"
    TAGS = "tags"
    PRUNE = "prune"


def _handle_errors(func: Callable[..., int]) -> Callable[..., int]:
    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> int:
        try:
            return func(*args, **kwargs)
        except TaskliError as e:
            render_error(str(e))

            return 1

    return wrapper


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task",
        description=(
            "Manage task lists. LIST defaults to 'inbox' when omitted."
        ),
        epilog='Example: task groceries --new-list -c teal -a "buy milk"',
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        metavar="LIST",
        help="Name of the list to act on (default: configured default_list).",
    )

    list_mgmt = parser.add_argument_group("list management")
    ops = list_mgmt.add_mutually_exclusive_group()
    ops.add_argument(
        "--new-list",
        dest="new_list",
        action="store_true",
        help="Create LIST as a new, empty list.",
    )
    ops.add_argument(
        "--rm-list",
        dest="rm_list",
        action="store_true",
        help="Delete LIST and all its items.",
    )
    ops.add_argument(
        "--edit-list",
        dest="edit_list",
        action="store_true",
        help="Change LIST's color (requires -c/--color).",
    )
    ops.add_argument(
        "--config",
        dest="config",
        nargs="*",
        default=None,
        metavar=("KEY", "VALUE"),
        help="View or edit config settings. Omit KEY/VALUE to view all.",
    )
    ops.add_argument(
        "--lists",
        dest="lists",
        action="store_true",
        help="Show every list name, nested as a tree.",
    )

    item_actions = parser.add_argument_group("item actions")
    actions = item_actions.add_mutually_exclusive_group()
    actions.add_argument(
        "-a",
        "--add",
        dest="add",
        nargs="+",
        action="append",
        metavar="TEXT",
        help="Add an item to LIST. Repeatable for multiple items.",
    )
    actions.add_argument(
        "-d",
        "--done",
        dest="done",
        type=int,
        metavar="ID",
        help="Mark an item as done.",
    )
    actions.add_argument(
        "-u",
        "--undone",
        dest="undone",
        type=int,
        metavar="ID",
        help="Mark an item as not done.",
    )
    actions.add_argument(
        "-r",
        "--rm",
        dest="rm",
        type=int,
        metavar="ID",
        help="Remove an item from LIST.",
    )
    actions.add_argument(
        "-e",
        "--edit",
        dest="edit",
        type=int,
        metavar="ID",
        help="Edit an item's text, priority, or tags.",
    )
    actions.add_argument(
        "--tags",
        dest="tags_action",
        action="store_true",
        help="Show all distinct tags used in LIST.",
    )
    actions.add_argument(
        "--prune",
        dest="prune",
        action="store_true",
        help="Remove all done items from LIST.",
    )

    modifiers = parser.add_argument_group("modifiers")
    colors_str = ", ".join(c.name.lower() for c in Color) + "."
    modifiers.add_argument(
        "-c",
        "--color",
        choices=[c.name.lower() for c in Color],
        default=None,
        help=f"List color for --new-list/--edit-list. Choices: {colors_str}",
    )
    modifiers.add_argument(
        "-p",
        "--priority",
        choices=[p.value for p in Priority],
        default=None,
        help="Item priority for -a/-e (default: medium on add).",
    )
    modifiers.add_argument(
        "-t",
        "--tag",
        dest="tags",
        action="append",
        default=[],
        metavar="TAG",
        help="Tag to set on -a/-e. Repeatable.",
    )
    modifiers.add_argument(
        "-f",
        "--filter-tag",
        dest="filter_tag",
        default=None,
        metavar="TAG",
        help="Only show items with this tag (default view only).",
    )
    modifiers.add_argument(
        "--all",
        dest="all",
        action="store_true",
        help=(
            "Include descendant lists in the default view. Without LIST, "
            "shows every list's items."
        ),
    )
    modifiers.add_argument(
        "--text",
        dest="text",
        default=None,
        help="Replace an item's text (-e only).",
    )

    return parser


def _resolve_list_op(namespace: argparse.Namespace) -> ListOp | None:
    if namespace.new_list:
        return ListOp.NEW_LIST
    if namespace.rm_list:
        return ListOp.RM_LIST
    if namespace.edit_list:
        return ListOp.EDIT_LIST
    if namespace.config is not None:
        return ListOp.CONFIG
    if namespace.lists:
        return ListOp.LISTS

    return None


def _resolve_item_action(namespace: argparse.Namespace) -> ItemAction | None:
    if namespace.add is not None:
        return ItemAction.ADD
    if namespace.done is not None:
        return ItemAction.DONE
    if namespace.undone is not None:
        return ItemAction.UNDONE
    if namespace.rm is not None:
        return ItemAction.RM
    if namespace.edit is not None:
        return ItemAction.EDIT
    if namespace.tags_action:
        return ItemAction.TAGS
    if namespace.prune:
        return ItemAction.PRUNE

    return None


def _validate_flags(
    namespace: argparse.Namespace,
    list_op: ListOp | None,
    item_action: ItemAction | None,
    parser: argparse.ArgumentParser,
) -> None:
    if list_op in {ListOp.CONFIG, ListOp.LISTS} and item_action:
        parser.error("item action flags are not valid with --config/--lists.")
    if namespace.all and any((item_action, list_op)):
        parser.error("--all is only valid with the default view.")
    if namespace.config and len(namespace.config) > 2:
        parser.error("--config takes at most KEY and VALUE.")
    if namespace.color and list_op not in {ListOp.NEW_LIST, ListOp.EDIT_LIST}:
        parser.error("-c/--color is only valid with --new-list/--edit-list.")
    if list_op == ListOp.EDIT_LIST and namespace.color is None:
        parser.error("--edit-list requires -c/--color.")

    add_or_edit = item_action in {ItemAction.ADD, ItemAction.EDIT}
    if namespace.tags and not add_or_edit:
        parser.error("-t/--tag is only valid with -a/--add or -e/--edit.")
    if namespace.priority and not add_or_edit:
        parser.error("-p/--priority is only valid with -a/--add or -e/--edit.")
    if namespace.filter_tag and any((item_action, list_op)):
        parser.error("-f/--filter-tag is only valid with the default view.")
    if namespace.text and item_action != ItemAction.EDIT:
        parser.error("--text is only valid with -e/--edit.")


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ")

    return answer.strip().lower() in {"y", "yes"}


def _print_list(task_list: TaskliList, config: Config) -> None:
    render_items(
        task_list.display_name(config.sublist_delimiter),
        task_list.items,
        task_list.color,
    )


def _mutate_cmd(
    list_name: str, config: Config, mutate: Callable[[TaskliList], str]
) -> int:
    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    message = mutate(task_list)

    save_list(storage_dir, task_list)
    print(message)
    _print_list(task_list, config)

    return 0


@_handle_errors
def _lists_cmd() -> int:
    storage_dir = resolve_storage_dir()

    entries: list[tuple[str, Color | None]] = []
    for name in list_all_lists(storage_dir):
        try:
            entries.append((name, load_list(storage_dir, name).color))
        except TaskliError:
            entries.append((name, None))

    render_list_names(entries)

    return 0


@_handle_errors
def _new_list_cmd(name: str, color: str | None, config: Config) -> int:
    storage_dir = resolve_storage_dir()
    resolved_color = (
        Color[color.upper()] if color is not None else config.default_color
    )

    task_list = create_list(storage_dir, name, color=resolved_color)

    display_name = task_list.display_name(config.sublist_delimiter)
    print(f"created list '{display_name}'.")
    _print_list(task_list, config)

    return 0


@_handle_errors
def _edit_list_cmd(name: str, color: str, config: Config) -> int:
    def mutate(task_list: TaskliList) -> str:
        task_list.set_color(Color[color.upper()])
        display_name = task_list.display_name(config.sublist_delimiter)

        return f"updated color of '{display_name}' to '{color}'."

    return _mutate_cmd(name, config, mutate)


@_handle_errors
def _config_cmd(key: str | None, value: str | None) -> int:
    storage_dir = resolve_storage_dir()
    config = load_config(storage_dir)

    if key is None:
        render_config(config)

        return 0

    if value is None:
        print(config.get_value(key))

        return 0

    config.set_value(key, value)
    save_config(storage_dir, config)

    if key == "default_sort":
        resort_all_lists(storage_dir, config.default_sort)

    print(f"set '{key}' to '{value}'.")

    return 0


@_handle_errors
def _rm_list_cmd(name: str, config: Config) -> int:
    storage_dir = resolve_storage_dir()
    descendants = descendant_list_names(name, list_all_lists(storage_dir))
    display_name = TaskliList(name=name).display_name(config.sublist_delimiter)

    prompt = f"delete list '{display_name}' and all its items?"
    if descendants:
        display_descendants = [
            TaskliList(name=d).display_name(config.sublist_delimiter)
            for d in descendants
        ]
        prompt = (
            f"delete list '{display_name}' and its {len(descendants)} "
            f"sublist(s) ({', '.join(display_descendants)}) and all "
            "their items?"
        )

    if not _confirm(prompt):
        print("aborted.")

        return 1

    deleted_descendants = delete_list(storage_dir, name)

    # no list left to print back after deletion.
    if deleted_descendants:
        print(
            f"deleted list '{display_name}' and {len(deleted_descendants)} "
            "sublist(s)."
        )
    else:
        print(f"deleted list '{display_name}'.")

    return 0


@_handle_errors
def _add_cmd(
    list_name: str,
    texts: list[str],
    tags: list[str],
    priority: str,
    config: Config,
) -> int:
    storage_dir = resolve_storage_dir()
    task_list = load_or_create_list(storage_dir, list_name)
    display_name = task_list.display_name(config.sublist_delimiter)

    # add items first --> re-sort --> print item indexes.
    added = [
        task_list.add_item(text, priority=Priority(priority), tags=list(tags))
        for text in texts
    ]

    task_list.resort(config.default_sort)

    for item in added:
        print(f"added #{item.id} to '{display_name}'.")

    save_list(storage_dir, task_list)
    _print_list(task_list, config)

    return 0


def _grouped_lists(
    storage_dir: Path,
    list_name: str,
    all_names: list[str],
    tag: str | None,
    config: Config,
) -> list[TaskliList]:
    task_list = load_list(storage_dir, list_name)
    if config.auto_prune and task_list.prune():
        save_list(storage_dir, task_list)

    lists = [
        TaskliList(
            name=list_name,
            color=task_list.color,
            items=task_list.filtered_items(tag=tag),
        )
    ]

    # filter each descendant list by tag if given to parent.
    for descendant_name in descendant_list_names(list_name, all_names):
        descendant_list = load_list(storage_dir, descendant_name)
        if config.auto_prune and descendant_list.prune():
            save_list(storage_dir, descendant_list)

        lists.append(
            TaskliList(
                name=descendant_name,
                color=descendant_list.color,
                items=descendant_list.filtered_items(tag=tag),
            )
        )

    return lists


@_handle_errors
def _list_cmd(
    list_name: str, tag: str | None, include_descendants: bool
) -> int:
    storage_dir = resolve_storage_dir()
    config = load_config(storage_dir)
    all_names = list_all_lists(storage_dir) if include_descendants else []

    render_list_tree(
        _grouped_lists(storage_dir, list_name, all_names, tag, config),
        config.sublist_delimiter,
    )

    return 0


@_handle_errors
def _all_cmd() -> int:
    storage_dir = resolve_storage_dir()
    config = load_config(storage_dir)
    all_names = list_all_lists(storage_dir)

    if not all_names:
        render_list_names([])

        return 0

    roots = [name for name in all_names if "." not in name]
    for root in roots:
        render_list_tree(
            _grouped_lists(storage_dir, root, all_names, None, config),
            config.sublist_delimiter,
        )

    return 0


@_handle_errors
def _done_cmd(list_name: str, item_id: int, config: Config) -> int:
    def mutate(task_list: TaskliList) -> str:
        task_list.mark_done(item_id)
        display_name = task_list.display_name(config.sublist_delimiter)

        return f"marked #{item_id} done in '{display_name}'."

    return _mutate_cmd(list_name, config, mutate)


@_handle_errors
def _undone_cmd(list_name: str, item_id: int, config: Config) -> int:
    def mutate(task_list: TaskliList) -> str:
        task_list.mark_undone(item_id)
        display_name = task_list.display_name(config.sublist_delimiter)

        return f"marked #{item_id} not done in '{display_name}'."

    return _mutate_cmd(list_name, config, mutate)


@_handle_errors
def _rm_cmd(list_name: str, item_id: int, config: Config) -> int:
    def mutate(task_list: TaskliList) -> str:
        task_list.remove_item(item_id)
        display_name = task_list.display_name(config.sublist_delimiter)

        return f"removed #{item_id} from '{display_name}'."

    return _mutate_cmd(list_name, config, mutate)


@_handle_errors
def _prune_cmd(list_name: str, config: Config) -> int:
    def mutate(task_list: TaskliList) -> str:
        removed = task_list.prune()
        display_name = task_list.display_name(config.sublist_delimiter)

        return f"pruned {len(removed)} item(s) from '{display_name}'."

    return _mutate_cmd(list_name, config, mutate)


@_handle_errors
def _edit_cmd(
    list_name: str,
    item_id: int,
    text: str | None,
    priority: str | None,
    tags: list[str],
    config: Config,
) -> int:
    def mutate(task_list: TaskliList) -> str:
        task_list.edit_item(
            item_id,
            text=text,
            priority=Priority(priority) if priority else None,
            tags=list(tags) if tags else None,
        )
        display_name = task_list.display_name(config.sublist_delimiter)

        return f"updated #{item_id} in '{display_name}'."

    return _mutate_cmd(list_name, config, mutate)


@_handle_errors
def _tags_cmd(list_name: str) -> int:
    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)

    tags = sorted({t for item in task_list.items for t in item.tags})
    for tag in tags:
        print(tag)

    return 0


def _run_item_action(
    action: ItemAction,
    list_name: str,
    namespace: argparse.Namespace,
    config: Config,
) -> int:
    if action == ItemAction.ADD:
        texts = [" ".join(words) for words in namespace.add]
        priority = namespace.priority or config.default_priority.value

        return _add_cmd(list_name, texts, namespace.tags, priority, config)
    if action == ItemAction.DONE:
        return _done_cmd(list_name, namespace.done, config)
    if action == ItemAction.UNDONE:
        return _undone_cmd(list_name, namespace.undone, config)
    if action == ItemAction.RM:
        return _rm_cmd(list_name, namespace.rm, config)
    if action == ItemAction.EDIT:
        return _edit_cmd(
            list_name,
            namespace.edit,
            namespace.text,
            namespace.priority,
            namespace.tags,
            config,
        )
    if action == ItemAction.TAGS:
        return _tags_cmd(list_name)

    return _prune_cmd(list_name, config)


def _dispatch(
    namespace: argparse.Namespace,
    config: Config,
    list_op: ListOp | None,
    item_action: ItemAction | None,
) -> int:
    if list_op == ListOp.LISTS:
        return _lists_cmd()
    if list_op == ListOp.CONFIG:
        key = namespace.config[0] if namespace.config else None
        value = namespace.config[1] if len(namespace.config) > 1 else None

        return _config_cmd(key, value)

    target_given = namespace.target is not None
    if target_given:
        list_name = namespace.target.replace(config.sublist_delimiter, ".")
    else:
        list_name = config.default_list.replace(config.sublist_delimiter, ".")

    if list_op == ListOp.NEW_LIST:
        exit_code = _new_list_cmd(list_name, namespace.color, config)
    elif list_op == ListOp.RM_LIST:
        exit_code = _rm_list_cmd(list_name, config)
    elif list_op == ListOp.EDIT_LIST:
        exit_code = _edit_list_cmd(list_name, namespace.color, config)
    elif item_action is not None:
        return _run_item_action(item_action, list_name, namespace, config)
    elif not target_given and namespace.all:
        return _all_cmd()
    else:
        return _list_cmd(list_name, namespace.filter_tag, namespace.all)

    if exit_code != 0 or item_action is None:
        return exit_code

    return _run_item_action(item_action, list_name, namespace, config)


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)

    parser = _build_parser()
    try:
        namespace = parser.parse_args(raw_argv)
        list_op = _resolve_list_op(namespace)
        item_action = _resolve_item_action(namespace)
        _validate_flags(namespace, list_op, item_action, parser)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    config = load_config(resolve_storage_dir())

    return _dispatch(namespace, config, list_op, item_action)


if __name__ == "__main__":
    sys.exit(main())
