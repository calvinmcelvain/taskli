from taskli.models import TaskliList
from taskli.render import render_items, render_reminder
from utils import add_subtask


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
