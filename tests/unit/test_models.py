from datetime import datetime
from typing import get_args

import pytest
from pydantic import ValidationError
from rich.color import Color as RichColor

from taskli.exceptions import (
    InvalidConfigValueError,
    ItemNotFoundError,
    UnknownConfigKeyError,
)
from taskli.models import (
    Color,
    Config,
    Delimters,
    Filter,
    Priority,
    Status,
    TaskliItem,
    TaskliList,
    path_key,
    walk_items,
)
from utils import (
    add_item,
    add_subtask,
    edit_item,
    priority_criterion,
    sort,
    tag_criterion,
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


class TestTaskliItem:
    def test_due_date_defaults_none(self):
        item = TaskliItem(id="1", text="x", created_at=datetime(2020, 1, 1))

        assert item.due_date is None

    def test_due_date_survives_json_round_trip(self):
        item = TaskliItem(
            id="1",
            text="x",
            created_at=datetime(2020, 1, 1),
            due_date=datetime(2020, 6, 1),
        )

        restored = TaskliItem.model_validate(item.model_dump(mode="json"))

        assert restored.due_date == datetime(2020, 6, 1)

    def test_old_shape_without_due_date_validates_to_none(self):
        restored = TaskliItem.model_validate(
            {"id": "1", "text": "x", "created_at": "2020-01-01T00:00:00"}
        )

        assert restored.due_date is None

    def test_description_defaults_none(self):
        item = TaskliItem(id="1", text="x", created_at=datetime(2020, 1, 1))

        assert item.description is None

    def test_description_survives_json_round_trip(self):
        item = TaskliItem(
            id="1",
            text="x",
            created_at=datetime(2020, 1, 1),
            description="a note",
        )

        restored = TaskliItem.model_validate(item.model_dump(mode="json"))

        assert restored.description == "a note"

    def test_old_shape_without_description_validates_to_none(self):
        restored = TaskliItem.model_validate(
            {"id": "1", "text": "x", "created_at": "2020-01-01T00:00:00"}
        )

        assert restored.description is None

    def test_children_default_empty(self):
        item = TaskliItem(id="1", text="x", created_at=datetime(2020, 1, 1))

        assert item.children == []

    def test_rejects_non_path_id(self):
        with pytest.raises(ValidationError):
            TaskliItem(id="1.x", text="x", created_at=datetime(2020, 1, 1))

    def test_accepts_deep_path_id(self):
        item = TaskliItem.model_validate(
            {"id": "1.2.3", "text": "x", "created_at": "2020-01-01T00:00:00"}
        )

        assert item.id == "1.2.3"


class TestTaskliList:
    def test_add_item_assigns_sequential_ids(self):
        todo_list = TaskliList(name="work")

        first = todo_list.add_item("first")
        second = todo_list.add_item("second")

        assert first.id == "1"
        assert second.id == "2"

    def test_add_item_defaults(self):
        todo_list = TaskliList(name="work")

        item = todo_list.add_item("task")

        assert isinstance(item, TaskliItem)
        assert item.priority == Priority.MEDIUM
        assert item.tags == []
        assert item.done is False

    def test_add_item_defaults_modified_at_to_created_at(self):
        todo_list = TaskliList(name="work")

        item = todo_list.add_item("task")

        assert item.modified_at == item.created_at

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

    def test_mark_done_updates_modified_at(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")
        item.modified_at = datetime(2020, 1, 1)

        todo_list.mark_done(item.id)

        assert item.modified_at != datetime(2020, 1, 1)

    def test_mark_undone_updates_modified_at(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")
        todo_list.mark_done(item.id)
        item.modified_at = datetime(2020, 1, 1)

        todo_list.mark_undone(item.id)

        assert item.modified_at != datetime(2020, 1, 1)

    def test_mark_in_progress_sets_status(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        todo_list.mark_in_progress(item.id)

        assert item.status == Status.IN_PROGRESS
        assert item.done is False

    def test_mark_in_progress_from_done_clears_completed_at(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")
        todo_list.mark_done(item.id)

        todo_list.mark_in_progress(item.id)

        assert item.status == Status.IN_PROGRESS
        assert item.completed_at is None

    def test_mark_in_progress_updates_modified_at(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")
        item.modified_at = datetime(2020, 1, 1)

        todo_list.mark_in_progress(item.id)

        assert item.modified_at != datetime(2020, 1, 1)

    def test_mark_undone_resets_in_progress_to_todo(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")
        todo_list.mark_in_progress(item.id)

        todo_list.mark_undone(item.id)

        assert item.status == Status.TODO
        assert item.completed_at is None

    def test_remove_item(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        todo_list.remove_item(item.id)

        assert todo_list.items == []

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
        item = add_item(todo_list, "task", tags=["a"])

        edit_item(todo_list, item.id, text="new text")

        assert item.text == "new text"
        assert item.tags == ["a"]

    def test_edit_item_updates_modified_at_when_changed(self):
        todo_list = TaskliList(name="work")
        item = add_item(todo_list, "task")
        item.modified_at = datetime(2020, 1, 1)

        edit_item(todo_list, item.id, text="new text")

        assert item.modified_at != datetime(2020, 1, 1)

    def test_edit_item_sets_due_date_and_bumps_modified_at(self):
        todo_list = TaskliList(name="work")
        item = add_item(todo_list, "task")
        item.modified_at = datetime(2020, 1, 1)

        edit_item(todo_list, item.id, due_date=datetime(2021, 3, 4))

        assert item.due_date == datetime(2021, 3, 4)
        assert item.modified_at != datetime(2020, 1, 1)

    def test_edit_item_sets_description_and_bumps_modified_at(self):
        todo_list = TaskliList(name="work")
        item = add_item(todo_list, "task")
        item.modified_at = datetime(2020, 1, 1)

        edit_item(todo_list, item.id, description="a note")

        assert item.description == "a note"
        assert item.modified_at != datetime(2020, 1, 1)

    def test_edit_item_clears_description_and_bumps_modified_at(self):
        todo_list = TaskliList(name="work")
        item = add_item(todo_list, "task", description="a note")
        item.modified_at = datetime(2020, 1, 1)

        edit_item(todo_list, item.id, description=None)

        assert item.description is None
        assert item.modified_at != datetime(2020, 1, 1)

    def test_edit_item_leaves_modified_at_when_nothing_changes(self):
        todo_list = TaskliList(name="work")
        item = add_item(todo_list, "task")
        item.modified_at = datetime(2020, 1, 1)

        edit_item(todo_list, item.id)

        assert item.modified_at == datetime(2020, 1, 1)

    def test_filtered_items_by_tag_case_insensitive(self):
        todo_list = TaskliList(name="work")
        add_item(todo_list, "a", tags=["Urgent"])
        add_item(todo_list, "b", tags=["later"])

        result = todo_list.filtered_items(Filter((tag_criterion("urgent"),)))

        assert len(result) == 1
        assert result[0].text == "a"

    def test_filtered_items_no_filter_returns_all(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("a")
        todo_list.add_item("b")

        result = todo_list.filtered_items(Filter())

        assert len(result) == 2

    def test_filtered_items_by_priority(self):
        todo_list = TaskliList(name="work")
        add_item(todo_list, "a", priority=Priority.HIGH)
        add_item(todo_list, "b", priority=Priority.LOW)

        result = todo_list.filtered_items(
            Filter((priority_criterion(Priority.HIGH),))
        )

        assert len(result) == 1
        assert result[0].text == "a"

    def test_filtered_items_combines_tag_and_priority(self):
        todo_list = TaskliList(name="work")
        add_item(todo_list, "a", tags=["urgent"], priority=Priority.HIGH)
        add_item(todo_list, "b", tags=["urgent"], priority=Priority.LOW)
        add_item(todo_list, "c", tags=["later"], priority=Priority.HIGH)
        item_filter = Filter(
            (tag_criterion("urgent"), priority_criterion(Priority.HIGH))
        )

        result = todo_list.filtered_items(item_filter)

        assert len(result) == 1
        assert result[0].text == "a"

    def test_add_tags_appends_new_only(self):
        todo_list = TaskliList(name="work")
        item = add_item(todo_list, "task", tags=["a"])

        todo_list.add_tags(item.id, ["a", "b"])

        assert item.tags == ["a", "b"]

    def test_add_tags_updates_modified_at(self):
        todo_list = TaskliList(name="work")
        item = add_item(todo_list, "task", tags=["a"])
        item.modified_at = datetime(2020, 1, 1)

        todo_list.add_tags(item.id, ["b"])

        assert item.modified_at != datetime(2020, 1, 1)

    def test_copy_item_adds_to_target_with_new_id(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        item = add_item(source, "task", priority=Priority.HIGH, tags=["a"])

        copied = source.copy_item(item.id, target)

        assert copied.id == "1"
        assert copied.text == "task"
        assert copied.priority == Priority.HIGH
        assert copied.tags == ["a"]
        assert copied in target.items
        assert item in source.items

    def test_copy_item_copies_all_settable_attributes(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        item = add_item(
            source,
            "task",
            priority=Priority.HIGH,
            tags=["a"],
            due_date=datetime(2020, 6, 1),
            description="a note",
        )

        copied = source.copy_item(item.id, target)

        assert copied.priority == Priority.HIGH
        assert copied.tags == ["a"]
        assert copied.tags is not item.tags
        assert copied.due_date == datetime(2020, 6, 1)
        assert copied.description == "a note"

    def test_copy_item_resets_done_state(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        item = source.add_item("task")
        source.mark_done(item.id)

        copied = source.copy_item(item.id, target)

        assert copied.done is False
        assert copied.completed_at is None

    def test_copy_item_preserves_created_at_and_bumps_modified_at(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        item = source.add_item("task")
        item.created_at = datetime(2020, 1, 1)
        item.modified_at = datetime(2020, 1, 1)

        copied = source.copy_item(item.id, target)

        assert copied.created_at == datetime(2020, 1, 1)
        assert copied.modified_at != datetime(2020, 1, 1)

    def test_copy_item_interleaves_target_by_created_at(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        old_item = source.add_item("old task")
        old_item.created_at = datetime(2020, 1, 1)
        existing = target.add_item("existing task")

        source.copy_item(old_item.id, target)
        target.resort(sort("created_at"))

        assert target.get_item(1).text == "old task"
        assert target.get_item(2).text == existing.text

    def test_copy_item_missing_id_raises(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")

        with pytest.raises(ItemNotFoundError):
            source.copy_item(1, target)

    def test_move_item_removes_from_source(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        item = add_item(source, "task", priority=Priority.LOW, tags=["a"])

        moved = source.move_item(item.id, target)

        assert source.items == []
        assert moved in target.items
        assert moved.text == "task"
        assert moved.priority == Priority.LOW
        assert moved.tags == ["a"]

    def test_move_item_reindexes_source(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        first = source.add_item("first")
        second = source.add_item("second")

        source.move_item(first.id, target)

        assert [item.id for item in source.items] == ["1"]
        assert second.id == "1"

    def test_move_item_preserves_created_at_and_bumps_modified_at(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        item = source.add_item("task")
        item.created_at = datetime(2020, 1, 1)
        item.modified_at = datetime(2020, 1, 1)

        moved = source.move_item(item.id, target)

        assert moved.created_at == datetime(2020, 1, 1)
        assert moved.modified_at != datetime(2020, 1, 1)

    def test_move_item_missing_id_raises(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")

        with pytest.raises(ItemNotFoundError):
            source.move_item(1, target)

    def test_remove_item_ref_drops_and_reindexes(self):
        todo_list = TaskliList(name="work")
        first = todo_list.add_item("first")
        second = todo_list.add_item("second")

        todo_list.remove_item_ref(first)

        assert todo_list.items == [second]
        assert second.id == "1"

    def test_mark_done_ref_updates_item(self):
        todo_list = TaskliList(name="work")
        item = todo_list.add_item("task")

        result = todo_list.mark_done_ref(item)

        assert isinstance(result, TaskliItem)
        assert result is item
        assert item.status == Status.DONE
        assert item.completed_at is not None

    def test_copy_item_ref_adds_to_target(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        item = add_item(source, "task", priority=Priority.HIGH, tags=["a"])

        copied = source.copy_item_ref(item, target)

        assert isinstance(copied, TaskliItem)
        assert copied.id == "1"
        assert copied.text == "task"
        assert copied.priority == Priority.HIGH
        assert copied in target.items
        assert item in source.items

    def test_move_item_ref_removes_from_source(self):
        source = TaskliList(name="work")
        target = TaskliList(name="groceries")
        item = source.add_item("task")

        moved = source.move_item_ref(item, target)

        assert isinstance(moved, TaskliItem)
        assert source.items == []
        assert moved in target.items
        assert moved.text == "task"

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
        add_item(todo_list, "first", tags=["z", "a"])
        add_item(todo_list, "second", tags=["m"])
        add_item(todo_list, "third")

        todo_list.sort_by(sort("tags"))

        assert [item.text for item in todo_list.items] == [
            "first",
            "second",
            "third",
        ]

    def test_sort_by_priority_orders_high_to_low(self):
        todo_list = TaskliList(name="work")
        add_item(todo_list, "c", priority=Priority.HIGH)
        add_item(todo_list, "a", priority=Priority.LOW)
        add_item(todo_list, "b", priority=Priority.MEDIUM)

        todo_list.sort_by(sort("priority"))

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
        add_item(todo_list, "low", priority=Priority.LOW)
        add_item(todo_list, "high", priority=Priority.HIGH)

        todo_list.resort(sort("priority"))

        assert [item.text for item in todo_list.items] == ["high", "low"]
        assert [item.id for item in todo_list.items] == ["1", "2"]

    def test_view_only_excluded_from_dump(self):
        todo_list = TaskliList(name="work", view_only=True)

        assert "view_only" not in todo_list.model_dump()


class TestPathKey:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("1", (1,)),
            ("1.2", (1, 2)),
            ("1.2.3", (1, 2, 3)),
        ],
        ids=["single", "nested", "deep"],
    )
    def test_segments(self, path, expected):
        assert path_key(path) == expected

    def test_orders_numerically(self):
        assert path_key("1.10") > path_key("1.2")

    def test_non_numeric_segment_raises(self):
        with pytest.raises(ValueError):
            path_key("1.x")


class TestWalkItems:
    def test_pre_order_dfs(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("a")
        add_subtask(todo_list, "1", "a1")
        add_subtask(todo_list, "1.1", "a1a")
        add_subtask(todo_list, "1", "a2")
        todo_list.add_item("b")

        flat = walk_items(todo_list.items)

        assert [item.text for item in flat] == ["a", "a1", "a1a", "a2", "b"]


class TestTaskliListTree:
    def test_get_item_by_dotted_path(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        child = todo_list.add_item("child", parent_path="1")
        grandchild = todo_list.add_item("grandchild", parent_path="1.1")

        assert todo_list.get_item("1.1") is child
        assert todo_list.get_item("1.1.1") is grandchild

    def test_get_item_missing_nested_path_raises(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")

        with pytest.raises(ItemNotFoundError):
            todo_list.get_item("1.5")

    def test_add_item_under_parent_assigns_dotted_id(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        first = todo_list.add_item("first", parent_path="1")
        second = todo_list.add_item("second", parent_path="1")

        assert first.id == "1.1"
        assert second.id == "1.2"

    def test_add_item_under_parent_survives_resort(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        add_subtask(todo_list, "1", "first")
        add_subtask(todo_list, "1", "second")

        todo_list.resort(sort("created_at"))

        assert todo_list.get_item("1.2").text == "second"

    def test_reindex_renumbers_nested_and_keeps_refs(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("a")
        todo_list.add_item("b")
        child = todo_list.add_item("b child", parent_path="2")
        todo_list.items.insert(0, todo_list.items.pop(1))

        todo_list.reindex()

        assert todo_list.items[0].id == "1"
        assert child.id == "1.1"

    def test_sort_by_orders_children(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        add_subtask(todo_list, "1", "low", priority=Priority.LOW)
        add_subtask(todo_list, "1", "high", priority=Priority.HIGH)

        todo_list.sort_by(sort("priority"))

        children = todo_list.items[0].children
        assert [child.text for child in children] == ["high", "low"]

    def test_sort_by_index_uses_path_key_order(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        for n in range(10):
            add_subtask(todo_list, "1", f"child {n}")
        todo_list.items[0].children.reverse()

        todo_list.sort_by_index()

        ids = [child.id for child in todo_list.items[0].children]
        assert ids == [f"1.{n}" for n in range(1, 11)]
        assert ids.index("1.10") > ids.index("1.2")

    def test_prune_removes_done_leaf(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("keep")
        done_leaf = todo_list.add_item("done")
        todo_list.mark_done("2")

        removed = todo_list.prune()

        assert removed == [done_leaf]
        assert [item.text for item in todo_list.items] == ["keep"]

    def test_prune_keeps_done_parent_with_open_child(self):
        todo_list = TaskliList(name="work")
        parent = todo_list.add_item("parent")
        add_subtask(todo_list, "1", "open child")
        todo_list.mark_done("1")

        removed = todo_list.prune()

        assert removed == []
        assert todo_list.get_item("1") is parent
        assert len(parent.children) == 1

    def test_prune_removes_fully_done_subtree(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        add_subtask(todo_list, "1", "child")
        todo_list.mark_done("1.1")
        todo_list.mark_done("1")

        removed = todo_list.prune()

        assert {item.text for item in removed} == {"parent", "child"}
        assert todo_list.items == []

    def test_remove_item_ref_cascades_subtree(self):
        todo_list = TaskliList(name="work")
        first = todo_list.add_item("first")
        add_subtask(todo_list, "1", "child")
        add_subtask(todo_list, "1.1", "grandchild")
        todo_list.add_item("second")

        todo_list.remove_item_ref(first)

        assert [item.id for item in walk_items(todo_list.items)] == ["1"]
        assert todo_list.items[0].text == "second"

    def test_remove_item_nested_path_reindexes_siblings(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        add_subtask(todo_list, "1", "a")
        add_subtask(todo_list, "1", "b")

        todo_list.remove_item("1.1")

        children = todo_list.items[0].children
        assert [child.id for child in children] == ["1.1"]
        assert children[0].text == "b"

    def test_filtered_items_keeps_ancestor_of_match(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        add_subtask(todo_list, "1", "child", tags=["urgent"])
        todo_list.add_item("other")

        result = todo_list.filtered_items(Filter((tag_criterion("urgent"),)))

        assert [item.text for item in result] == ["parent"]
        assert [item.text for item in result[0].children] == ["child"]

    def test_filtered_items_drops_non_matching_branch(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        add_subtask(todo_list, "1", "child", tags=["urgent"])
        add_subtask(todo_list, "1", "sibling", tags=["later"])

        result = todo_list.filtered_items(Filter((tag_criterion("urgent"),)))

        assert [item.text for item in result[0].children] == ["child"]

    def test_filtered_items_returns_deep_copies(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        add_subtask(todo_list, "1", "child", tags=["urgent"])

        result = todo_list.filtered_items(Filter((tag_criterion("urgent"),)))
        result[0].text = "mutated"
        result[0].children.clear()

        assert todo_list.get_item("1").text == "parent"
        assert [c.text for c in todo_list.get_item("1").children] == ["child"]

    def test_filtered_items_copies_isolate_nested_mutations(self):
        todo_list = TaskliList(name="work")
        todo_list.add_item("parent")
        add_subtask(todo_list, "1", "child", tags=["urgent"])

        result = todo_list.filtered_items(Filter((tag_criterion("urgent"),)))
        result[0].children[0].text = "mutated"
        result[0].children[0].tags.append("extra")

        assert todo_list.get_item("1.1").text == "child"
        assert todo_list.get_item("1.1").tags == ["urgent"]

    def test_copy_item_carries_subtree(self):
        source = TaskliList(name="work")
        target = TaskliList(name="archive")
        source.add_item("parent")
        add_subtask(source, "1", "child")
        add_subtask(source, "1.1", "grandchild")

        copied = source.copy_item("1", target)
        target.resort(sort("created_at"))

        assert copied.text == "parent"
        assert [item.text for item in walk_items(target.items)] == [
            "parent",
            "child",
            "grandchild",
        ]
        assert [item.id for item in walk_items(target.items)] == [
            "1",
            "1.1",
            "1.1.1",
        ]

    def test_copy_item_makes_fresh_items(self):
        source = TaskliList(name="work")
        target = TaskliList(name="archive")
        source.add_item("parent")
        add_subtask(source, "1", "child")
        source.mark_done("1.1")

        source.copy_item("1", target)
        target.resort(sort("created_at"))

        assert target.get_item("1.1").status == Status.TODO
        assert source.get_item("1.1").status == Status.DONE

    def test_move_item_carries_subtree_and_clears_source(self):
        source = TaskliList(name="work")
        target = TaskliList(name="archive")
        source.add_item("keep")
        source.add_item("parent")
        add_subtask(source, "2", "child")

        source.move_item("2", target)
        target.resort(sort("created_at"))

        assert [item.text for item in walk_items(source.items)] == ["keep"]
        assert [item.text for item in walk_items(target.items)] == [
            "parent",
            "child",
        ]
