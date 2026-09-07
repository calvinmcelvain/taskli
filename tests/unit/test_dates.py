from datetime import date, datetime

import pytest

from taskli.exceptions import InvalidModifierValueError
from taskli.models.dates import parse_agenda_window, parse_due_date
from utils import freeze_today


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    freeze_today(monkeypatch, date(2026, 3, 10))


class TestParseDueDate:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("today", datetime(2026, 3, 10)),
            ("  TODAY ", datetime(2026, 3, 10)),
            ("tomorrow", datetime(2026, 3, 11)),
            ("next week", datetime(2026, 3, 17)),
            ("Next Week", datetime(2026, 3, 17)),
            ("1 day", datetime(2026, 3, 11)),
            ("3 days", datetime(2026, 3, 13)),
            ("1 week", datetime(2026, 3, 17)),
            ("2 weeks", datetime(2026, 3, 24)),
            ("04-15-2026", datetime(2026, 4, 15)),
            ("monday", datetime(2026, 3, 16)),
            ("mon", datetime(2026, 3, 16)),
            ("Wed", datetime(2026, 3, 11)),
            ("sunday", datetime(2026, 3, 15)),
            ("tuesday", datetime(2026, 3, 17)),
        ],
        ids=[
            "today",
            "today-padded-caps",
            "tomorrow",
            "next-week",
            "next-week-caps",
            "one-day",
            "n-days",
            "one-week",
            "n-weeks",
            "explicit-date",
            "weekday-full",
            "weekday-abbrev",
            "weekday-caps",
            "weekday-later-this-week",
            "weekday-today-rolls-to-next-week",
        ],
    )
    def test_accepts(self, raw, expected):
        assert parse_due_date(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "overdue",
            "someday",
            "2026-04-15",
            "0 days",
            "-3 days",
            "13-40-2026",
            "tues",
            "mondays",
        ],
        ids=[
            "empty",
            "overdue",
            "someday",
            "iso",
            "zero-days",
            "negative-days",
            "out-of-range-date",
            "weekday-wrong-abbrev",
            "weekday-plural",
        ],
    )
    def test_rejects(self, raw):
        with pytest.raises(InvalidModifierValueError):
            parse_due_date(raw)

    def test_error_names_accepted_forms(self):
        with pytest.raises(InvalidModifierValueError) as excinfo:
            parse_due_date("someday")

        message = str(excinfo.value)

        assert "today" in message
        assert "tomorrow" in message
        assert "next week" in message
        assert "N days" in message
        assert "N weeks" in message
        assert "weekday" in message
        assert "MM-DD-YYYY" in message


class TestParseAgendaWindow:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("today", "today"),
            ("  TODAY ", "today"),
            ("week", "week"),
            ("Week", "week"),
            ("overdue", "overdue"),
            ("OVERDUE", "overdue"),
            ("3", "3"),
            ("14", "14"),
        ],
        ids=[
            "today",
            "today-padded-caps",
            "week",
            "week-caps",
            "overdue",
            "overdue-caps",
            "digits",
            "multi-digit",
        ],
    )
    def test_accepts(self, raw, expected):
        assert parse_agenda_window(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        ["", "someday", "0", "-3", "1.5"],
        ids=["empty", "garbage", "zero", "negative", "float"],
    )
    def test_rejects(self, raw):
        with pytest.raises(InvalidModifierValueError):
            parse_agenda_window(raw)
