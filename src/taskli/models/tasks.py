"""Tasks & task list models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator

from ..exceptions import ItemNotFoundError
from . import registry
from .attributes import Color, Priority, Status
from .paths import path_key
from .query import Filter, Sort

__all__ = ["TaskliItem", "TaskliList", "walk_items"]


class TaskliItem(BaseModel):
    id: str
    text: str
    status: Status = Status.TODO
    priority: Priority = Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    modified_at: datetime | None = None
    completed_at: datetime | None = None
    due_date: datetime | None = None
    description: str | None = None
    children: list["TaskliItem"] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        path_key(value)  # rejects a non-numeric or empty segment.

        return value

    @field_serializer("status")
    def _serialize_status(self, value: Status) -> str:
        return value.label

    @field_serializer("priority")
    def _serialize_priority(self, value: Priority) -> str:
        return value.label

    @property
    def done(self) -> bool:
        """Whether the item's status is ``Status.DONE``.

        Returns
        -------
        bool
            True if the item is done.
        """

        return self.status == Status.DONE


TaskliItem.model_rebuild()


def walk_items(items: list[TaskliItem]) -> list[TaskliItem]:
    """Flatten an item forest to pre-order DFS.

    Parameters
    ----------
    items : list[TaskliItem]
        The top-level items to walk.

    Returns
    -------
    list[TaskliItem]
        Every item in the forest, each parent before its own children
        and siblings in list order.
    """

    flat: list[TaskliItem] = []
    for item in items:
        flat.append(item)
        flat.extend(walk_items(item.children))

    return flat


def _reindex(items: list[TaskliItem], prefix: str = "") -> None:
    """Renumber a sibling group and its descendants positionally."""

    for position, item in enumerate(items, start=1):
        item.id = f"{prefix}{position}"
        _reindex(item.children, f"{item.id}.")


def _sort_tree(items: list[TaskliItem], sort: Sort) -> list[TaskliItem]:
    """Sort a sibling group by ``sort``, then recurse into children."""

    ordered = sorted(items, key=sort.key, reverse=sort.descending)
    for item in ordered:
        item.children = _sort_tree(item.children, sort)

    return ordered


def _sort_tree_by_path(items: list[TaskliItem]) -> list[TaskliItem]:
    """Reorder a sibling group ascending by path key, recursively."""

    ordered = sorted(items, key=lambda item: path_key(item.id))
    for item in ordered:
        item.children = _sort_tree_by_path(item.children)

    return ordered


def _find_container(
    items: list[TaskliItem], target: TaskliItem
) -> list[TaskliItem] | None:
    """Return the sibling list holding ``target`` by identity, or None."""

    if any(item is target for item in items):
        return items
    for item in items:
        found = _find_container(item.children, target)
        if found is not None:
            return found

    return None


def _prune_tree(
    items: list[TaskliItem],
) -> tuple[list[TaskliItem], list[TaskliItem]]:
    """Drop fully-done subtrees bottom-up; return (survivors, removed)."""

    survivors: list[TaskliItem] = []
    removed: list[TaskliItem] = []
    for item in items:
        kept_children, child_removed = _prune_tree(item.children)
        item.children = kept_children
        removed.extend(child_removed)
        if item.done and not item.children:
            removed.append(item)
        else:
            survivors.append(item)

    return survivors, removed


def _filter_tree(
    items: list[TaskliItem], item_filter: Filter
) -> list[TaskliItem]:
    """Copy items that match ``item_filter`` or have a kept child.

    Each kept item is a fresh copy with its mutable state (``tags``,
    ``children``) replaced, so the returned forest never aliases the
    originals.
    """

    kept: list[TaskliItem] = []
    for item in items:
        kept_children = _filter_tree(item.children, item_filter)
        if item_filter.matches(item) or kept_children:
            narrowed = item.model_copy(
                update={"children": kept_children, "tags": list(item.tags)}
            )
            kept.append(narrowed)

    return kept


def _copy_subtree(src: TaskliItem, dest_item: TaskliItem) -> None:
    """Recursively copy ``src``'s children into ``dest_item``'s subtree."""

    now = datetime.now()
    for child in src.children:
        attrs: dict[str, Any] = {
            name: getattr(child, name) for name in registry.modifiable("add")
        }
        attrs["tags"] = list(child.tags)  # own list object per copy.
        new_child = TaskliItem(
            id=f"{dest_item.id}.{len(dest_item.children) + 1}",
            text=child.text,
            created_at=child.created_at,
            modified_at=now,
            **attrs,
        )
        dest_item.children.append(new_child)
        _copy_subtree(child, new_child)


class TaskliList(BaseModel):
    name: str
    color: Color | None = Color.WHITE
    items: list[TaskliItem] = Field(default_factory=list)
    # a filtered (deep-copied) view storage.save_list must refuse to write.
    view_only: bool = Field(default=False, exclude=True)

    def display_name(self, delimiter: str = ".") -> str:
        """Render the name with sublist segments joined by ``delimiter``.

        Parameters
        ----------
        delimiter : str, optional
            Delimiter to substitute for the storage-form ".", by default
            ".".

        Returns
        -------
        str
            The name in display form.
        """

        return self.name.replace(".", delimiter)

    def sort_by(self, sort: Sort) -> None:
        """Sort ``items`` in place under ``sort``.

        Every item's ``children`` are sorted the same way, recursively.

        Parameters
        ----------
        sort : Sort
            The sort mode to apply.
        """

        self.items = _sort_tree(self.items, sort)

        return None

    def set_color(self, color: Color) -> None:
        """Set the list's display color.

        Parameters
        ----------
        color : Color
            The new color.
        """

        self.color = color

        return None

    def reindex(self) -> None:
        """Renumber items to their positional dotted paths.

        Top-level items become ``"1"``, ``"2"``, ...; a child of
        ``"1"`` becomes ``"1.1"``, ``"1.2"``, ...; recursively. Ids are
        mutated in place so held references survive.
        """

        _reindex(self.items)

        return None

    def sort_by_index(self) -> None:
        """Reorder each sibling group ascending by its current path."""

        self.items = _sort_tree_by_path(self.items)

        return None

    def resort(self, sort: Sort) -> None:
        """Sort ``items`` by ``sort``, then reindex to match the new order.

        Parameters
        ----------
        sort : Sort
            The sort mode to apply.
        """

        self.sort_by(sort)
        self.reindex()

        return None

    def add_item(
        self,
        text: str,
        attrs: dict[str, Any] | None = None,
        *,
        created_at: datetime | None = None,
        modified_at: datetime | None = None,
        parent_path: str | None = None,
    ) -> TaskliItem:
        """Create and append a new item, returning it.

        Parameters
        ----------
        text : str
            The item's description.
        attrs : dict[str, Any] | None, optional
            Typed field values keyed by pydantic field name (e.g.
            ``{"priority": Priority.HIGH, "tags": ["x"]}``). Present
            keys are validated and absent ones defaulted by the
            ``TaskliItem`` constructor. By default none.
        created_at : datetime | None, optional
            Creation timestamp, by default ``datetime.now()``. Set by
            ``copy_item`` to preserve the source item's timestamp.
        modified_at : datetime | None, optional
            Last-modified timestamp, by default the resolved
            ``created_at``. Set by ``copy_item`` to the time of copy.
        parent_path : str | None, optional
            The dotted path of an existing item to nest the new item
            under. By default none, appending at the top level. The
            provisional child id is finalised by a later
            ``resort``/``reindex``.

        Returns
        -------
        TaskliItem
            The newly created item.
        """

        resolved_created_at = created_at or datetime.now()
        if parent_path is None:
            new_id = str(len(self.items) + 1)
            container = self.items
        else:
            parent = self.get_item(parent_path)
            new_id = f"{parent.id}.{len(parent.children) + 1}"
            container = parent.children
        item = TaskliItem(
            id=new_id,
            text=text,
            created_at=resolved_created_at,
            modified_at=modified_at or resolved_created_at,
            **(attrs or {}),
        )
        container.append(item)

        return item

    def get_item(self, item_id: str | int) -> TaskliItem:
        """Return the item anywhere in the tree with the given id.

        Parameters
        ----------
        item_id : str | int
            The item's dotted path; an ``int`` is normalised to its
            string form for legacy call sites.

        Returns
        -------
        TaskliItem
            The matching item.
        """

        path = str(item_id)
        try:
            return next(
                item for item in walk_items(self.items) if item.id == path
            )
        except StopIteration as e:
            raise ItemNotFoundError(
                f"no item with id {item_id} in list '{self.name}'."
            ) from e

    def mark_done_ref(self, item: TaskliItem) -> TaskliItem:
        """Mark a resolved item done and set its completion timestamp.

        Parameters
        ----------
        item : TaskliItem
            The item to mark done.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        now = datetime.now()
        item.status = Status.DONE
        item.completed_at = now
        item.modified_at = now

        return item

    def mark_done(self, item_id: str | int) -> TaskliItem:
        """Mark an item done and set its completion timestamp.

        Parameters
        ----------
        item_id : str | int
            The item's id.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        return self.mark_done_ref(self.get_item(item_id))

    def mark_undone_ref(self, item: TaskliItem) -> TaskliItem:
        """Reset a resolved item to todo and clear its completion timestamp.

        Resets from either ``Status.DONE`` or ``Status.IN_PROGRESS``.

        Parameters
        ----------
        item : TaskliItem
            The item to reset.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        item.status = Status.TODO
        item.completed_at = None
        item.modified_at = datetime.now()

        return item

    def mark_undone(self, item_id: str | int) -> TaskliItem:
        """Reset an item to todo and clear its completion timestamp.

        Resets from either ``Status.DONE`` or ``Status.IN_PROGRESS``.

        Parameters
        ----------
        item_id : str | int
            The item's id.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        return self.mark_undone_ref(self.get_item(item_id))

    def mark_in_progress_ref(self, item: TaskliItem) -> TaskliItem:
        """Mark a resolved item in progress; clear its completion timestamp.

        Parameters
        ----------
        item : TaskliItem
            The item to mark in progress.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        item.status = Status.IN_PROGRESS
        item.completed_at = None
        item.modified_at = datetime.now()

        return item

    def mark_in_progress(self, item_id: str | int) -> TaskliItem:
        """Mark an item in progress and clear its completion timestamp.

        Parameters
        ----------
        item_id : str | int
            The item's id.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        return self.mark_in_progress_ref(self.get_item(item_id))

    def remove_item_ref(self, item: TaskliItem) -> None:
        """Remove a resolved item and its subtree, then reindex.

        Parameters
        ----------
        item : TaskliItem
            The item to remove; its children travel with it.
        """

        container = _find_container(self.items, item)
        if container is None:
            raise ValueError("item is not in the list.")
        container[:] = [
            existing for existing in container if existing is not item
        ]
        self.reindex()

    def remove_item(self, item_id: str | int) -> None:
        """Remove an item and its subtree from the list.

        Parameters
        ----------
        item_id : str | int
            The item's id.
        """

        self.remove_item_ref(self.get_item(item_id))

    def prune(self) -> list[TaskliItem]:
        """Remove every item whose entire subtree is done.

        A done item is kept when it still has a surviving un-done
        descendant; done leaves are always removed.

        Returns
        -------
        list[TaskliItem]
            Every removed item, as one flat list.
        """

        survivors, removed = _prune_tree(self.items)
        self.items = survivors
        self.reindex()

        return removed

    def edit_item(
        self, item_id: str | int, attrs: dict[str, object]
    ) -> TaskliItem:
        """Apply a mapping of typed field values to an existing item.

        Assignment is a bare ``setattr`` with no pydantic validation
        (``TaskliItem`` has no ``validate_assignment``); callers are
        responsible for passing already-valid typed values.

        Parameters
        ----------
        item_id : str | int
            The item's id.
        attrs : dict[str, object]
            Field values keyed by pydantic field name. An empty
            mapping is a no-op and leaves ``modified_at`` untouched.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        item = self.get_item(item_id)
        for name, value in attrs.items():
            setattr(item, name, value)
        if attrs:
            item.modified_at = datetime.now()

        return item

    def filtered_items(self, item_filter: Filter) -> list[TaskliItem]:
        """Return a forest of fresh copies narrowed to matching subtrees.

        An item is kept when it matches ``item_filter`` or any of its
        descendants does. Each kept item is a copy with its mutable state
        replaced, so the originals are left untouched -- these views are
        for rendering only and must never be persisted.

        Parameters
        ----------
        item_filter : Filter
            The filter to apply; an empty filter keeps every item.

        Returns
        -------
        list[TaskliItem]
            The matching items as independent copies.
        """

        return _filter_tree(self.items, item_filter)

    def add_tags(self, item_id: str | int, tags: list[str]) -> TaskliItem:
        """Append new tags to an item's existing tags, deduplicated.

        Parameters
        ----------
        item_id : str | int
            The item's id.
        tags : list[str]
            Tags to add, in addition to any the item already has.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        item = self.get_item(item_id)
        item.tags = item.tags + [t for t in tags if t not in item.tags]
        item.modified_at = datetime.now()

        return item

    def copy_item_ref(
        self, item: TaskliItem, target: "TaskliList"
    ) -> TaskliItem:
        """Copy a resolved item and its subtree into another list.

        The copied root keeps the source item's ``created_at``; only
        ``modified_at`` is stamped with the time of copy. Descendants
        are recreated as fresh items with their status reset to the
        ``TaskliItem`` default.

        Parameters
        ----------
        item : TaskliItem
            The item to copy.
        target : TaskliList
            The list to copy the item into.

        Returns
        -------
        TaskliItem
            The newly created root item in ``target``.
        """

        # the add-settable attributes are exactly the ones a copy should
        # carry today; test_add_modifiers_in_column_order pins the set.
        attrs: dict[str, Any] = {
            name: getattr(item, name) for name in registry.modifiable("add")
        }
        attrs["tags"] = list(item.tags)  # own list object per copy.

        new_item = target.add_item(
            item.text,
            attrs,
            created_at=item.created_at,
            modified_at=datetime.now(),
        )
        _copy_subtree(item, new_item)

        return new_item

    def copy_item(
        self, item_id: str | int, target: "TaskliList"
    ) -> TaskliItem:
        """Copy an item and its subtree into another list.

        The copied root keeps the source item's ``created_at``; only
        ``modified_at`` is stamped with the time of copy.

        Parameters
        ----------
        item_id : str | int
            The item's id in ``self``.
        target : TaskliList
            The list to copy the item into.

        Returns
        -------
        TaskliItem
            The newly created root item in ``target``.
        """

        return self.copy_item_ref(self.get_item(item_id), target)

    def move_item_ref(
        self, item: TaskliItem, target: "TaskliList"
    ) -> TaskliItem:
        """Move a resolved item into another list, removing it from ``self``.

        Parameters
        ----------
        item : TaskliItem
            The item to move; its subtree travels with it.
        target : TaskliList
            The list to move the item into.

        Returns
        -------
        TaskliItem
            The newly created root item in ``target``.
        """

        moved = self.copy_item_ref(item, target)
        self.remove_item_ref(item)

        return moved

    def move_item(
        self, item_id: str | int, target: "TaskliList"
    ) -> TaskliItem:
        """Move an item into another list, removing it from ``self``.

        Parameters
        ----------
        item_id : str | int
            The item's id in ``self``.
        target : TaskliList
            The list to move the item into.

        Returns
        -------
        TaskliItem
            The newly created root item in ``target``.
        """

        return self.move_item_ref(self.get_item(item_id), target)
