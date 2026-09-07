# PYTHON_ARGCOMPLETE_OK
"""Command-line interface and argument routing."""

import argparse
import functools
import sys
from collections.abc import Callable
from enum import StrEnum
from typing import Any, NamedTuple

import argcomplete

from . import logic
from .__version__ import __version__
from .exceptions import TaskliError
from .models import (
    Color,
    Config,
    Criterion,
    Filter,
    Priority,
    TaskliList,
    due_to_criteria,
    registry,
)
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


def _render_notices(result: logic.CommandResult) -> None:
    """Render a result's messages, then its warnings."""

    for message in result.messages:
        render_message(message)
    for warning in result.warnings:
        render_warning(warning)

    return None


def _emit(result: logic.CommandResult, config: Config) -> int:
    """Render a command result: messages, warnings, then any list view."""

    _render_notices(result)

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
    MIGRATE = "migrate"


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


type CommandOptions = ListCommands | ItemActionCommands | ConfigCommands


class ModifierArg(NamedTuple):
    flags: tuple[str, ...]
    dest: str
    kwargs: dict[str, Any]


class ModifierSpec(NamedTuple):
    args: tuple[ModifierArg, ...]
    to_criteria: Callable[[str], tuple[Criterion, ...]] | None = None
    filter_dest: str | None = None


MODIFIER_FLAGS: dict[str, ModifierSpec] = {
    "priority": ModifierSpec(
        args=(
            ModifierArg(
                flags=("-p", "--priority"),
                dest="priority",
                kwargs={
                    "choices": [p.name.lower() for p in Priority],
                    "nargs": "?",
                    "default": None,
                    "help": (
                        "Set or filter item's priority. Used to set"
                        " priority for -a/-e. Used to filter for viewing"
                        " items."
                    ),
                },
            ),
        ),
        filter_dest="priority",
    ),
    "tags": ModifierSpec(
        args=(
            ModifierArg(
                flags=("--tag",),
                dest="tag",
                kwargs={
                    "action": "append",
                    "default": [],
                    "metavar": "TAG",
                    "help": (
                        "Set of filter item's tag. Used to add/replace"
                        " tags for -a/-e. Use to filter for viewing"
                        " items. NOTE: If you want to add a tag and not"
                        " REPLACE a tag, use --add-tag instead."
                    ),
                },
            ),
            ModifierArg(
                flags=("--add-tag",),
                dest="add_tag",
                kwargs={
                    "action": "append",
                    "default": [],
                    "metavar": "TAG",
                    "help": (
                        "Used to add a tag to an existing set of tags"
                        " for an item. Can only be used for -e"
                        " statements."
                    ),
                },
            ),
        ),
        filter_dest="tag",
    ),
    "due_date": ModifierSpec(
        args=(
            ModifierArg(
                flags=("--due",),
                dest="due",
                kwargs={
                    "default": None,
                    "metavar": "WHEN",
                    "help": (
                        "Set (with -a/-e) or filter (default view) an"
                        " item's due date. Accepts: today, tomorrow,"
                        " 'N days', 'next week', 'N weeks', MM-DD-YYYY."
                        " Filtering also accepts 'overdue'."
                    ),
                },
            ),
        ),
        filter_dest="due",
        to_criteria=due_to_criteria,
    ),
    "text": ModifierSpec(
        args=(
            ModifierArg(
                flags=("-t", "--text"),
                dest="text",
                kwargs={
                    "type": str,
                    "default": None,
                    "help": (
                        "Replace an item's text. Can use for -e"
                        " statements only."
                    ),
                },
            ),
        ),
    ),
    "description": ModifierSpec(
        args=(
            ModifierArg(
                flags=("--desc",),
                dest="desc",
                kwargs={
                    "type": str,
                    "default": None,
                    "metavar": "TEXT",
                    "help": (
                        "Set (with -a/-e) an item's description; pass an"
                        " empty string to clear it. -a/-e only."
                    ),
                },
            ),
        ),
    ),
    "color": ModifierSpec(
        args=(
            ModifierArg(
                flags=("--color",),
                dest="color",
                kwargs={
                    "choices": [c.name.lower() for c in Color],
                    "nargs": "?",
                    "default": None,
                    "help": "Add/Change color of LIST.",
                },
            ),
        ),
    ),
}


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
    ops.add_argument(
        "--migrate",
        dest="migrate",
        action="store_true",
        help=(
            "Bring every list and config file up to the current on-disk"
            " schema."
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

    for spec in MODIFIER_FLAGS.values():
        for arg in spec.args:
            modifiers.add_argument(*arg.flags, dest=arg.dest, **arg.kwargs)
    modifiers.add_argument(
        "--all",
        dest="all",
        action="store_true",
        help=(
            "Used to prune or view across multiple lists. See documentation"
            " for examples."
        ),
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
    if namespace.migrate:
        return ListCommands.MIGRATE
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


def _reject_modifiers(
    namespace: argparse.Namespace,
    parser: argparse.ArgumentParser,
    message: str,
    allowed: set[str],
) -> None:
    # every modifier dest, plus the hand-wired --all scope flag.
    dests = {"all"} | {
        arg.dest for spec in MODIFIER_FLAGS.values() for arg in spec.args
    }
    for dest in sorted(dests - allowed):
        if getattr(namespace, dest):
            parser.error(message)

    return None


def _validate(
    op: ListCommands | ItemActionCommands | ConfigCommands,
    namespace: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    match op:
        case (
            ListCommands.DELETE
            | ListCommands.LISTS
            | ListCommands.RENAME
            | ListCommands.MIGRATE
        ):
            _reject_modifiers(
                namespace,
                parser,
                f"no modifiers are valid with --{op.value}.",
                set(),
            )
        case ListCommands.NEW | ListCommands.COLOR:
            # --color is the only modifier that means anything for either:
            # the initial color on creation, or the new color on recolor.
            _reject_modifiers(
                namespace,
                parser,
                "only --color is valid with --new/when recoloring an"
                " existing list.",
                {"color"},
            )
        case ListCommands.PRUNE:
            _reject_modifiers(
                namespace,
                parser,
                "only --all is valid with --prune.",
                {"all"},
            )
        case ItemActionCommands.ADD:
            _reject_modifiers(
                namespace,
                parser,
                "--add-tag/--text/--all are not valid with -a/--add.",
                {"priority", "tag", "due", "desc"},
            )
        case ItemActionCommands.EDIT:
            if namespace.tag and namespace.add_tag:
                parser.error(
                    "--tag and --add-tag cannot both be given; --tag"
                    " replaces, --add-tag appends."
                )
            _reject_modifiers(
                namespace,
                parser,
                "--all is not valid with -e/--edit.",
                {"priority", "tag", "add_tag", "text", "due", "desc"},
            )
        case (
            ItemActionCommands.REMOVE
            | ItemActionCommands.DONE
            | ItemActionCommands.UNDONE
            | ItemActionCommands.IN_PROGRESS
        ):
            _reject_modifiers(
                namespace,
                parser,
                f"no modifiers are valid with --{op.value}.",
                set(),
            )
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
            _reject_modifiers(
                namespace,
                parser,
                f"no modifiers are valid with --{op.value}.",
                set(),
            )
        case ConfigCommands.CONFIG:
            if namespace.config and len(namespace.config) > 2:
                parser.error("--config takes at most KEY and VALUE.")
            _reject_modifiers(
                namespace,
                parser,
                "no modifiers are valid with --config.",
                set(),
            )
        case ListCommands.VIEW:
            _reject_modifiers(
                namespace,
                parser,
                "--add-tag/--text/--color are not valid with the"
                " default view.",
                {"priority", "tag", "all", "due"},
            )

    return None


def _modifier_values(
    op: ItemActionCommands, namespace: argparse.Namespace
) -> dict[str, object]:
    values: dict[str, object] = {}
    for name, spec in MODIFIER_FLAGS.items():
        if op not in registry.ATTRIBUTES[name].modifier_ops:
            continue
        if name == "tags":
            if namespace.tag:
                values["tags"] = namespace.tag
            if op is ItemActionCommands.EDIT and namespace.add_tag:
                values["add_tag"] = namespace.add_tag
            continue
        value = getattr(namespace, spec.args[0].dest)
        if value is not None:
            values[name] = value

    return values


def _run_item_action(
    action: ItemActionCommands,
    list_name: str,
    namespace: argparse.Namespace,
    config: Config,
) -> logic.CommandResult:
    match action:
        case ItemActionCommands.ADD:
            texts = [" ".join(words) for words in namespace.add]

            return logic.add(
                list_name,
                texts,
                _modifier_values(action, namespace),
                config,
            )
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
        _modifier_values(ItemActionCommands.EDIT, namespace),
        config,
    )


@_handle_errors
def _dispatch(
    namespace: argparse.Namespace,
    op: ListCommands | ItemActionCommands | ConfigCommands,
) -> int:
    if op is ListCommands.MIGRATE:
        result = logic.migrate()
        _render_notices(result)

        return result.exit_code

    config = load_config(resolve_storage_dir())

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
            criteria: list[Criterion] = []
            for name, attr in registry.filterable().items():
                spec = MODIFIER_FLAGS[name]
                dest = spec.filter_dest

                assert dest is not None  # filterable entries set it.

                raw = getattr(namespace, dest)
                if not raw:
                    continue

                value = raw[0] if isinstance(raw, list) else raw

                if spec.to_criteria is not None:
                    criteria.extend(spec.to_criteria(value))
                    continue

                parse = attr.parse
                operand = parse(value) if parse is not None else value
                operator = attr.filter_default_operator

                assert operator is not None  # filterable() entries set it.

                criteria.append(Criterion(name, operator, operand))

            item_filter = Filter(tuple(criteria))

            if not namespace.list and namespace.all:
                groups = logic.all_views(item_filter)
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
                item_filter,
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

    return _dispatch(namespace, op)


if __name__ == "__main__":
    sys.exit(main())
