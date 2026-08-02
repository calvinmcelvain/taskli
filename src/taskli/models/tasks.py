"""Tasks & task list models."""

from datetime import datetime

from pydantic import BaseModel, Field

from ..exceptions import ItemNotFoundError
from .attributes import Color, Priority

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
    next_id: int = 1
    items: list[TaskliItem] = Field(default_factory=list)

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

        self.next_id = len(self.items) + 1

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

        item = TaskliItem(
            id=self.next_id,
            text=text,
            priority=priority,
            tags=tags or [],
            created_at=datetime.now(),
        )
        self.items.append(item)
        self.next_id += 1

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

    def remove_done_items(self) -> list[TaskliItem]:
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

    def filtered_items(self, *, tag: str | None = None) -> list[TaskliItem]:
        """Return items, optionally filtered by tag (case-insensitive).

        Parameters
        ----------
        tag : str | None, optional
            Tag to filter by, by default no filtering.

        Returns
        -------
        list[TaskliItem]
            The matching items.
        """

        if tag is None:
            return list(self.items)

        needle = tag.lower()

        return [
            item
            for item in self.items
            if needle in (t.lower() for t in item.tags)
        ]
