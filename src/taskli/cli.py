"""Command-line interface and argument routing."""

import argparse
import functools
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from .exceptions import ItemNotFoundError, TaskliError
from .models import Color, Config, Priority, TaskliList
from .render import (
    render_config,
    render_error,
    render_items,
    render_list_names,
    render_list_tree,
    render_warning,
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


def _handle_errors(func: Callable[..., int]) -> Callable[..., int]:
    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> int:
        try:
            return func(*args, **kwargs)
        except TaskliError as e:
            render_error(str(e))

            return 1

    return wrapper


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ")

    return answer.strip().lower() in {"y", "yes"}


def _print_list(task_list: TaskliList, config: Config) -> None:
    render_items(
        task_list.display_name(config.sublist_delimiter),
        task_list.items,
        task_list.color,
    )

    return None


class ListCommands(StrEnum):
    VIEW = "view"
    NEW = "new"
    DELETE = "delete"
    COLOR = "color"
    LISTS = "lists"
    PRUNE = "prune"


class ConfigCommands(StrEnum):
    CONFIG = "config"


class ItemActionCommands(StrEnum):
    ADD = "add"
    REMOVE = "remove"
    DONE = "done"
    UNDONE = "undone"
    EDIT = "edit"
    MOVE = "move"
    COPY = "copy"


class ModifierCommands(StrEnum):
    ALL = "all"
    PRIORITY = "priority"
    TAG = "tags"
    ADD_TAG = "add_tag"
    TEXT = "text"


type CommandOptions = ListCommands | ItemActionCommands | ConfigCommands


def _register_list_args(parser: argparse.ArgumentParser) -> None:
    list_group = parser.add_argument_group(
        "List management",
        "Add, remove, view, prune, or change the color for the given LIST.",
    )

    ops = list_group.add_mutually_exclusive_group()
    ops.add_argument(
        "-n",
        "--new",
        dest="new",
        action="store_true",
        help="Create LIST as a new, empty list.",
    )
    ops.add_argument(
        "--delete",
        dest="delete",
        action="store_true",
        help="Delete LIST and all its items.",
    )
    ops.add_argument(
        "-l",
        "--lists",
        dest="lists",
        action="store_true",
        help="Show every list name, nested as a tree.",
    )
    ops.add_argument(
        "--prune",
        dest="prune",
        action="store_true",
        help=(
            "Remove all done items from LIST. Combine with --all to prune"
            " all lists."
        ),
    )

    return None


def _register_config_args(parser: argparse.ArgumentParser) -> None:
    config_group = parser.add_argument_group(
        "Configuration management", "View or edit Taskli configs."
    )

    ops = config_group.add_mutually_exclusive_group()
    ops.add_argument(
        "--config",
        dest="config",
        nargs="*",
        default=None,
        metavar=("KEY", "VALUE"),
        help="View or edit config settings. Omit KEY/VALUE to view all.",
    )

    return None


def _register_item_action_args(parser: argparse.ArgumentParser) -> None:
    actions_group = parser.add_argument_group(
        "Item actions",
        "Add, remove, edit, or mark item(s) done/undone for the current LIST.",
    )

    ops = actions_group.add_mutually_exclusive_group()
    ops.add_argument(
        "-a",
        "--add",
        dest="add",
        nargs="+",
        action="append",
        metavar="TEXT",
        help="Add an item to LIST. Repeatable for multiple items.",
    )
    ops.add_argument(
        "-rm",
        "--remove",
        dest="remove",
        type=int,
        nargs="+",
        metavar="ID",
        help="Remove an item, or items, from LIST.",
    )
    ops.add_argument(
        "-d",
        "--done",
        dest="done",
        type=int,
        nargs="+",
        metavar="ID",
        help="Mark an item, or items, as done.",
    )
    ops.add_argument(
        "-u",
        "--undone",
        dest="undone",
        type=int,
        nargs="+",
        metavar="ID",
        help="Mark an item, or items, as not done.",
    )
    ops.add_argument(
        "-e",
        "--edit",
        dest="edit",
        type=int,
        nargs=1,
        metavar="ID",
        help="Edit an item's text, priority, or tags.",
    )
    ops.add_argument(
        "-mv",
        "--move",
        dest="move",
        nargs="+",
        metavar=("TARGET_LIST", "ID"),
        help=(
            "Move item(s) from LIST to TARGET_LIST. Omit ID to move"
            " every item in LIST."
        ),
    )
    ops.add_argument(
        "--copy",
        dest="copy",
        nargs="+",
        metavar=("TARGET_LIST", "ID"),
        help=(
            "Copy item(s) from LIST to TARGET_LIST. Omit ID to copy"
            " every item in LIST."
        ),
    )

    return None


def _register_modifier_args(parser: argparse.ArgumentParser) -> None:
    modifiers = parser.add_argument_group(
        "Modifiers", "Add to list or item action args to change behavior."
    )

    modifiers.add_argument(
        "-p",
        "--priority",
        choices=[p.value for p in Priority],
        nargs="?",
        default=None,
        help=(
            "Set or filter item's priority. Used to set priority for -a/-e."
            " Used to filter for viewing items."
        ),
    )
    modifiers.add_argument(
        "--tag",
        dest="tag",
        action="append",
        default=[],
        metavar="TAG",
        help=(
            "Set of filter item's tag. Used to add/replace tags for -a/-e."
            " Use to filter for viewing items. NOTE: If you want to add a tag"
            " and not REPLACE a tag, use --add-tag instead."
        ),
    )
    modifiers.add_argument(
        "--add-tag",
        dest="add_tag",
        action="append",
        default=[],
        metavar="TAG",
        help=(
            "Used to add a tag to an existing set of tags for an item. Can"
            " only be used for -e statements."
        ),
    )
    modifiers.add_argument(
        "--all",
        dest="all",
        action="store_true",
        help=(
            "Used to prune or view across multiple lists. See documentation"
            " for examples."
        ),
    )
    modifiers.add_argument(
        "-t",
        "--text",
        dest="text",
        type=str,
        default=None,
        help="Replace an item's text. Can use for -e statements only.",
    )
    modifiers.add_argument(
        "--color",
        dest="color",
        choices=[c.name.lower() for c in Color],
        nargs="?",
        default=None,
        help="Add/Change color of LIST.",
    )


def _compose_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taskli[tk]",
        description=(
            "Manage Taskli lists/items. LIST defaults to 'inbox' when omitted."
        ),
        epilog="Example: tk groceries --new --color teal",
    )
    parser.add_argument(
        "list",
        nargs="?",
        default=None,
        metavar="LIST",
        help="Name of the list to act on (default: configured default_list).",
    )

    # register commands/arg groups.
    _register_list_args(parser)
    _register_item_action_args(parser)
    _register_modifier_args(parser)
    _register_config_args(parser)

    return parser


def _resolve_list_op(namespace: argparse.Namespace) -> ListCommands | None:
    if namespace.new:
        return ListCommands.NEW
    if namespace.delete:
        return ListCommands.DELETE
    if namespace.lists:
        return ListCommands.LISTS
    if namespace.prune:
        return ListCommands.PRUNE
    # bare --color with no other list flag means "recolor this list."
    if namespace.color:
        return ListCommands.COLOR

    return None


def _resolve_item_action_op(
    namespace: argparse.Namespace,
) -> ItemActionCommands | None:
    if namespace.add:
        return ItemActionCommands.ADD
    if namespace.remove:
        return ItemActionCommands.REMOVE
    if namespace.done:
        return ItemActionCommands.DONE
    if namespace.undone:
        return ItemActionCommands.UNDONE
    if namespace.edit:
        return ItemActionCommands.EDIT
    if namespace.move:
        return ItemActionCommands.MOVE
    if namespace.copy:
        return ItemActionCommands.COPY

    return None


def _resolve_config_op(
    namespace: argparse.Namespace,
) -> ConfigCommands | None:
    if namespace.config is not None:
        return ConfigCommands.CONFIG

    return None


def _resolve_op(namespace: argparse.Namespace) -> CommandOptions:
    defined = [
        (label, op)
        for label, op in (
            ("list management", _resolve_list_op(namespace)),
            ("item action", _resolve_item_action_op(namespace)),
            ("config", _resolve_config_op(namespace)),
        )
        if op is not None
    ]

    # only allow one option. take first & warn.
    if len(defined) > 1:
        winner_label, winner_op = defined[0]
        ignored = ", ".join(label for label, _ in defined[1:])
        render_warning(
            f"multiple option groups given; using {winner_label} "
            f"('{winner_op.value}'), ignoring {ignored}."
        )

    if defined:
        return defined[0][1]

    # if no option (w/ exception of modifiers), default is view.
    return ListCommands.VIEW


def _validate(
    op: ListCommands | ItemActionCommands | ConfigCommands,
    namespace: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    match op:
        case ListCommands.DELETE | ListCommands.LISTS:
            if (
                namespace.priority
                or namespace.tag
                or namespace.add_tag
                or namespace.text
                or namespace.all
                or namespace.color
            ):
                parser.error(f"no modifiers are valid with --{op.value}.")
        case ListCommands.NEW | ListCommands.COLOR:
            # --color is the only modifier that means anything for either:
            # the initial color on creation, or the new color on recolor.
            if (
                namespace.priority
                or namespace.tag
                or namespace.add_tag
                or namespace.text
                or namespace.all
            ):
                parser.error(
                    "only --color is valid with --new/when recoloring an"
                    " existing list."
                )
        case ListCommands.PRUNE:
            if (
                namespace.priority
                or namespace.tag
                or namespace.add_tag
                or namespace.text
                or namespace.color
            ):
                parser.error("only --all is valid with --prune.")
        case ItemActionCommands.ADD:
            if namespace.add_tag or namespace.text or namespace.all:
                parser.error(
                    "--add-tag/--text/--all are not valid with -a/--add."
                )
        case ItemActionCommands.EDIT:
            if namespace.tag and namespace.add_tag:
                parser.error(
                    "--tag and --add-tag cannot both be given; --tag"
                    " replaces, --add-tag appends."
                )
            if namespace.all:
                parser.error("--all is not valid with -e/--edit.")
        case (
            ItemActionCommands.REMOVE
            | ItemActionCommands.DONE
            | ItemActionCommands.UNDONE
        ):
            if (
                namespace.priority
                or namespace.tag
                or namespace.add_tag
                or namespace.text
                or namespace.all
                or namespace.color
            ):
                parser.error(f"no modifiers are valid with --{op.value}.")
        case ItemActionCommands.MOVE | ItemActionCommands.COPY:
            ids = (
                namespace.move
                if op == ItemActionCommands.MOVE
                else namespace.copy
            )[1:]
            try:
                [int(i) for i in ids]
            except ValueError:
                parser.error("ID must be an integer.")
            if (
                namespace.priority
                or namespace.tag
                or namespace.add_tag
                or namespace.text
                or namespace.all
                or namespace.color
            ):
                parser.error(f"no modifiers are valid with --{op.value}.")
        case ConfigCommands.CONFIG:
            if namespace.config and len(namespace.config) > 2:
                parser.error("--config takes at most KEY and VALUE.")
            if (
                namespace.priority
                or namespace.tag
                or namespace.add_tag
                or namespace.text
                or namespace.all
                or namespace.color
            ):
                parser.error("no modifiers are valid with --config.")
        case ListCommands.VIEW:
            if namespace.add_tag or namespace.text or namespace.color:
                parser.error(
                    "--add-tag/--text/--color are not valid with the"
                    " default view."
                )

    return None


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
def _lists_cmd(config: Config) -> int:
    storage_dir = resolve_storage_dir()

    entries: list[tuple[str, Color | None]] = []
    for name in list_all_lists(storage_dir):
        try:
            entries.append((name, load_list(storage_dir, name).color))
        except TaskliError:
            entries.append((name, None))

    default_name = config.default_list.replace(config.sublist_delimiter, ".")
    render_list_names(entries, default_name)

    return 0


@_handle_errors
def _new_list_cmd(name: str, color: str | None, config: Config) -> int:
    storage_dir = resolve_storage_dir()
    resolved_color = Color[color.upper()] if color else config.default_color

    task_list = create_list(storage_dir, name, color=resolved_color)

    display_name = task_list.display_name(config.sublist_delimiter)
    print(f"created list '{display_name}'.")
    _print_list(task_list, config)

    return 0


@_handle_errors
def _color_cmd(name: str, color: str, config: Config) -> int:
    def mutate(task_list: TaskliList) -> str:
        task_list.set_color(Color[color.upper()])
        display_name = task_list.display_name(config.sublist_delimiter)

        return f"updated color of '{display_name}' to '{color}'."

    return _mutate_cmd(name, config, mutate)


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
    priority: Priority | None,
    config: Config,
) -> list[TaskliList]:
    task_list = load_list(storage_dir, list_name)
    if config.auto_prune and task_list.prune():
        save_list(storage_dir, task_list)

    lists = [
        TaskliList(
            name=list_name,
            color=task_list.color,
            items=task_list.filtered_items(tag=tag, priority=priority),
        )
    ]

    # filter each descendant list by tag/priority if given to parent.
    for descendant_name in descendant_list_names(list_name, all_names):
        descendant_list = load_list(storage_dir, descendant_name)
        if config.auto_prune and descendant_list.prune():
            save_list(storage_dir, descendant_list)

        lists.append(
            TaskliList(
                name=descendant_name,
                color=descendant_list.color,
                items=descendant_list.filtered_items(
                    tag=tag, priority=priority
                ),
            )
        )

    return lists


@_handle_errors
def _list_cmd(
    list_name: str,
    tag: str | None,
    priority: str | None,
    include_descendants: bool,
) -> int:
    storage_dir = resolve_storage_dir()
    config = load_config(storage_dir)
    all_names = list_all_lists(storage_dir) if include_descendants else []
    resolved_priority = Priority(priority) if priority else None

    render_list_tree(
        _grouped_lists(
            storage_dir, list_name, all_names, tag, resolved_priority, config
        ),
        config.sublist_delimiter,
    )

    return 0


@_handle_errors
def _all_cmd(tag: str | None, priority: str | None) -> int:
    storage_dir = resolve_storage_dir()
    config = load_config(storage_dir)
    all_names = list_all_lists(storage_dir)
    resolved_priority = Priority(priority) if priority else None

    if not all_names:
        render_list_names([])

        return 0

    roots = [name for name in all_names if "." not in name]
    for root in roots:
        render_list_tree(
            _grouped_lists(
                storage_dir, root, all_names, tag, resolved_priority, config
            ),
            config.sublist_delimiter,
        )

    return 0


@_handle_errors
def _done_cmd(list_name: str, item_ids: list[int], config: Config) -> int:
    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    display_name = task_list.display_name(config.sublist_delimiter)

    failed = False
    for item_id in item_ids:
        try:
            task_list.mark_done(item_id)
            print(f"marked #{item_id} done in '{display_name}'.")
        except ItemNotFoundError as e:
            render_warning(str(e))
            failed = True

    save_list(storage_dir, task_list)
    _print_list(task_list, config)

    return 1 if failed else 0


@_handle_errors
def _undone_cmd(list_name: str, item_ids: list[int], config: Config) -> int:
    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    display_name = task_list.display_name(config.sublist_delimiter)

    failed = False
    for item_id in item_ids:
        try:
            task_list.mark_undone(item_id)
            print(f"marked #{item_id} not done in '{display_name}'.")
        except ItemNotFoundError as e:
            render_warning(str(e))
            failed = True

    save_list(storage_dir, task_list)
    _print_list(task_list, config)

    return 1 if failed else 0


@_handle_errors
def _rm_cmd(list_name: str, item_ids: list[int], config: Config) -> int:
    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    display_name = task_list.display_name(config.sublist_delimiter)

    failed = False
    # remove_item reindexes on every call, which renumbers ids positioned
    # after the removed one; working id-descending keeps not-yet-processed
    # ids stable.
    for item_id in sorted(item_ids, reverse=True):
        try:
            task_list.remove_item(item_id)
            print(f"removed #{item_id} from '{display_name}'.")
        except ItemNotFoundError as e:
            render_warning(str(e))
            failed = True

    save_list(storage_dir, task_list)
    _print_list(task_list, config)

    return 1 if failed else 0


@_handle_errors
def _prune_cmd(
    list_name: str, all: bool, target_given: bool, config: Config
) -> int:
    storage_dir = resolve_storage_dir()

    # an explicit LIST scopes --all to LIST + its descendants (a missing
    # LIST still raises, same as without --all); no LIST (falls back to
    # default_list) prunes every list instead, same as the default view's
    # --all fallback.
    lists: list[TaskliList] = [load_list(storage_dir, list_name)]
    if all:
        all_lists = list_all_lists(storage_dir)
        if target_given:
            lists.extend(
                [
                    load_list(storage_dir, lst)
                    for lst in descendant_list_names(list_name, all_lists)
                ]
            )
        else:
            lists.extend([load_list(storage_dir, lst) for lst in all_lists])

    for lst in lists:
        removed = lst.prune()
        save_list(storage_dir, lst)

        display_name = lst.display_name(config.sublist_delimiter)

        print(f"pruned {len(removed)} item(s) from '{display_name}'.")

    render_list_tree(lists, config.sublist_delimiter)

    return 0


@_handle_errors
def _edit_cmd(
    list_name: str,
    item_id: int,
    text: str | None,
    priority: str | None,
    tags: list[str],
    add_tag: list[str],
    config: Config,
) -> int:
    def mutate(task_list: TaskliList) -> str:
        task_list.edit_item(
            item_id,
            text=text,
            priority=Priority(priority) if priority else None,
            tags=list(tags) if tags else None,
        )
        if add_tag:
            task_list.add_tags(item_id, add_tag)

        display_name = task_list.display_name(config.sublist_delimiter)

        return f"updated #{item_id} in '{display_name}'."

    return _mutate_cmd(list_name, config, mutate)


@_handle_errors
def _move_cmd(
    list_name: str, target_name: str, item_ids: list[int], config: Config
) -> int:
    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    target_list = load_or_create_list(storage_dir, target_name)
    display_name = task_list.display_name(config.sublist_delimiter)
    target_display_name = target_list.display_name(config.sublist_delimiter)

    ids = item_ids or [item.id for item in task_list.items]

    # move_item reindexes the source on every call, renumbering ids
    # positioned after the one just moved; id-descending order keeps
    # not-yet-processed ids stable, same reasoning as -rm's batch loop.
    failed = False
    for item_id in sorted(ids, reverse=True):
        try:
            task_list.move_item(item_id, target_list)
            print(
                f"moved #{item_id} from '{display_name}' to "
                f"'{target_display_name}'."
            )
        except ItemNotFoundError as e:
            render_warning(str(e))
            failed = True

    target_list.resort(config.default_sort)

    save_list(storage_dir, task_list)
    save_list(storage_dir, target_list)
    _print_list(target_list, config)

    return 1 if failed else 0


@_handle_errors
def _copy_cmd(
    list_name: str, target_name: str, item_ids: list[int], config: Config
) -> int:
    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    target_list = load_or_create_list(storage_dir, target_name)
    display_name = task_list.display_name(config.sublist_delimiter)
    target_display_name = target_list.display_name(config.sublist_delimiter)

    ids = item_ids or [item.id for item in task_list.items]

    failed = False
    for item_id in ids:
        try:
            task_list.copy_item(item_id, target_list)
            print(
                f"copied #{item_id} from '{display_name}' to "
                f"'{target_display_name}'."
            )
        except ItemNotFoundError as e:
            render_warning(str(e))
            failed = True

    target_list.resort(config.default_sort)

    save_list(storage_dir, target_list)
    _print_list(target_list, config)

    return 1 if failed else 0


def _run_item_action(
    action: ItemActionCommands,
    list_name: str,
    namespace: argparse.Namespace,
    config: Config,
) -> int:
    match action:
        case ItemActionCommands.ADD:
            texts = [" ".join(words) for words in namespace.add]
            priority = namespace.priority or config.default_priority.value

            return _add_cmd(list_name, texts, namespace.tag, priority, config)
        case ItemActionCommands.DONE:
            return _done_cmd(list_name, namespace.done, config)
        case ItemActionCommands.UNDONE:
            return _undone_cmd(list_name, namespace.undone, config)
        case ItemActionCommands.REMOVE:
            return _rm_cmd(list_name, namespace.remove, config)
        case ItemActionCommands.MOVE:
            target, *ids = namespace.move
            target_name = target.replace(config.sublist_delimiter, ".")

            return _move_cmd(
                list_name, target_name, [int(i) for i in ids], config
            )
        case ItemActionCommands.COPY:
            target, *ids = namespace.copy
            target_name = target.replace(config.sublist_delimiter, ".")

            return _copy_cmd(
                list_name, target_name, [int(i) for i in ids], config
            )

    # only EDIT is left once the match above didn't return.
    return _edit_cmd(
        list_name,
        namespace.edit[0],
        namespace.text,
        namespace.priority,
        namespace.tag,
        namespace.add_tag,
        config,
    )


def _dispatch(
    namespace: argparse.Namespace,
    config: Config,
    op: ListCommands | ItemActionCommands | ConfigCommands,
) -> int:
    if namespace.list:
        list_name = namespace.list.replace(config.sublist_delimiter, ".")
    else:
        list_name = config.default_list.replace(config.sublist_delimiter, ".")

    match op:
        case ListCommands.LISTS:
            return _lists_cmd(config)
        case ConfigCommands.CONFIG:
            key = namespace.config[0] if namespace.config else None
            value = namespace.config[1] if len(namespace.config) > 1 else None

            return _config_cmd(key, value)
        case ListCommands.NEW:
            return _new_list_cmd(list_name, namespace.color, config)
        case ListCommands.DELETE:
            return _rm_list_cmd(list_name, config)
        case ListCommands.COLOR:
            return _color_cmd(list_name, namespace.color, config)
        case ListCommands.PRUNE:
            return _prune_cmd(
                list_name, namespace.all, bool(namespace.list), config
            )
        case ItemActionCommands():
            return _run_item_action(op, list_name, namespace, config)
        case _:
            # only ListCommands.VIEW reaches here; it's the fallback when
            # nothing else matched, so it's never named explicitly.
            tag_filter = namespace.tag[0] if namespace.tag else None
            if not namespace.list and namespace.all:
                return _all_cmd(tag_filter, namespace.priority)

            return _list_cmd(
                list_name, tag_filter, namespace.priority, namespace.all
            )


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)

    parser = _compose_parser()
    try:
        namespace = parser.parse_args(raw_argv)
        op = _resolve_op(namespace)
        _validate(op, namespace, parser)

    # argparse calls sys.exit for --help and its own parse errors; convert
    # that into a return code instead of letting it propagate.
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    config = load_config(resolve_storage_dir())

    return _dispatch(namespace, config, op)


if __name__ == "__main__":
    sys.exit(main())
