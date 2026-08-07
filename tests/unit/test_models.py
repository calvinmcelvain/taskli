from typing import get_args

import pytest
from rich.color import Color as RichColor

from taskli.exceptions import (
    InvalidConfigValueError,
    ItemNotFoundError,
    UnknownConfigKeyError,
)
from taskli.models import (
    ActionOutcome,
    Color,
    Config,
    Delimters,
    Priority,
    TaskliItem,
    TaskliList,
)


class TestColor:
    @pytest.mark.parametrize("member", list(Color))
    def test_values_parse_as_rich_colors(self, member):
        RichColor.parse(member.value)


class TestConfig:
    def test_get_value(self):
        config = Config()

        assert config.get_value("default_list") == "inbox"

    def test_get_value_unknown_key_raises(self):
        config = Config()

        with pytest.raises(UnknownConfigKeyError):
            config.get_value("nope")

    def test_set_value_bool(self):
        config = Config()

        config.set_value("auto_prune", "true")

        assert config.auto_prune is True

    def test_set_value_rejects_bad_bool(self):
        config = Config()

        with pytest.raises(InvalidConfigValueError):
            config.set_value("auto_prune", "sortof")

    def test_set_value_sort_by(self):
        config = Config()

        config.set_value("default_sort", "priority")

        assert config.default_sort == "priority"

    def test_set_value_rejects_bad_sort_by(self):
        config = Config()

        with pytest.raises(InvalidConfigValueError):
            config.set_value("default_sort", "size")

    def test_set_value_priority(self):
        config = Config()

        config.set_value("default_priority", "high")

        assert config.default_priority == Priority.HIGH

    def test_set_value_rejects_bad_priority(self):
        config = Config()

        with pytest.raises(InvalidConfigValueError):
            config.set_value("default_priority", "urgent")

    def test_set_value_color(self):
        config = Config()

        config.set_value("default_color", "teal")

        assert config.default_color == Color.TEAL

    def test_set_value_rejects_bad_color(self):
        config = Config()

        with pytest.raises(InvalidConfigValueError):
            config.set_value("default_color", "notacolor")

    @pytest.mark.parametrize(
        "delimiter",
        list(get_args(Delimters.__value__)),
        ids=["dot", "slash", "dash", "pipe"],
    )
    def test_sets_allowed_delimiters(self, delimiter):
        config = Config()
        config.set_value("sublist_delimiter", delimiter)

        assert config.sublist_delimiter == delimiter

    def test_rejects_disallowed_delimiter(self):
        config = Config()

        with pytest.raises(InvalidConfigValueError):
            config.set_value("sublist_delimiter", ":")

    def test_set_value_rejects_empty_string(self):
        config = Config()

        with pytest.raises(InvalidConfigValueError):
            config.set_value("default_list", "")

    def test_set_value_unknown_key_raises(self):
        config = Config()

        with pytest.raises(UnknownConfigKeyError):
            config.set_value("nope", "x")


class TestTaskliList:
    def test_add_item_assigns_sequential_ids(self):
        todo_list = TaskliList(name="work")

        first = todo_list.add_item("first")
        second = todo_list.add_item("second")

        assert first.id == 1
        assert second.id == 2

    def test_add_item_defaults(self):
        todo_list = TaskliList(name="work")

        item = todo_list.add_item("task")

        assert isinstance(item, TaskliItem)
        assert item.priority == Priority.MEDIUM
        assert item.tags == []
        assert item.done is False

    def test_get_item_missing_id_raises(self):
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

    def test_mark_done_returns_outcome(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        outcome = todo_list.mark_done(item.id)

        assert isinstance(outcome, ActionOutcome)
        assert outcome.item_id == item.id
        assert not outcome.error

    def test_mark_done_missing_id_returns_error_outcome(self):
        todo_list = TaskliList(name="work")

        outcome = todo_list.mark_done(1)

        assert outcome.item_id == 1
        assert outcome.error

    def test_mark_undone_missing_id_returns_error_outcome(self):
        todo_list = TaskliList(name="work")

        outcome = todo_list.mark_undone(1)

        assert outcome.error

    def test_remove_item_returns_outcome(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        outcome = todo_list.remove_item(item.id)

        assert isinstance(outcome, ActionOutcome)
        assert not outcome.error
        assert todo_list.items == []

    def test_remove_item_missing_id_returns_error_outcome(self):
        todo_list = TaskliList(name="work")

        outcome = todo_list.remove_item(1)

        assert outcome.error

    def test_prune_keeps_open_items(self):
        todo_list = TaskliList(name="work")
        done_item = todo_list.add_item("done task")
        not_done_item = todo_list.add_item("open task")
        todo_list.mark_done(done_item.id)

        removed = todo_list.prune()

        assert removed == [done_item]
        assert todo_list.items == [not_done_item]

    def test_prune_noop_when_none_done(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        removed = todo_list.prune()

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
            '{"name": "work", "items": []}'
        )

        assert restored.color == Color.WHITE

    def test_display_name_defaults_to_stored_name(self):
        todo_list = TaskliList(name="work")

        assert todo_list.display_name() == "work"

    def test_display_name_substitutes_delimiter_for_dots(self):
        todo_list = TaskliList(name="work.meetings")

        assert todo_list.display_name("/") == "work/meetings"

    def test_sort_by_tags_orders_by_joined_sorted_tags(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("first", tags=["z", "a"])
        todo_list.add_item("second", tags=["m"])
        todo_list.add_item("third")

        todo_list.sort_by("tags")

        assert [item.text for item in todo_list.items] == [
            "first",
            "second",
            "third",
        ]

    def test_sort_by_priority_orders_high_to_low(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("c", priority=Priority.HIGH)
        todo_list.add_item("a", priority=Priority.LOW)
        todo_list.add_item("b", priority=Priority.MEDIUM)

        todo_list.sort_by("priority")

        assert [item.text for item in todo_list.items] == ["c", "b", "a"]

    def test_sort_by_index_orders_by_id_ascending(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("a")
        todo_list.add_item("b")
        todo_list.add_item("c")
        todo_list.items[0].id, todo_list.items[2].id = (
            todo_list.items[2].id,
            todo_list.items[0].id,
        )

        todo_list.sort_by_index()

        assert [item.text for item in todo_list.items] == ["c", "b", "a"]

    def test_resort_sorts_then_reindexes(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("low", priority=Priority.LOW)
        todo_list.add_item("high", priority=Priority.HIGH)

        todo_list.resort("priority")

        assert [item.text for item in todo_list.items] == ["high", "low"]
        assert [item.id for item in todo_list.items] == [1, 2]


class TestBatchMutation:
    def test_mark_done_many_partial_success(self):
        task_list = TaskliList(name="work")
        for text in ("a", "b", "c"):
            task_list.add_item(text)

        outcomes = task_list.mark_done_many([1, 3, 99])

        assert [o.item_id for o in outcomes] == [1, 3, 99]
        assert not outcomes[0].error
        assert not outcomes[1].error
        assert outcomes[2].error
        assert task_list.get_item(1).done is True
        assert task_list.get_item(3).done is True
        assert task_list.get_item(2).done is False

    def test_mark_undone_many_partial_success(self):
        task_list = TaskliList(name="work")
        task_list.add_item("a")
        task_list.mark_done(1)

        outcomes = task_list.mark_undone_many([1, 99])

        assert not outcomes[0].error
        assert outcomes[1].error
        assert task_list.get_item(1).done is False

    def test_remove_items_partial_success_reindexes_once(self):
        task_list = TaskliList(name="work")
        for text in ("a", "b", "c", "d"):
            task_list.add_item(text)

        outcomes = task_list.remove_items([2, 4, 99])

        assert not outcomes[0].error
        assert not outcomes[1].error
        assert outcomes[2].error
        assert [item.text for item in task_list.items] == ["a", "c"]
        assert [item.id for item in task_list.items] == [1, 2]

    def test_remove_items_all_missing_removes_nothing(self):
        task_list = TaskliList(name="work")
        task_list.add_item("a")

        outcomes = task_list.remove_items([99, 100])

        assert all(o.error for o in outcomes)
        assert [item.text for item in task_list.items] == ["a"]
