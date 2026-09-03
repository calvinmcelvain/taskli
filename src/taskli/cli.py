# PYTHON_ARGCOMPLETE_OK
"""Command-line interface and argument routing."""

import argparse
import functools
import sys
from collections.abc import Callable
from enum import StrEnum

import argcomplete

from . import logic
from .__version__ import __version__
from .exceptions import TaskliError
from .models import Color, Config, Priority, TaskliList
from .render import (
    render_config,
    render_error,
    render_items,
    render_list_names,
    render_list_tree,
    render_message,
    render_value,
    render_warning,
)
from .storage import load_config, resolve_storage_dir


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


def _emit(result: logic.CommandResult, config: Config) -> int:
    """Render a command result: messages, warnings, then any list view."""

    for message in result.messages:
        render_message(message)
    for warning in result.warnings:
        render_warning(warning)

    if result.item_view is not None:
        _print_list(result.item_view, config)
    if result.tree_view is not None:
        render_list_tree(result.tree_view, config.sublist_delimiter)

    return result.exit_code


class ListCommands(StrEnum):
    VIEW = "view"
    NEW = "new"
    DELETE = "delete"
    COLOR = "color"
    LISTS = "lists"
    PRUNE = "prune"
    RENAME = "rename"


class ConfigCommands(StrEnum):
    CONFIG = "config"


class ItemActionCommands(StrEnum):
    ADD = "add"
    REMOVE = "remove"
    DONE = "done"
    UNDONE = "undone"
    IN_PROGRESS = "in_progress"
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
    ops.add_argument(
        "--rename",
        dest="rename",
        default=None,
        metavar="NEW_NAME",
        help="Rename LIST (and its sublists) to NEW_NAME.",
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
        "Add, remove, edit, or mark item(s) done/in-progress/undone for the"
        " current LIST.",
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
        "-i",
        "--in-progress",
        dest="in_progress",
        type=int,
        nargs="+",
        metavar="ID",
        help="Mark an item, or items, as in progress.",
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
        choices=[p.name.lower() for p in Priority],
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


def _complete_list_names(
    prefix: str, parsed_args: argparse.Namespace, **kwargs: object
) -> list[str]:
    """argcomplete callback: existing list names for the LIST positional."""

    return logic.list_names()


def _compose_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taskli[tk]",
        description=(
            "Manage Taskli lists/items. LIST defaults to 'inbox' when omitted."
        ),
        epilog="Example: tk groceries --new --color teal",
    )
    list_action = parser.add_argument(
        "list",
        nargs="?",
        default=None,
        metavar="LIST",
        help="Name of the list to act on (default: configured default_list).",
    )
    list_action.completer = _complete_list_names  # type: ignore[attr-defined]
    parser.add_argument(
        "--version",
        action="version",
        version=f"taskli {__version__}",
    )
    parser.add_argument(
        "--path",
        action="store_true",
        help="Print the storage directory currently in use and exit.",
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
    if namespace.rename:
        return ListCommands.RENAME
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
    if namespace.in_progress:
        return ItemActionCommands.IN_PROGRESS
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
        case ListCommands.DELETE | ListCommands.LISTS | ListCommands.RENAME:
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
            | ItemActionCommands.IN_PROGRESS
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


def _run_item_action(
    action: ItemActionCommands,
    list_name: str,
    namespace: argparse.Namespace,
    config: Config,
) -> logic.CommandResult:
    match action:
        case ItemActionCommands.ADD:
            texts = [" ".join(words) for words in namespace.add]
            priority = (
                namespace.priority or config.default_priority.name.lower()
            )

            return logic.add(list_name, texts, namespace.tag, priority, config)
        case ItemActionCommands.DONE:
            return logic.mark_done(list_name, namespace.done, config)
        case ItemActionCommands.UNDONE:
            return logic.mark_undone(list_name, namespace.undone, config)
        case ItemActionCommands.IN_PROGRESS:
            return logic.mark_in_progress(
                list_name, namespace.in_progress, config
            )
        case ItemActionCommands.REMOVE:
            return logic.remove_items(list_name, namespace.remove, config)
        case ItemActionCommands.MOVE:
            target, *ids = namespace.move
            target_name = target.replace(config.sublist_delimiter, ".")

            return logic.move(
                list_name, target_name, [int(i) for i in ids], config
            )
        case ItemActionCommands.COPY:
            target, *ids = namespace.copy
            target_name = target.replace(config.sublist_delimiter, ".")

            return logic.copy(
                list_name, target_name, [int(i) for i in ids], config
            )

    # only EDIT is left once the match above didn't return.
    return logic.edit(
        list_name,
        namespace.edit[0],
        namespace.text,
        namespace.priority,
        namespace.tag,
        namespace.add_tag,
        config,
    )


@_handle_errors
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
            default_name = config.default_list.replace(
                config.sublist_delimiter, "."
            )
            render_list_names(logic.list_entries(), default_name)

            return 0
        case ConfigCommands.CONFIG:
            key = namespace.config[0] if namespace.config else None
            value = namespace.config[1] if len(namespace.config) > 1 else None

            if key is None:
                render_config(config)

                return 0
            if value is None:
                render_value(str(config.get_value(key)))

                return 0

            return _emit(logic.set_config(key, value), config)
        case ListCommands.NEW:
            return _emit(
                logic.new_list(list_name, namespace.color, config), config
            )
        case ListCommands.DELETE:
            prompt = logic.delete_prompt(list_name, config)
            if not _confirm(prompt):
                render_message("aborted.")

                return 1

            return _emit(logic.delete_confirmed(list_name, config), config)
        case ListCommands.COLOR:
            return _emit(
                logic.set_list_color(list_name, namespace.color, config),
                config,
            )
        case ListCommands.PRUNE:
            return _emit(
                logic.prune(
                    list_name,
                    namespace.all,
                    bool(namespace.list),
                    config,
                ),
                config,
            )
        case ListCommands.RENAME:
            new_name = namespace.rename.replace(config.sublist_delimiter, ".")

            return _emit(logic.rename(list_name, new_name, config), config)
        case ItemActionCommands():
            return _emit(
                _run_item_action(op, list_name, namespace, config), config
            )
        case _:
            # only ListCommands.VIEW reaches here; it's the fallback when
            # nothing else matched, so it's never named explicitly.
            tag_filter = namespace.tag[0] if namespace.tag else None

            if not namespace.list and namespace.all:
                groups = logic.all_views(tag_filter, namespace.priority)
                if not groups:
                    # all_views returns [] either for a filter that
                    # matched nothing or for genuinely-empty storage;
                    # has_any_lists tells the two apart.
                    if logic.has_any_lists():
                        render_message("no items match the given filter.")
                    else:
                        render_list_names([])

                    return 0
                for group in groups:
                    render_list_tree(group, config.sublist_delimiter)

                return 0

            views = logic.list_view(
                list_name,
                tag_filter,
                namespace.priority,
                namespace.all,
            )
            if not views:
                # no empty-storage case to disambiguate here (unlike the
                # --all branch): a missing target raises before list_view
                # can return [], so [] always means the filter pruned
                # every list from a --all view.
                render_message("no items match the given filter.")

                return 0

            render_list_tree(views, config.sublist_delimiter)

            return 0


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)

    parser = _compose_parser()
    try:
        argcomplete.autocomplete(parser)
        namespace = parser.parse_args(raw_argv)

        if namespace.path:
            render_value(str(logic.storage_path()))

            return 0

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
