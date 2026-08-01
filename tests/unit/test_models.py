import pytest
from rich.color import Color as RichColor

from taskli.models import (
    Color,
    ItemNotFoundError,
    Priority,
    TaskliItem,
    TaskliList,
)


class TestColor:
    @pytest.mark.parametrize("member", list(Color))
    def test_values_parse_as_rich_colors(self, member):
        RichColor.parse(member.value)


class TestTaskliList:
    def test_add_item_assigns_sequential_ids(self):
        todo_list = TaskliList(name="work")

        first = todo_list.add_item("first")
        second = todo_list.add_item("second")

        assert first.id == 1
        assert second.id == 2
        assert todo_list.next_id == 3

    def test_add_item_defaults(self):
        todo_list = TaskliList(name="work")

        item = todo_list.add_item("task")

        assert isinstance(item, TaskliItem)
        assert item.priority == Priority.MEDIUM
        assert item.tags == []
        assert item.done is False

    def test_get_item_raises_for_missing_id(self):
        todo_list = TaskliList(name="work")

        with pytest.raises(ItemNotFoundError):
            todo_list.get_item(1)

    def test_mark_done_sets_completed_at(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        todo_list.mark_done(item.id)

        assert item.done is True
        assert item.completed_at is not None

    def test_mark_undone_clears_completed_at(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")
        todo_list.mark_done(item.id)

        todo_list.mark_undone(item.id)

        assert item.done is False
        assert item.completed_at is None

    def test_remove_item(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        todo_list.remove_item(item.id)

        assert todo_list.items == []

    def test_remove_done_items_removes_done_only(self):
        todo_list = TaskliList(name="work")
        done_item = todo_list.add_item("done task")
        not_done_item = todo_list.add_item("open task")
        todo_list.mark_done(done_item.id)

        removed = todo_list.remove_done_items()

        assert removed == [done_item]
        assert todo_list.items == [not_done_item]

    def test_remove_done_items_noop_when_none_done(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        removed = todo_list.remove_done_items()

        assert removed == []
        assert todo_list.items == [item]

    def test_edit_item_updates_given_fields_only(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task", tags=["a"])

        todo_list.edit_item(item.id, text="new text")

        assert item.text == "new text"
        assert item.tags == ["a"]

    def test_filtered_items_by_tag_case_insensitive(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("a", tags=["Urgent"])
        todo_list.add_item("b", tags=["later"])

        result = todo_list.filtered_items(tag="urgent")

        assert len(result) == 1
        assert result[0].text == "a"

    def test_filtered_items_no_filter_returns_all(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("a")
        todo_list.add_item("b")

        result = todo_list.filtered_items()

        assert len(result) == 2

    def test_color_defaults(self):
        todo_list = TaskliList(name="work")

        assert todo_list.color == Color.WHITE

    def test_set_color_updates_field(self):
        todo_list = TaskliList(name="work")

        todo_list.set_color(Color.CORAL)

        assert todo_list.color is Color.CORAL

    def test_color_survives_json_round_trip(self):
        todo_list = TaskliList(name="work", color=Color.CORAL)

        restored = TaskliList.model_validate_json(todo_list.model_dump_json())

        assert restored.color is Color.CORAL

    def test_missing_color_key_defaults(self):
        restored = TaskliList.model_validate_json(
            '{"name": "work", "next_id": 1, "items": []}'
        )

        assert restored.color == Color.WHITE
