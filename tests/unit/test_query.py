from datetime import datetime

import pytest

from taskli.exceptions import InvalidConfigValueError
from taskli.models import (
    Criterion,
    Filter,
    Operator,
    Priority,
    Sort,
    TaskliList,
)


class TestOperator:
    def test_eq_true(self):
        assert Operator.EQ.compare(Priority.HIGH, Priority.HIGH) is True

    def test_eq_false(self):
        assert Operator.EQ.compare(Priority.HIGH, Priority.LOW) is False

    @pytest.mark.parametrize(
        ("value", "operand", "expected"),
        [
            ("Buy MILK", "milk", True),
            ("Buy milk", "eggs", False),
            (["Urgent", "Home"], "urgent", True),
            (["home"], "urgent", False),
            (5, "5", False),
            (None, "x", False),
        ],
        ids=[
            "str-substr-ci",
            "str-miss",
            "list-member-ci",
            "list-miss",
            "non-iterable",
            "none",
        ],
    )
    def test_contains(self, value, operand, expected):
        assert Operator.CONTAINS.compare(value, operand) is expected


class TestFilter:
    def test_empty_matches_every_item(self):
        todo = TaskliList(name="t")
        tagged = todo.add_item("a", tags=["x"])
        plain = todo.add_item("b")

        empty = Filter()

        assert empty.matches(tagged) is True
        assert empty.matches(plain) is True
        assert empty.apply(todo.items) == todo.items

    def test_active_false_when_empty(self):
        assert Filter().active is False

    def test_active_true_with_criteria(self):
        item_filter = Filter((Criterion("tags", Operator.CONTAINS, "x"),))

        assert item_filter.active is True

    def test_single_criterion_filters(self):
        todo = TaskliList(name="t")
        todo.add_item("keep", tags=["urgent"])
        todo.add_item("drop", tags=["later"])
        item_filter = Filter((Criterion("tags", Operator.CONTAINS, "urgent"),))

        result = item_filter.apply(todo.items)

        assert [i.text for i in result] == ["keep"]

    def test_two_criteria_and_combine(self):
        todo = TaskliList(name="t")
        todo.add_item("both", tags=["urgent"], priority=Priority.HIGH)
        todo.add_item("tag only", tags=["urgent"], priority=Priority.LOW)
        todo.add_item("prio only", tags=["later"], priority=Priority.HIGH)
        item_filter = Filter(
            (
                Criterion("tags", Operator.CONTAINS, "urgent"),
                Criterion("priority", Operator.EQ, Priority.HIGH),
            )
        )

        result = item_filter.apply(todo.items)

        assert [i.text for i in result] == ["both"]


class TestSort:
    def test_key_orders_by_created_at(self):
        todo = TaskliList(name="t")
        todo.add_item("late", created_at=datetime(2022, 1, 1))
        todo.add_item("early", created_at=datetime(2020, 1, 1))
        todo.add_item("mid", created_at=datetime(2021, 1, 1))

        ordered = sorted(todo.items, key=Sort("created_at").key)

        assert [i.text for i in ordered] == ["early", "mid", "late"]

    def test_key_orders_by_priority(self):
        todo = TaskliList(name="t")
        todo.add_item("hi", priority=Priority.HIGH)
        todo.add_item("lo", priority=Priority.LOW)
        todo.add_item("mid", priority=Priority.MEDIUM)

        ordered = sorted(todo.items, key=Sort("priority").key)

        assert [i.text for i in ordered] == ["lo", "mid", "hi"]

    def test_key_orders_by_tags(self):
        todo = TaskliList(name="t")
        todo.add_item("untagged")
        todo.add_item("z tag", tags=["z"])
        todo.add_item("a tag", tags=["a"])

        ordered = sorted(todo.items, key=Sort("tags").key)

        assert [i.text for i in ordered] == ["a tag", "z tag", "untagged"]

    def test_descending_reverses(self):
        todo = TaskliList(name="t")
        todo.add_item("lo", priority=Priority.LOW)
        todo.add_item("hi", priority=Priority.HIGH)
        descending = Sort("priority", descending=True)

        ordered = sorted(
            todo.items, key=descending.key, reverse=descending.descending
        )

        assert [i.text for i in ordered] == ["hi", "lo"]

    @pytest.mark.parametrize(
        ("value", "descending"),
        [("priority", True), ("created_at", False), ("tags", False)],
        ids=["priority", "created-at", "tags"],
    )
    def test_from_default_sort_maps_direction(self, value, descending):
        result = Sort.from_default_sort(value)

        assert isinstance(result, Sort)
        assert result.attr_key == value
        assert result.descending is descending

    def test_rejects_unknown_attr_key(self):
        with pytest.raises(InvalidConfigValueError):
            Sort("bogus")
