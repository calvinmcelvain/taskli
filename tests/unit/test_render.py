from taskli.models import TaskliList
from taskli.render import render_items
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
