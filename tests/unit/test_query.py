from datetime import date, datetime

import pytest

from taskli.exceptions import (
    InvalidConfigValueError,
    InvalidModifierValueError,
)
from taskli.models import (
    Criterion,
    Filter,
    Operator,
    Priority,
    Sort,
    TaskliList,
    due_to_criteria,
)
from utils import add_item, freeze_today


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

    @pytest.mark.parametrize(
        ("value", "operand", "expected"),
        [
            (datetime(2020, 1, 1), datetime(2021, 1, 1), True),
            (datetime(2021, 1, 1), datetime(2020, 1, 1), False),
            (datetime(2020, 1, 1), datetime(2020, 1, 1), False),
            (None, datetime(2021, 1, 1), False),
            (datetime(2020, 1, 1), None, False),
        ],
        ids=[
            "before",
            "after",
            "equal",
            "none-value",
            "none-operand",
        ],
    )
    def test_lt(self, value, operand, expected):
        assert Operator.LT.compare(value, operand) is expected


class TestFilter:
    def test_empty_matches_every_item(self):
        todo = TaskliList(name="t")
        tagged = add_item(todo, "a", tags=["x"])
        plain = add_item(todo, "b")

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
        add_item(todo, "keep", tags=["urgent"])
        add_item(todo, "drop", tags=["later"])
        item_filter = Filter((Criterion("tags", Operator.CONTAINS, "urgent"),))

        result = item_filter.apply(todo.items)

        assert [i.text for i in result] == ["keep"]

    def test_two_criteria_and_combine(self):
        todo = TaskliList(name="t")
        add_item(todo, "both", tags=["urgent"], priority=Priority.HIGH)
        add_item(todo, "tag only", tags=["urgent"], priority=Priority.LOW)
        add_item(todo, "prio only", tags=["later"], priority=Priority.HIGH)
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
        add_item(todo, "late", created_at=datetime(2022, 1, 1))
        add_item(todo, "early", created_at=datetime(2020, 1, 1))
        add_item(todo, "mid", created_at=datetime(2021, 1, 1))

        ordered = sorted(todo.items, key=Sort("created_at").key)

        assert [i.text for i in ordered] == ["early", "mid", "late"]

    def test_key_orders_by_priority(self):
        todo = TaskliList(name="t")
        add_item(todo, "hi", priority=Priority.HIGH)
        add_item(todo, "lo", priority=Priority.LOW)
        add_item(todo, "mid", priority=Priority.MEDIUM)

        ordered = sorted(todo.items, key=Sort("priority").key)

        assert [i.text for i in ordered] == ["lo", "mid", "hi"]

    def test_key_orders_by_tags(self):
        todo = TaskliList(name="t")
        add_item(todo, "untagged")
        add_item(todo, "z tag", tags=["z"])
        add_item(todo, "a tag", tags=["a"])

        ordered = sorted(todo.items, key=Sort("tags").key)

        assert [i.text for i in ordered] == ["a tag", "z tag", "untagged"]

    def test_descending_reverses(self):
        todo = TaskliList(name="t")
        add_item(todo, "lo", priority=Priority.LOW)
        add_item(todo, "hi", priority=Priority.HIGH)
        descending = Sort("priority", descending=True)

        ordered = sorted(
            todo.items, key=descending.key, reverse=descending.descending
        )

        assert [i.text for i in ordered] == ["hi", "lo"]

    @pytest.mark.parametrize(
        ("value", "descending"),
        [
            ("priority", True),
            ("created_at", False),
            ("tags", False),
            ("due_date", False),
        ],
        ids=["priority", "created-at", "tags", "due-date"],
    )
    def test_from_default_sort_maps_direction(self, value, descending):
        result = Sort.from_default_sort(value)

        assert isinstance(result, Sort)
        assert result.attr_key == value
        assert result.descending is descending

    def test_rejects_unknown_attr_key(self):
        with pytest.raises(InvalidConfigValueError):
            Sort("bogus")

    @pytest.mark.parametrize(
        "attr_key", ["id", "status", "text", "description", "color"]
    )
    def test_rejects_unsortable_attr_key(self, attr_key):
        with pytest.raises(InvalidConfigValueError):
            Sort(attr_key)

    def test_from_default_sort_rejects_unknown_value(self):
        with pytest.raises(InvalidConfigValueError):
            Sort.from_default_sort("bogus")


class TestDueToCriteria:
    @pytest.mark.parametrize(
        ("raw", "operand"),
        [
            ("today", datetime(2026, 3, 10)),
            ("03-15-2026", datetime(2026, 3, 15)),
        ],
        ids=["today", "explicit-date"],
    )
    def test_builds_single_day_criterion(self, monkeypatch, raw, operand):
        freeze_today(monkeypatch, date(2026, 3, 10))

        (criterion,) = due_to_criteria(raw)

        assert isinstance(criterion, Criterion)
        assert criterion.attr_key == "due_date"
        assert criterion.operator is Operator.EQ
        assert criterion.operand == operand

    def test_overdue_builds_date_and_not_done_criteria(self, monkeypatch):
        freeze_today(monkeypatch, date(2026, 3, 10))

        criteria = due_to_criteria("overdue")

        assert criteria == (
            Criterion("due_date", Operator.LT, datetime(2026, 3, 10)),
            Criterion("done", Operator.EQ, False),
        )

    def test_rejects_unparseable_token(self, monkeypatch):
        freeze_today(monkeypatch, date(2026, 3, 10))

        with pytest.raises(InvalidModifierValueError):
            due_to_criteria("someday")

    def test_overdue_filter_skips_undated_and_done_items(self, monkeypatch):
        freeze_today(monkeypatch, date(2026, 3, 10))
        todo = TaskliList(name="t")
        add_item(todo, "past", due_date=datetime(2026, 3, 9))
        add_item(todo, "now", due_date=datetime(2026, 3, 10))
        add_item(todo, "soon", due_date=datetime(2026, 3, 11))
        add_item(todo, "none")
        done_past = add_item(todo, "done", due_date=datetime(2026, 3, 1))
        todo.mark_done(done_past.id)

        result = Filter(due_to_criteria("overdue")).apply(todo.items)

        assert [i.text for i in result] == ["past"]

    def test_today_filter_matches_only_today(self, monkeypatch):
        freeze_today(monkeypatch, date(2026, 3, 10))
        todo = TaskliList(name="t")
        add_item(todo, "past", due_date=datetime(2026, 3, 9))
        add_item(todo, "now", due_date=datetime(2026, 3, 10))
        add_item(todo, "soon", due_date=datetime(2026, 3, 11))
        add_item(todo, "none")

        result = Filter(due_to_criteria("today")).apply(todo.items)

        assert [i.text for i in result] == ["now"]
