"""Per-command orchestration between the CLI and storage/models."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .exceptions import ItemNotFoundError, TaskliError
from .hierarchy import ancestor_chain, descendant_list_names
from .models import (
    Color,
    Config,
    Filter,
    Priority,
    Sort,
    TaskliItem,
    TaskliList,
)
from .storage import (
    create_list,
    delete_list,
    list_all_lists,
    load_config,
    load_list,
    load_or_create_list,
    migrate_all,
    rename_list,
    resolve_storage_dir,
    resort_all_lists,
    save_config,
    save_list,
)


@dataclass
class CommandResult:
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    exit_code: int = 0
    item_view: TaskliList | None = None
    tree_view: list[TaskliList] | None = None


def storage_path() -> Path:
    """Return the storage directory currently in use.

    Returns
    -------
    Path
        The resolved storage directory.
    """

    return resolve_storage_dir()


def _mutate(
    list_name: str, mutate_fn: Callable[[TaskliList], str]
) -> CommandResult:
    """Load a list, apply ``mutate_fn``, save, and echo the list back."""

    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    message = mutate_fn(task_list)

    save_list(storage_dir, task_list)

    return CommandResult(messages=[message], item_view=task_list)


def add(
    list_name: str,
    texts: list[str],
    tags: list[str],
    priority: str,
    config: Config,
) -> CommandResult:
    """Add one or more items to a list, creating the list if missing.

    Parameters
    ----------
    list_name : str
        The target list.
    texts : list[str]
        One entry per item to add.
    tags : list[str]
        Tags applied to every item added in this call.
    priority : str
        Priority name (lower-cased) applied to every item added.
    config : Config
        The active config, for the display name and default sort.

    Returns
    -------
    CommandResult
        One message per added item plus the list as the item view.
    """

    storage_dir = resolve_storage_dir()
    task_list = load_or_create_list(storage_dir, list_name)
    display_name = task_list.display_name(config.sublist_delimiter)

    added = [
        task_list.add_item(
            text, priority=Priority[priority.upper()], tags=list(tags)
        )
        for text in texts
    ]

    # resort before reading ids back: reindex can renumber the new items.
    task_list.resort(Sort.from_default_sort(config.default_sort))

    result = CommandResult(item_view=task_list)
    for item in added:
        result.messages.append(f"added #{item.id} to '{display_name}'.")

    save_list(storage_dir, task_list)

    return result


def set_list_color(name: str, color: str, config: Config) -> CommandResult:
    """Recolor an existing list.

    Parameters
    ----------
    name : str
        The list to recolor.
    color : str
        Color name (lower-cased).
    config : Config
        The active config, for the display name.

    Returns
    -------
    CommandResult
        The status message plus the list as the item view.
    """

    def mutate_fn(task_list: TaskliList) -> str:
        task_list.set_color(Color[color.upper()])
        display_name = task_list.display_name(config.sublist_delimiter)

        return f"updated color of '{display_name}' to '{color}'."

    return _mutate(name, mutate_fn)


def edit(
    list_name: str,
    item_id: int,
    text: str | None,
    priority: str | None,
    tags: list[str],
    add_tag: list[str],
    config: Config,
) -> CommandResult:
    """Edit an item's text, priority, or tags.

    Parameters
    ----------
    list_name : str
        The list holding the item.
    item_id : int
        The item to edit.
    text : str | None
        Replacement text, or None to leave unchanged.
    priority : str | None
        Replacement priority name, or None to leave unchanged.
    tags : list[str]
        Replacement tag list, or empty to leave unchanged.
    add_tag : list[str]
        Tags to append to the item's existing tags.
    config : Config
        The active config, for the display name.

    Returns
    -------
    CommandResult
        The status message plus the list as the item view.
    """

    def mutate_fn(task_list: TaskliList) -> str:
        task_list.edit_item(
            item_id,
            text=text,
            priority=Priority[priority.upper()] if priority else None,
            tags=list(tags) if tags else None,
        )
        if add_tag:
            task_list.add_tags(item_id, add_tag)

        display_name = task_list.display_name(config.sublist_delimiter)

        return f"updated #{item_id} in '{display_name}'."

    return _mutate(list_name, mutate_fn)


def mark_done(
    list_name: str, item_ids: list[int], config: Config
) -> CommandResult:
    """Mark one or more items done, tolerating missing ids.

    Parameters
    ----------
    list_name : str
        The list holding the items.
    item_ids : list[int]
        Ids to mark done.
    config : Config
        The active config, for the display name.

    Returns
    -------
    CommandResult
        One message per marked id, one warning per missing id.
    """

    return _batch_mark(
        list_name, item_ids, config, TaskliList.mark_done_ref, "done"
    )


def mark_undone(
    list_name: str, item_ids: list[int], config: Config
) -> CommandResult:
    """Mark one or more items not done, tolerating missing ids.

    Parameters
    ----------
    list_name : str
        The list holding the items.
    item_ids : list[int]
        Ids to mark not done.
    config : Config
        The active config, for the display name.

    Returns
    -------
    CommandResult
        One message per marked id, one warning per missing id.
    """

    return _batch_mark(
        list_name, item_ids, config, TaskliList.mark_undone_ref, "not done"
    )


def mark_in_progress(
    list_name: str, item_ids: list[int], config: Config
) -> CommandResult:
    """Mark one or more items in progress, tolerating missing ids.

    Parameters
    ----------
    list_name : str
        The list holding the items.
    item_ids : list[int]
        Ids to mark in progress.
    config : Config
        The active config, for the display name.

    Returns
    -------
    CommandResult
        One message per marked id, one warning per missing id.
    """

    return _batch_mark(
        list_name,
        item_ids,
        config,
        TaskliList.mark_in_progress_ref,
        "in progress",
    )


def _resolve_items(
    task_list: TaskliList, item_ids: list[int]
) -> tuple[list[tuple[int, TaskliItem]], list[str]]:
    """Resolve ids to items once, deduped by identity, with per-id warnings."""

    resolved: list[tuple[int, TaskliItem]] = []
    seen: set[int] = set()
    warnings: list[str] = []
    for item_id in item_ids:
        try:
            item = task_list.get_item(item_id)
        except ItemNotFoundError as e:
            warnings.append(str(e))
            continue
        if id(item) in seen:
            continue
        seen.add(id(item))
        resolved.append((item_id, item))

    return resolved, warnings


def _batch_mark(
    list_name: str,
    item_ids: list[int],
    config: Config,
    mark: Callable[[TaskliList, TaskliItem], object],
    label: str,
) -> CommandResult:
    """Apply ``mark`` to each resolved item, collecting messages/warnings."""

    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    display_name = task_list.display_name(config.sublist_delimiter)

    result = CommandResult()
    resolved, result.warnings = _resolve_items(task_list, item_ids)
    for item_id, item in resolved:
        mark(task_list, item)
        result.messages.append(
            f"marked #{item_id} {label} in '{display_name}'."
        )

    save_list(storage_dir, task_list)
    result.item_view = task_list
    result.exit_code = 1 if result.warnings else 0

    return result


def remove_items(
    list_name: str, item_ids: list[int], config: Config
) -> CommandResult:
    """Remove one or more items, tolerating missing ids.

    Parameters
    ----------
    list_name : str
        The list holding the items.
    item_ids : list[int]
        Ids to remove.
    config : Config
        The active config, for the display name.

    Returns
    -------
    CommandResult
        One message per removed id, one warning per missing id.
    """

    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    display_name = task_list.display_name(config.sublist_delimiter)

    result = CommandResult()
    resolved, result.warnings = _resolve_items(task_list, item_ids)
    for item_id, item in resolved:
        task_list.remove_item_ref(item)
        result.messages.append(f"removed #{item_id} from '{display_name}'.")

    save_list(storage_dir, task_list)
    result.item_view = task_list
    result.exit_code = 1 if result.warnings else 0

    return result


def move(
    list_name: str,
    target_name: str,
    item_ids: list[int],
    config: Config,
) -> CommandResult:
    """Move items from one list to another, tolerating missing ids.

    Parameters
    ----------
    list_name : str
        The source list.
    target_name : str
        The destination list, created if missing.
    item_ids : list[int]
        Ids to move; empty moves every item in the source.
    config : Config
        The active config, for display names and default sort.

    Returns
    -------
    CommandResult
        One message per moved id, one warning per missing id, plus the
        target list as the item view.
    """

    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    target_list = load_or_create_list(storage_dir, target_name)
    display_name = task_list.display_name(config.sublist_delimiter)
    target_display_name = target_list.display_name(config.sublist_delimiter)

    ids = item_ids or [item.id for item in task_list.items]

    result = CommandResult()
    resolved, result.warnings = _resolve_items(task_list, ids)
    for item_id, item in resolved:
        task_list.move_item_ref(item, target_list)
        result.messages.append(
            f"moved #{item_id} from '{display_name}' to "
            f"'{target_display_name}'."
        )

    target_list.resort(Sort.from_default_sort(config.default_sort))

    save_list(storage_dir, task_list)
    save_list(storage_dir, target_list)
    result.item_view = target_list
    result.exit_code = 1 if result.warnings else 0

    return result


def copy(
    list_name: str,
    target_name: str,
    item_ids: list[int],
    config: Config,
) -> CommandResult:
    """Copy items from one list to another, tolerating missing ids.

    Parameters
    ----------
    list_name : str
        The source list.
    target_name : str
        The destination list, created if missing.
    item_ids : list[int]
        Ids to copy; empty copies every item in the source.
    config : Config
        The active config, for display names and default sort.

    Returns
    -------
    CommandResult
        One message per copied id, one warning per missing id, plus the
        target list as the item view.
    """

    storage_dir = resolve_storage_dir()
    task_list = load_list(storage_dir, list_name)
    target_list = load_or_create_list(storage_dir, target_name)
    display_name = task_list.display_name(config.sublist_delimiter)
    target_display_name = target_list.display_name(config.sublist_delimiter)

    ids = item_ids or [item.id for item in task_list.items]

    result = CommandResult()
    resolved, result.warnings = _resolve_items(task_list, ids)
    for item_id, item in resolved:
        task_list.copy_item_ref(item, target_list)
        result.messages.append(
            f"copied #{item_id} from '{display_name}' to "
            f"'{target_display_name}'."
        )

    target_list.resort(Sort.from_default_sort(config.default_sort))

    save_list(storage_dir, target_list)
    result.item_view = target_list
    result.exit_code = 1 if result.warnings else 0

    return result


def prune(
    list_name: str,
    prune_all: bool,
    target_given: bool,
    config: Config,
) -> CommandResult:
    """Remove done items from one or more lists.

    Parameters
    ----------
    list_name : str
        The primary list to prune.
    prune_all : bool
        When true, also prune descendants (with a target) or every list
        on disk (without one).
    target_given : bool
        Whether an explicit list name was passed on the command line.
    config : Config
        The active config, for display names.

    Returns
    -------
    CommandResult
        One message per pruned list plus every pruned list as the tree
        view.
    """

    storage_dir = resolve_storage_dir()

    lists: list[TaskliList] = [load_list(storage_dir, list_name)]
    if prune_all:
        all_lists = list_all_lists(storage_dir)
        if target_given:
            names = descendant_list_names(list_name, all_lists)
        else:
            names = all_lists
        lists.extend(load_list(storage_dir, name) for name in names)

    result = CommandResult(tree_view=lists)
    for task_list in lists:
        removed = task_list.prune()
        save_list(storage_dir, task_list)

        display_name = task_list.display_name(config.sublist_delimiter)
        result.messages.append(
            f"pruned {len(removed)} item(s) from '{display_name}'."
        )

    return result


def new_list(name: str, color: str | None, config: Config) -> CommandResult:
    """Create and persist a new, empty list.

    Parameters
    ----------
    name : str
        The new list's name.
    color : str | None
        Color name (lower-cased), or None to use the config default.
    config : Config
        The active config, for the default color and display name.

    Returns
    -------
    CommandResult
        The status message plus the new list as the item view.
    """

    storage_dir = resolve_storage_dir()
    resolved_color = Color[color.upper()] if color else config.default_color

    task_list = create_list(storage_dir, name, color=resolved_color)
    display_name = task_list.display_name(config.sublist_delimiter)

    return CommandResult(
        messages=[f"created list '{display_name}'."], item_view=task_list
    )


def rename(old_name: str, new_name: str, config: Config) -> CommandResult:
    """Rename a list and its descendants, following the default list.

    Parameters
    ----------
    old_name : str
        The list's current name.
    new_name : str
        The list's new name.
    config : Config
        The active config; its ``default_list`` is updated and saved if it
        pointed at a renamed list.

    Returns
    -------
    CommandResult
        A single status message.
    """

    storage_dir = resolve_storage_dir()
    old_display = TaskliList(name=old_name).display_name(
        config.sublist_delimiter
    )
    new_display = TaskliList(name=new_name).display_name(
        config.sublist_delimiter
    )

    renamed = rename_list(storage_dir, old_name, new_name)

    if not renamed:
        return CommandResult(
            messages=[f"'{old_display}' is already named '{old_display}'."]
        )

    if len(renamed) > 1:
        message = (
            f"renamed '{old_display}' to '{new_display}' and "
            f"{len(renamed) - 1} sublist(s)."
        )
    else:
        message = f"renamed '{old_display}' to '{new_display}'."

    canonical_default = config.default_list.replace(
        config.sublist_delimiter, "."
    )
    for old, new in renamed:
        if canonical_default == old:
            config.default_list = new.replace(".", config.sublist_delimiter)
            save_config(storage_dir, config)
            break

    return CommandResult(messages=[message])


def delete_prompt(name: str, config: Config) -> str:
    """Build the confirmation prompt for deleting a list.

    Parameters
    ----------
    name : str
        The list to be deleted.
    config : Config
        The active config, for display names.

    Returns
    -------
    str
        The prompt text, naming any descendant lists that would also go.
    """

    storage_dir = resolve_storage_dir()
    descendants = descendant_list_names(name, list_all_lists(storage_dir))
    display_name = TaskliList(name=name).display_name(config.sublist_delimiter)

    if not descendants:
        return f"delete list '{display_name}' and all its items?"

    display_descendants = [
        TaskliList(name=d).display_name(config.sublist_delimiter)
        for d in descendants
    ]

    return (
        f"delete list '{display_name}' and its {len(descendants)} "
        f"sublist(s) ({', '.join(display_descendants)}) and all "
        "their items?"
    )


def delete_confirmed(name: str, config: Config) -> CommandResult:
    """Delete a list and its descendants after confirmation.

    Parameters
    ----------
    name : str
        The list to delete.
    config : Config
        The active config, for the display name.

    Returns
    -------
    CommandResult
        A single status message; no list view (the list is gone).
    """

    storage_dir = resolve_storage_dir()
    display_name = TaskliList(name=name).display_name(config.sublist_delimiter)

    deleted_descendants = delete_list(storage_dir, name)

    if deleted_descendants:
        message = (
            f"deleted list '{display_name}' and "
            f"{len(deleted_descendants)} sublist(s)."
        )
    else:
        message = f"deleted list '{display_name}'."

    return CommandResult(messages=[message])


def set_config(key: str, value: str) -> CommandResult:
    """Set a config value, resorting every list if the sort changed.

    Parameters
    ----------
    key : str
        The config key to set.
    value : str
        The new value.

    Returns
    -------
    CommandResult
        A single status message.
    """

    storage_dir = resolve_storage_dir()
    config = load_config(storage_dir)

    config.set_value(key, value)
    save_config(storage_dir, config)

    if key == "default_sort":
        resort_all_lists(
            storage_dir, Sort.from_default_sort(config.default_sort)
        )

    return CommandResult(messages=[f"set '{key}' to '{value}'."])


def migrate() -> CommandResult:
    """Bring every on-disk list and config file up to the current schema.

    Returns
    -------
    CommandResult
        One message per migrated or already-current file, one warning per
        file whose JSON could not be read; ``exit_code`` is 1 when any
        file was unreadable.
    """

    result = CommandResult()
    for name, outcome in migrate_all(resolve_storage_dir()):
        if outcome == "migrated":
            result.messages.append(f"migrated '{name}'.")
        elif outcome == "current":
            result.messages.append(f"'{name}' already current.")
        else:
            result.warnings.append(f"could not read '{name}'; skipped.")

    result.exit_code = 1 if result.warnings else 0

    return result


def list_names() -> list[str]:
    """Return every list name currently on disk.

    Returns
    -------
    list[str]
        Sorted list names.
    """

    return list_all_lists(resolve_storage_dir())


def list_entries() -> list[tuple[str, Color | None]]:
    """Return every list name paired with its color.

    Returns
    -------
    list[tuple[str, Color | None]]
        (name, color) for every list on disk, color None if the file
        fails to load.
    """

    storage_dir = resolve_storage_dir()

    entries: list[tuple[str, Color | None]] = []
    for name in list_all_lists(storage_dir):
        try:
            entries.append((name, load_list(storage_dir, name).color))
        except TaskliError:
            entries.append((name, None))

    return entries


def has_any_lists() -> bool:
    """Return whether any list exists on disk.

    Returns
    -------
    bool
        True if at least one list file is present.
    """

    return bool(list_all_lists(resolve_storage_dir()))


def _grouped_lists(
    storage_dir: Path,
    list_name: str,
    all_names: list[str],
    item_filter: Filter,
    config: Config,
) -> list[TaskliList]:
    """Build filtered views of a list and (optionally) its descendants."""

    task_list = load_list(storage_dir, list_name)
    if config.auto_prune and task_list.prune():
        save_list(storage_dir, task_list)

    lists = [
        TaskliList(
            name=list_name,
            color=task_list.color,
            items=task_list.filtered_items(item_filter),
        )
    ]

    # filter each descendant list by the same criteria given to the parent.
    for descendant_name in descendant_list_names(list_name, all_names):
        descendant_list = load_list(storage_dir, descendant_name)
        if config.auto_prune and descendant_list.prune():
            save_list(storage_dir, descendant_list)

        lists.append(
            TaskliList(
                name=descendant_name,
                color=descendant_list.color,
                items=descendant_list.filtered_items(item_filter),
            )
        )

    return lists


def _drop_unmatched_lists(lists: list[TaskliList]) -> list[TaskliList]:
    """Drop empty lists, keeping in-group ancestors of any non-empty one.

    Ancestor retention only sees names present in ``lists``, so callers
    must pass a full group (as ``_grouped_lists`` builds it).
    """

    present = {tl.name for tl in lists}
    keep: set[str] = set()
    for tl in lists:
        if tl.items:
            keep.add(tl.name)
            # keep the empty ancestors too, so render_list_tree can still
            # parent this list under its chain.
            keep.update(a for a in ancestor_chain(tl.name) if a in present)

    return [tl for tl in lists if tl.name in keep]


def list_view(
    list_name: str,
    item_filter: Filter,
    include_descendants: bool,
) -> list[TaskliList]:
    """Return the filtered tree view for a single list.

    Parameters
    ----------
    list_name : str
        The list to view.
    item_filter : Filter
        The criteria to filter items by; empty matches everything.
    include_descendants : bool
        Whether to include descendant lists in the view.

    Returns
    -------
    list[TaskliList]
        The list, then any descendants, each filtered. When descendants
        are included and a filter is active, lists left empty by the
        filter are dropped (ancestors of a kept list are retained for
        tree connectivity); an all-empty result is ``[]``.
    """

    storage_dir = resolve_storage_dir()
    config = load_config(storage_dir)
    all_names = list_all_lists(storage_dir) if include_descendants else []

    groups = _grouped_lists(
        storage_dir, list_name, all_names, item_filter, config
    )
    if include_descendants and item_filter.active:
        return _drop_unmatched_lists(groups)

    return groups


def all_views(item_filter: Filter) -> list[list[TaskliList]]:
    """Return one filtered tree view per root list on disk.

    Parameters
    ----------
    item_filter : Filter
        The criteria to filter items by; empty matches everything.

    Returns
    -------
    list[list[TaskliList]]
        One group per root list. With a filter active, groups left with
        no surviving lists are omitted, so the result may be shorter
        than the number of roots (or empty); empty too when no lists
        exist.
    """

    storage_dir = resolve_storage_dir()
    config = load_config(storage_dir)
    all_names = list_all_lists(storage_dir)

    roots = [name for name in all_names if "." not in name]

    groups = [
        _grouped_lists(storage_dir, root, all_names, item_filter, config)
        for root in roots
    ]
    if item_filter.active:
        kept: list[list[TaskliList]] = []
        for group in groups:
            pruned = _drop_unmatched_lists(group)
            if pruned:
                kept.append(pruned)

        return kept

    return groups
