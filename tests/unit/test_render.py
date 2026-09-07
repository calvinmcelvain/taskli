from datetime import date, datetime

import pytest
from rich.console import Console

import taskli.render as render_module
from taskli.models import Priority, TaskliList
from taskli.render import (
    render_agenda,
    render_error,
    render_items,
    render_list_names,
    render_reminder,
    render_value,
)
from utils import add_item, add_subtask, freeze_today


@pytest.fixture
def recording_console(monkeypatch):
    console = Console(record=True)
    monkeypatch.setattr(render_module, "_console", console)
    return console


@pytest.fixture
def recording_err_console(monkeypatch):
    console = Console(record=True)
    monkeypatch.setattr(render_module, "_err_console", console)
    return console


class TestRenderItems:
    def test_child_renders_as_own_row(self, capsys):
        todo = TaskliList(name="chores")
        todo.add_item("alpha")
        add_subtask(todo, "1", "beta")

        render_items("chores", todo.items)

        out = capsys.readouterr().out
        lines = out.splitlines()
        child_line = next(line for line in lines if "beta" in line)
        assert "1.1" in child_line

    def test_child_row_indented_past_parent(self, capsys):
        todo = TaskliList(name="chores")
        todo.add_item("alpha")
        add_subtask(todo, "1", "beta")

        render_items("chores", todo.items)

        out = capsys.readouterr().out
        lines = out.splitlines()
        parent_line = next(line for line in lines if "alpha" in line)
        child_line = next(line for line in lines if "beta" in line)
        assert child_line.index("beta") > parent_line.index("alpha")

    def test_grandchild_indented_past_child(self, capsys):
        todo = TaskliList(name="chores")
        todo.add_item("alpha")
        add_subtask(todo, "1", "beta")
        add_subtask(todo, "1.1", "gamma")

        render_items("chores", todo.items)

        out = capsys.readouterr().out
        lines = out.splitlines()
        child_line = next(line for line in lines if "beta" in line)
        grandchild_line = next(line for line in lines if "gamma" in line)
        assert "1.1.1" in grandchild_line
        assert grandchild_line.index("gamma") > child_line.index("beta")

    def test_done_item_text_dim(self, recording_console):
        todo = TaskliList(name="chores")
        add_item(todo, "wash up")
        todo.mark_done("1")

        render_items("chores", todo.items)

        lines = recording_console.export_text(styles=True).splitlines()
        text_line = next(line for line in lines if "wash up" in line)
        assert "\x1b[2m" in text_line

    def test_styled_cell_padding_not_colored(self, recording_console):
        todo = TaskliList(name="chores")
        add_item(todo, "wash up", priority=Priority.HIGH)

        render_items("chores", todo.items)

        lines = recording_console.export_text(styles=True).splitlines()
        row = next(line for line in lines if "high" in line)
        assert "\x1b[31mhigh\x1b[0m" in row


class TestRenderReminder:
    def test_shows_both_counts(self, capsys):
        render_reminder(2, 1)

        err = capsys.readouterr().err
        assert "2 overdue" in err
        assert "1 due today" in err

    def test_omits_zero_count(self, capsys):
        render_reminder(0, 1)

        err = capsys.readouterr().err
        assert "overdue" not in err
        assert "1 due today" in err

    def test_writes_to_stderr_not_stdout(self, capsys):
        render_reminder(1, 0)

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "1 overdue" in captured.err

    def test_bold_yellow_prefix(self, recording_err_console):
        render_reminder(1, 0)

        out = recording_err_console.export_text(styles=True)
        assert "\x1b[1;33m" in out


class TestRenderError:
    def test_bold_red_prefix(self, recording_err_console):
        render_error("boom")

        out = recording_err_console.export_text(styles=True)
        assert "error:" in out
        assert "\x1b[1;31m" in out


class TestRenderValue:
    def test_bracket_value_printed_verbatim(self, capsys):
        render_value("[bold]/x/y[/bold]")

        assert "[bold]/x/y[/bold]" in capsys.readouterr().out


class TestRenderAgenda:
    def test_empty_rows_prints_dim_message(self, capsys):
        render_agenda([])

        out = capsys.readouterr().out
        assert "nothing on the agenda." in out

    def test_row_content(self, capsys):
        work = TaskliList(name="work")
        work.add_item("chores")
        item = add_subtask(work, "1", "ship", due_date=datetime(2026, 9, 10))

        render_agenda([("work", item)])

        out = capsys.readouterr().out
        assert "work" in out
        assert "1.1" in out
        assert "ship" in out
        assert "2026-09-10" in out

    def test_display_name_uses_delimiter(self, capsys):
        work = TaskliList(name="work.meetings")
        item = add_item(work, "sync", due_date=datetime(2026, 9, 10))

        render_agenda([("work.meetings", item)], delimiter="/")

        out = capsys.readouterr().out
        assert "work/meetings" in out

    def test_overdue_and_due_today_styled_differently(
        self, recording_console, monkeypatch
    ):
        freeze_today(monkeypatch, date(2026, 9, 7))
        work = TaskliList(name="work")
        overdue = add_item(work, "late", due_date=datetime(2026, 9, 6))
        due_today = add_item(work, "today", due_date=datetime(2026, 9, 7))

        render_agenda([("work", overdue), ("work", due_today)])

        lines = recording_console.export_text(styles=True).splitlines()
        overdue_line = next(line for line in lines if "2026-09-06" in line)
        due_today_line = next(line for line in lines if "2026-09-07" in line)
        assert "\x1b[31m" in overdue_line
        assert "\x1b[33m" in due_today_line


class TestRenderListNames:
    def test_default_list_bold_siblings_plain(self, recording_console):
        render_list_names([("alpha", None), ("beta", None)], "alpha")

        lines = recording_console.export_text(styles=True).splitlines()
        assert "\x1b[1malpha\x1b[0m" in next(
            line for line in lines if "alpha" in line
        )
        assert "\x1b[1mbeta" not in next(
            line for line in lines if "beta" in line
        )
