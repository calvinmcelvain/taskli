import argparse
import functools
import sys
from collections.abc import Callable

from .exceptions import TodoError
from .models import Priority
from .render import render_error, render_grouped_items, render_list_names
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

LIST_SCOPED_ACTIONS: frozenset[str] = frozenset(
    {"add", "list", "done", "undone", "rm", "edit", "tags", "prune"}
)
TOP_LEVEL_COMMANDS: frozenset[str] = frozenset(
    {"lists", "new-list", "rm-list"}
)
RESERVED_NAMES: frozenset[str] = LIST_SCOPED_ACTIONS | TOP_LEVEL_COMMANDS


def _normalize_argv(argv: list[str]) -> list[str]:
    if not argv or argv[0].startswith("-"):
        return argv

    if argv[0] in LIST_SCOPED_ACTIONS:
        return ["inbox", *argv]

    return argv


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
    parser = argparse.ArgumentParser(
        prog="todo",
        description="A simple, elegant CLI for tracking todo lists.",
        epilog=(
            "List-scoped actions (run as `todo [LIST] ACTION ...`; LIST "
            "defaults to 'inbox'): add, list, done, undone, rm, edit, "
            "tags, prune.\n\n"
            'Example: todo work add "finish report" -p high -t urgent'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("lists", help="Show all list names.")

    new_list_parser = subparsers.add_parser(
        "new-list", help="Create a new, empty list."
    )
    new_list_parser.add_argument("name")

    rm_list_parser = subparsers.add_parser(
        "rm-list", help="Delete a whole list and all its items."
    )
    rm_list_parser.add_argument("name")

    return parser


def _build_list_action_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="todo LIST")
    subparsers = parser.add_subparsers(dest="action", required=True)

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("text")
    add_parser.add_argument(
        "-t", "--tag", dest="tags", action="append", default=[]
    )
    add_parser.add_argument(
        "-p",
        "--priority",
        choices=[p.value for p in Priority],
        default=Priority.MEDIUM.value,
    )

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("-t", "--tag", dest="tag", default=None)

    done_parser = subparsers.add_parser("done")
    done_parser.add_argument("item_id", type=int)

    undone_parser = subparsers.add_parser("undone")
    undone_parser.add_argument("item_id", type=int)

    rm_parser = subparsers.add_parser("rm")
    rm_parser.add_argument("item_id", type=int)

    edit_parser = subparsers.add_parser("edit")
    edit_parser.add_argument("item_id", type=int)
    edit_parser.add_argument("--text", dest="text", default=None)
    edit_parser.add_argument(
        "-p",
        "--priority",
        choices=[p.value for p in Priority],
        default=None,
    )
    edit_parser.add_argument(
        "-t", "--tag", dest="tags", action="append", default=[]
    )

    subparsers.add_parser("tags")
    subparsers.add_parser("prune")

    return parser


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ")

    return answer.strip().lower() in {"y", "yes"}


@_handle_errors
def _lists_cmd() -> int:
    storage_dir = resolve_storage_dir()

    render_list_names(list_all_lists(storage_dir))

    return 0


@_handle_errors
def _new_list_cmd(name: str) -> int:
    storage_dir = resolve_storage_dir()

    create_list(storage_dir, name, reserved_names=RESERVED_NAMES)

    print(f"created list '{name}'.")

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

    if deleted_descendants:
        print(
            f"deleted list '{name}' and {len(deleted_descendants)} "
            "sublist(s)."
        )
    else:
        print(f"deleted list '{name}'.")

    return 0


@_handle_errors
def _add_cmd(list_name: str, text: str, tags: list[str], priority: str) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_or_create_list(
        storage_dir, list_name, reserved_names=RESERVED_NAMES
    )
    item = todo_list.add_item(
        text, priority=Priority(priority), tags=list(tags)
    )

    save_list(storage_dir, todo_list)

    print(f"added #{item.id} to '{list_name}'.")

    return 0


@_handle_errors
def _list_cmd(list_name: str, tag: str | None) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)

    sections = [(list_name, todo_list.filtered_items(tag=tag))]

    # filter each decendent list by tag if given to parent.
    all_names = list_all_lists(storage_dir)
    for child_name in descendant_list_names(list_name, all_names):
        child_list = load_list(storage_dir, child_name)
        child_items = child_list.filtered_items(tag=tag)

        if tag is not None and not child_items:
            continue

        sections.append((child_name, child_items))

    render_grouped_items(sections)

    return 0


@_handle_errors
def _done_cmd(list_name: str, item_id: int) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    todo_list.mark_done(item_id)

    save_list(storage_dir, todo_list)

    print(f"marked #{item_id} done in '{list_name}'.")

    return 0


@_handle_errors
def _undone_cmd(list_name: str, item_id: int) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    todo_list.mark_undone(item_id)

    save_list(storage_dir, todo_list)

    print(f"marked #{item_id} not done in '{list_name}'.")

    return 0


@_handle_errors
def _rm_cmd(list_name: str, item_id: int) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    todo_list.remove_item(item_id)

    save_list(storage_dir, todo_list)

    print(f"removed #{item_id} from '{list_name}'.")

    return 0


@_handle_errors
def _prune_cmd(list_name: str) -> int:
    storage_dir = resolve_storage_dir()
    todo_list = load_list(storage_dir, list_name)
    removed = todo_list.remove_done_items()

    save_list(storage_dir, todo_list)

    print(f"pruned {len(removed)} item(s) from '{list_name}'.")

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
    if namespace.command == "new-list":
        return _new_list_cmd(namespace.name)

    return _rm_list_cmd(namespace.name)


def _dispatch_list_action(
    list_name: str, namespace: argparse.Namespace
) -> int:
    action = namespace.action
    if action == "add":
        return _add_cmd(
            list_name, namespace.text, namespace.tags, namespace.priority
        )
    if action == "list":
        return _list_cmd(list_name, namespace.tag)
    if action == "done":
        return _done_cmd(list_name, namespace.item_id)
    if action == "undone":
        return _undone_cmd(list_name, namespace.item_id)
    if action == "rm":
        return _rm_cmd(list_name, namespace.item_id)
    if action == "edit":
        return _edit_cmd(
            list_name,
            namespace.item_id,
            namespace.text,
            namespace.priority,
            namespace.tags,
        )
    if action == "tags":
        return _tags_cmd(list_name)

    return _prune_cmd(list_name)


def main(argv: list[str] | None = None) -> int:

    raw_argv = sys.argv[1:] if argv is None else argv
    if not raw_argv:
        raw_argv = ["inbox"]

    normalized = _normalize_argv(raw_argv)

    if normalized[0].startswith("-") or normalized[0] in TOP_LEVEL_COMMANDS:
        parser = _build_top_level_parser()
        try:
            namespace = parser.parse_args(normalized)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1

        return _dispatch_top_level(namespace)

    list_name, *rest = normalized
    if not rest or rest[0].startswith("-"):
        storage_dir = resolve_storage_dir()
        list_names = list_all_lists(storage_dir)
        if list_name != "inbox" and list_name not in list_names:
            rest = ["add", list_name, *rest]
            list_name = "inbox"
        else:
            rest = ["list", *rest]
    elif rest[0] not in LIST_SCOPED_ACTIONS:
        rest = ["add", *rest]

    parser = _build_list_action_parser()
    try:
        namespace = parser.parse_args(rest)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    return _dispatch_list_action(list_name, namespace)


if __name__ == "__main__":
    sys.exit(main())
