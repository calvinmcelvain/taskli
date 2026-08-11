"""Tasks & task list models."""

from datetime import datetime

from pydantic import BaseModel, Field

from ..exceptions import ItemNotFoundError
from .attributes import Color, Priority
from .config import SortBy

__all__ = ["TaskliItem", "TaskliList"]


class TaskliItem(BaseModel):
    """Single task entry within a list."""

    id: int
    text: str
    done: bool = False
    priority: Priority = Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None


class TaskliList(BaseModel):
    """A named collection of tasks."""

    name: str
    color: Color | None = Color.WHITE
    items: list[TaskliItem] = Field(default_factory=list)

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

    def sort_by(self, sort: SortBy) -> None:
        """Sort ``items`` list by attributes.

        Parameters
        ----------
        sort : SortBy
            The attribute to sort by.
        """

        if sort == "tags":
            self.items = sorted(
                self.items,
                key=lambda item: (
                    "".join(item.tags) == "",
                    ",".join(sorted(item.tags)),
                ),
            )
        elif sort == "priority":
            self.items = sorted(
                self.items, key=lambda item: item.priority.index, reverse=True
            )
        else:
            self.items = sorted(
                self.items, key=lambda item: getattr(item, sort)
            )

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
        """Renumber remaining items sequentially starting at 1."""

        for new_id, item in enumerate(self.items, start=1):
            item.id = new_id

        return None

    def sort_by_index(self) -> None:
        """Reorder ``items`` ascending by their current ``id``."""

        self.items = sorted(self.items, key=lambda item: item.id)

        return None

    def resort(self, sort: SortBy) -> None:
        """Sort ``items`` by ``sort``, then reindex to match the new order.

        Parameters
        ----------
        sort : SortBy
            The attribute to sort by.
        """

        self.sort_by(sort)
        self.reindex()

        return None

    def add_item(
        self,
        text: str,
        *,
        priority: Priority = Priority.MEDIUM,
        tags: list[str] | None = None,
    ) -> TaskliItem:
        """Create and append a new item, returning it.

        Parameters
        ----------
        text : str
            The item's description.
        priority : Priority, optional
            Urgency level, by default ``Priority.MEDIUM``.
        tags : list[str] | None, optional
            Tags to attach, by default none.

        Returns
        -------
        TaskliItem
            The newly created item.
        """

        idx = len(self.items) + 1
        item = TaskliItem(
            id=idx,
            text=text,
            priority=priority,
            tags=tags or [],
            created_at=datetime.now(),
        )
        self.items.append(item)

        return item

    def get_item(self, item_id: int) -> TaskliItem:
        """Return the item with the given id.

        Parameters
        ----------
        item_id : int
            The item's id.

        Returns
        -------
        TaskliItem
            The matching item.
        """

        try:
            return next(item for item in self.items if item.id == item_id)
        except StopIteration as e:
            raise ItemNotFoundError(
                f"no item with id {item_id} in list '{self.name}'."
            ) from e

    def mark_done(self, item_id: int) -> TaskliItem:
        """Mark an item done and set its completion timestamp.

        Parameters
        ----------
        item_id : int
            The item's id.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        item = self.get_item(item_id)
        item.done = True
        item.completed_at = datetime.now()

        return item

    def mark_undone(self, item_id: int) -> TaskliItem:
        """Mark an item not done and clear its completion timestamp.

        Parameters
        ----------
        item_id : int
            The item's id.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        item = self.get_item(item_id)
        item.done = False
        item.completed_at = None

        return item

    def remove_item(self, item_id: int) -> None:
        """Remove an item from the list.

        Parameters
        ----------
        item_id : int
            The item's id.
        """

        item = self.get_item(item_id)
        self.items.remove(item)
        self.reindex()

    def prune(self) -> list[TaskliItem]:
        """Remove all done items from the list.

        Returns
        -------
        list[TaskliItem]
            The items that were removed.
        """

        removed = [item for item in self.items if item.done]
        self.items = [item for item in self.items if not item.done]
        self.reindex()

        return removed

    def edit_item(
        self,
        item_id: int,
        *,
        text: str | None = None,
        priority: Priority | None = None,
        tags: list[str] | None = None,
    ) -> TaskliItem:
        """Update the given fields of an existing item.

        Parameters
        ----------
        item_id : int
            The item's id.
        text : str | None, optional
            New description, if changing.
        priority : Priority | None, optional
            New priority, if changing.
        tags : list[str] | None, optional
            New tags, if changing.

        Returns
        -------
        TaskliItem
            The updated item.
        """

        item = self.get_item(item_id)
        if text is not None:
            item.text = text
        if priority is not None:
            item.priority = priority
        if tags is not None:
            item.tags = tags

        return item

    def filtered_items(
        self,
        *,
        tag: str | None = None,
        priority: Priority | None = None,
    ) -> list[TaskliItem]:
        """Return items, optionally filtered by tag and/or priority.

        Parameters
        ----------
        tag : str | None, optional
            Tag to filter by (case-insensitive), by default no filtering.
        priority : Priority | None, optional
            Priority to filter by, by default no filtering.

        Returns
        -------
        list[TaskliItem]
            The matching items.
        """

        items = list(self.items)
        if tag is not None:
            needle = tag.lower()
            items = [
                item
                for item in items
                if needle in (t.lower() for t in item.tags)
            ]
        if priority is not None:
            items = [item for item in items if item.priority == priority]

        return items

    def add_tags(self, item_id: int, tags: list[str]) -> TaskliItem:
        """Append new tags to an item's existing tags, deduplicated.

        Parameters
        ----------
        item_id : int
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

        return item

    def copy_item(self, item_id: int, target: "TaskliList") -> TaskliItem:
        """Copy an item into another list as a fresh, undone item.

        Parameters
        ----------
        item_id : int
            The item's id in ``self``.
        target : TaskliList
            The list to copy the item into.

        Returns
        -------
        TaskliItem
            The newly created item in ``target``.
        """

        item = self.get_item(item_id)

        return target.add_item(
            item.text, priority=item.priority, tags=list(item.tags)
        )

    def move_item(self, item_id: int, target: "TaskliList") -> TaskliItem:
        """Move an item into another list, removing it from ``self``.

        Parameters
        ----------
        item_id : int
            The item's id in ``self``.
        target : TaskliList
            The list to move the item into.

        Returns
        -------
        TaskliItem
            The newly created item in ``target``.
        """

        moved = self.copy_item(item_id, target)
        self.remove_item(item_id)

        return moved
