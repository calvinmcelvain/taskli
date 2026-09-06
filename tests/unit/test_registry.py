from datetime import datetime

import pytest

from taskli.models import Operator, Priority, Status, TaskliList
from taskli.models.registry import (
    ATTRIBUTES,
    filterable,
    renderable,
    sortable,
)


class TestAttributes:
    def test_key_set(self):
        assert set(ATTRIBUTES) == {
            "id",
            "status",
            "text",
            "priority",
            "tags",
            "created_at",
            "color",
        }

    @pytest.mark.parametrize("name", list(ATTRIBUTES))
    def test_name_matches_key(self, name):
        assert ATTRIBUTES[name].name == name

    def test_filter_operators_set(self):
        priority = ATTRIBUTES["priority"]
        tags = ATTRIBUTES["tags"]

        assert priority.filter_operators == (Operator.EQ,)
        assert priority.filter_default_operator is Operator.EQ
        assert tags.filter_operators == (Operator.CONTAINS,)
        assert tags.filter_default_operator is Operator.CONTAINS

    @pytest.mark.parametrize(
        "name", ["id", "status", "text", "created_at", "color"]
    )
    def test_filter_operators_absent(self, name):
        attr = ATTRIBUTES[name]

        assert attr.filter_operators == ()
        assert attr.filter_default_operator is None

    def test_priority_sort_key_is_index(self):
        todo = TaskliList(name="t")
        low = todo.add_item("low", priority=Priority.LOW)
        high = todo.add_item("high", priority=Priority.HIGH)
        key = ATTRIBUTES["priority"].sort_key
        assert key

        assert key(low) == 1
        assert key(high) == 3

    def test_priority_sort_descending(self):
        assert ATTRIBUTES["priority"].sort_descending is True

    def test_tags_sort_key_empty_last_then_alpha(self):
        todo = TaskliList(name="t")
        untagged = todo.add_item("untagged")
        zed = todo.add_item("zed", tags=["z"])
        ace = todo.add_item("ace", tags=["a"])
        key = ATTRIBUTES["tags"].sort_key
        assert key

        ordered = sorted([untagged, zed, ace], key=key)

        assert [i.text for i in ordered] == ["ace", "zed", "untagged"]

    def test_created_at_sort_key_is_datetime(self):
        todo = TaskliList(name="t")
        item = todo.add_item("x", created_at=datetime(2021, 6, 1))
        key = ATTRIBUTES["created_at"].sort_key
        assert key

        assert key(item) == datetime(2021, 6, 1)


class TestRenderFacets:
    def test_id_render_format(self):
        todo = TaskliList(name="t")
        item = todo.add_item("x")
        fmt = ATTRIBUTES["id"].render_format
        assert fmt

        assert fmt(item) == "1"

    @pytest.mark.parametrize(
        ("status", "marker"),
        [
            (Status.TODO, " "),
            (Status.IN_PROGRESS, "•"),
            (Status.DONE, "x"),
        ],
        ids=["todo", "in-progress", "done"],
    )
    def test_status_render_format(self, status, marker):
        todo = TaskliList(name="t")
        item = todo.add_item("x")
        item.status = status
        fmt = ATTRIBUTES["status"].render_format
        assert fmt

        assert fmt(item) == marker

    def test_text_render_format_passthrough(self):
        todo = TaskliList(name="t")
        item = todo.add_item("buy milk")
        fmt = ATTRIBUTES["text"].render_format
        assert fmt

        assert fmt(item) == "buy milk"

    def test_priority_render_format_label(self):
        todo = TaskliList(name="t")
        item = todo.add_item("x", priority=Priority.HIGH)
        fmt = ATTRIBUTES["priority"].render_format
        assert fmt

        assert fmt(item) == "high"

    def test_tags_render_format_joins(self):
        todo = TaskliList(name="t")
        item = todo.add_item("x", tags=["a", "b"])
        fmt = ATTRIBUTES["tags"].render_format
        assert fmt

        assert fmt(item) == "a, b"

    def test_render_format_absent_for_nonrendered(self):
        assert ATTRIBUTES["created_at"].render_format is None
        assert ATTRIBUTES["color"].render_format is None

    @pytest.mark.parametrize(
        ("priority", "color"),
        [
            (Priority.LOW, "green"),
            (Priority.MEDIUM, "yellow"),
            (Priority.HIGH, "red"),
        ],
        ids=["low", "medium", "high"],
    )
    def test_priority_render_style(self, priority, color):
        todo = TaskliList(name="t")
        item = todo.add_item("x", priority=priority)
        style = ATTRIBUTES["priority"].render_style
        assert style

        assert style(item) == color

    def test_text_render_style_dim_when_done(self):
        todo = TaskliList(name="t")
        item = todo.add_item("x")
        todo.mark_done(item.id)
        style = ATTRIBUTES["text"].render_style
        assert style

        assert style(item) == "dim"

    def test_text_render_style_none_when_not_done(self):
        todo = TaskliList(name="t")
        item = todo.add_item("x")
        style = ATTRIBUTES["text"].render_style
        assert style

        assert style(item) is None

    @pytest.mark.parametrize(
        "name", ["id", "status", "tags", "created_at", "color"]
    )
    def test_render_style_absent(self, name):
        assert ATTRIBUTES[name].render_style is None


class TestAccessors:
    def test_renderable_headers_and_justify_in_column_order(self):
        columns = renderable()

        assert [column.header for column in columns] == [
            "ID",
            "State",
            "Text",
            "Priority",
            "Tags",
        ]
        assert [column.justify for column in columns] == [
            "right",
            "center",
            "left",
            "left",
            "left",
        ]

    def test_renderable_carries_the_attribute_callables(self):
        priority = ATTRIBUTES["priority"]
        by_header = {column.header: column for column in renderable()}

        assert by_header["Priority"].format is priority.render_format
        assert by_header["Priority"].style is priority.render_style
        assert by_header["ID"].style is None

    def test_sortable_keys(self):
        assert list(sortable()) == ["priority", "tags", "created_at"]

    def test_filterable_keys(self):
        assert list(filterable()) == ["priority", "tags"]
