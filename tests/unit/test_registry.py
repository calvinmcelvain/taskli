from datetime import date, datetime

import pytest

from taskli.models import Operator, Priority, TaskliList
from taskli.models.dates import parse_due_date
from taskli.models.registry import (
    ATTRIBUTES,
    filterable,
    modifiable,
    renderable,
    sortable,
)
from utils import add_item, freeze_today


class TestAttributes:
    def test_key_set(self):
        assert set(ATTRIBUTES) == {
            "id",
            "status",
            "text",
            "description",
            "priority",
            "tags",
            "due_date",
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
        "name",
        ["id", "status", "text", "description", "created_at", "color"],
    )
    def test_filter_operators_absent(self, name):
        attr = ATTRIBUTES[name]

        assert attr.filter_operators == ()
        assert attr.filter_default_operator is None

    def test_priority_sort_key_is_index(self):
        todo = TaskliList(name="t")
        low = add_item(todo, "low", priority=Priority.LOW)
        high = add_item(todo, "high", priority=Priority.HIGH)
        key = ATTRIBUTES["priority"].sort_key
        assert key

        assert key(low) == 1
        assert key(high) == 3

    def test_priority_sort_descending(self):
        assert ATTRIBUTES["priority"].sort_descending is True

    def test_tags_sort_key_empty_last_then_alpha(self):
        todo = TaskliList(name="t")
        untagged = add_item(todo, "untagged")
        zed = add_item(todo, "zed", tags=["z"])
        ace = add_item(todo, "ace", tags=["a"])
        key = ATTRIBUTES["tags"].sort_key
        assert key

        ordered = sorted([untagged, zed, ace], key=key)

        assert [i.text for i in ordered] == ["ace", "zed", "untagged"]

    def test_created_at_sort_key_is_datetime(self):
        todo = TaskliList(name="t")
        item = add_item(todo, "x", created_at=datetime(2021, 6, 1))
        key = ATTRIBUTES["created_at"].sort_key
        assert key

        assert key(item) == datetime(2021, 6, 1)

    def test_due_date_sort_key_orders_none_last(self):
        todo = TaskliList(name="t")
        early = add_item(todo, "early", due_date=datetime(2020, 1, 1))
        late = add_item(todo, "late", due_date=datetime(2020, 6, 1))
        undated = add_item(todo, "undated")
        key = ATTRIBUTES["due_date"].sort_key
        assert key

        ordered = sorted([late, undated, early], key=key)

        assert [i.text for i in ordered] == ["early", "late", "undated"]


class TestRenderFacets:
    def test_priority_render_format_label(self):
        todo = TaskliList(name="t")
        item = add_item(todo, "x", priority=Priority.HIGH)
        fmt = ATTRIBUTES["priority"].render_format
        assert fmt

        assert fmt(item) == "high"

    def test_tags_render_format_joins(self):
        todo = TaskliList(name="t")
        item = add_item(todo, "x", tags=["a", "b"])
        fmt = ATTRIBUTES["tags"].render_format
        assert fmt

        assert fmt(item) == "a, b"

    @pytest.mark.parametrize(
        "name",
        ["id", "status", "text", "description", "created_at", "color"],
    )
    def test_render_format_absent_for_nonrendered(self, name):
        assert ATTRIBUTES[name].render_format is None

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
        item = add_item(todo, "x", priority=priority)
        style = ATTRIBUTES["priority"].render_style
        assert style

        assert style(item) == color

    def test_due_date_render_format(self):
        todo = TaskliList(name="t")
        dated = add_item(todo, "x", due_date=datetime(2020, 2, 1, 13, 30))
        undated = add_item(todo, "y")
        fmt = ATTRIBUTES["due_date"].render_format
        assert fmt

        assert fmt(dated) == "2020-02-01"
        assert fmt(undated) == ""

    @pytest.mark.parametrize(
        ("due_date", "expected"),
        [
            (datetime(2020, 6, 14), "red"),
            (datetime(2020, 6, 15), "yellow"),
            (datetime(2020, 6, 16), None),
            (None, None),
        ],
        ids=["overdue", "due-today", "future", "no-due-date"],
    )
    def test_due_date_render_style(self, monkeypatch, due_date, expected):
        freeze_today(monkeypatch, date(2020, 6, 15))
        todo = TaskliList(name="t")
        item = add_item(todo, "x", due_date=due_date)
        style = ATTRIBUTES["due_date"].render_style
        assert style

        assert style(item) == expected

    def test_due_date_render_style_none_when_done(self):
        todo = TaskliList(name="t")
        item = add_item(todo, "x", due_date=datetime(2000, 1, 1))
        todo.mark_done(item.id)
        style = ATTRIBUTES["due_date"].render_style
        assert style

        assert style(item) is None

    @pytest.mark.parametrize(
        "name",
        ["id", "status", "text", "description", "tags", "created_at", "color"],
    )
    def test_render_style_absent(self, name):
        assert ATTRIBUTES[name].render_style is None


class TestAccessors:
    def test_renderable_headers_and_justify_in_column_order(self):
        columns = renderable()

        assert [column.header for column in columns] == [
            "Priority",
            "Tags",
            "Due",
        ]
        assert [column.justify for column in columns] == [
            "left",
            "left",
            "left",
        ]

    def test_renderable_carries_the_attribute_callables(self):
        priority = ATTRIBUTES["priority"]
        by_header = {column.header: column for column in renderable()}

        assert by_header["Priority"].format is priority.render_format
        assert by_header["Priority"].style is priority.render_style

    def test_sortable_keys(self):
        assert list(sortable()) == [
            "priority",
            "tags",
            "due_date",
            "created_at",
        ]

    def test_filterable_keys(self):
        assert list(filterable()) == ["priority", "tags", "due_date"]


class TestModifiers:
    def test_add_modifiers_in_column_order(self):
        assert list(modifiable("add")) == [
            "description",
            "priority",
            "tags",
            "due_date",
        ]

    def test_edit_includes_text_but_add_does_not(self):
        assert "text" in modifiable("edit")
        assert "text" not in modifiable("add")

    def test_description_is_add_and_edit_modifier(self):
        assert "description" in modifiable("add")
        assert "description" in modifiable("edit")

    def test_due_date_is_add_and_edit_modifier(self):
        assert "due_date" in modifiable("add")
        assert "due_date" in modifiable("edit")

    def test_due_date_parse_is_parse_due_date(self):
        assert ATTRIBUTES["due_date"].parse is parse_due_date

    def test_color_is_not_an_item_modifier(self):
        assert ATTRIBUTES["color"].modifier_ops == frozenset()

    def test_text_modifier_ops(self):
        assert ATTRIBUTES["text"].modifier_ops == frozenset({"edit"})

    def test_priority_parse_maps_label_to_member(self):
        parse = ATTRIBUTES["priority"].parse
        assert parse

        assert parse("high") is Priority.HIGH

    def test_tags_has_no_parse(self):
        assert ATTRIBUTES["tags"].parse is None
