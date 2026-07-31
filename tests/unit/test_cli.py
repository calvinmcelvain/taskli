from todo_cli.cli import main
from todo_cli.models import Color
from todo_cli.storage import load_list


class TestAdd:
    def test_creates_list_if_missing(self, todos_env, capsys):
        exit_code = main(["work", "add", "task", "-t", "urgent"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'work'" in captured.out

    def test_add_to_inbox_implicit(self, todos_env, capsys):
        exit_code = main(["inbox", "add", "task"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'inbox'" in captured.out


class TestListItems:
    def test_shows_added_items(self, todos_env, capsys):
        main(["work", "add", "task", "-t", "urgent"])
        capsys.readouterr()

        exit_code = main(["work", "list"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_filters_by_tag(self, todos_env, capsys):
        main(["work", "add", "a", "-t", "urgent"])
        main(["work", "add", "b", "-t", "later"])
        capsys.readouterr()

        main(["work", "list", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" not in captured.out

    def test_raises_clean_error_for_missing_list(self, todos_env, capsys):
        exit_code = main(["ghost", "list"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err


class TestDoneUndone:
    def test_marks_done_and_undone(self, todos_env, capsys):
        main(["work", "add", "task"])
        capsys.readouterr()

        done_exit_code = main(["work", "done", "1"])
        done_captured = capsys.readouterr()

        undone_exit_code = main(["work", "undone", "1"])
        undone_captured = capsys.readouterr()

        assert done_exit_code == 0
        assert "marked #1 done" in done_captured.out
        assert undone_exit_code == 0
        assert "marked #1 not done" in undone_captured.out

    def test_raises_for_missing_item(self, todos_env, capsys):
        main(["work", "add", "task"])
        capsys.readouterr()

        exit_code = main(["work", "done", "999"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "no item with id 999" in captured.err


class TestEditRm:
    def test_edit_updates_text(self, todos_env, capsys):
        main(["work", "add", "task"])
        capsys.readouterr()

        edit_exit_code = main(["work", "edit", "1", "--text", "new"])
        capsys.readouterr()

        main(["work", "list"])
        list_captured = capsys.readouterr()

        assert edit_exit_code == 0
        assert "new" in list_captured.out

    def test_rm_removes_item(self, todos_env, capsys):
        main(["work", "add", "task"])
        capsys.readouterr()

        rm_exit_code = main(["work", "rm", "1"])
        capsys.readouterr()

        main(["work", "list"])
        list_captured = capsys.readouterr()

        assert rm_exit_code == 0
        assert "task" not in list_captured.out


class TestPrune:
    def test_prune_removes_done_items_only(self, todos_env, capsys):
        main(["work", "add", "done task"])
        main(["work", "add", "open task"])
        main(["work", "done", "1"])
        capsys.readouterr()

        main(["work", "prune"])
        capsys.readouterr()

        main(["work", "list"])
        list_captured = capsys.readouterr()

        assert "done task" not in list_captured.out
        assert "open task" in list_captured.out

    def test_prune_reports_count_in_message(self, todos_env, capsys):
        main(["work", "add", "task"])
        main(["work", "done", "1"])
        capsys.readouterr()

        main(["work", "prune"])

        captured = capsys.readouterr()
        assert "pruned 1 item" in captured.out

    def test_prune_noop_when_no_done_items(self, todos_env, capsys):
        main(["work", "add", "task"])
        capsys.readouterr()

        prune_exit_code = main(["work", "prune"])
        prune_captured = capsys.readouterr()

        main(["work", "list"])
        list_captured = capsys.readouterr()

        assert prune_exit_code == 0
        assert "pruned 0 item" in prune_captured.out
        assert "task" in list_captured.out

    def test_prune_raises_clean_error_for_missing_list(
        self, todos_env, capsys
    ):
        exit_code = main(["ghost", "prune"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err

    def test_prune_implicit_inbox(self, todos_env, capsys):
        main(["add", "task"])
        main(["done", "1"])
        capsys.readouterr()

        main(["prune"])
        capsys.readouterr()

        main(["list"])
        list_captured = capsys.readouterr()

        assert "task" not in list_captured.out


class TestTags:
    def test_shows_distinct_tags(self, todos_env, capsys):
        main(["work", "add", "a", "-t", "urgent", "-t", "soon"])
        main(["work", "add", "b", "-t", "urgent"])
        capsys.readouterr()

        main(["work", "tags"])

        captured = capsys.readouterr()
        assert captured.out.split() == ["soon", "urgent"]


class TestListsCommand:
    def test_lists_all_list_names(self, todos_env, capsys):
        main(["work", "add", "task"])
        main(["new-list", "groceries"])
        capsys.readouterr()

        main(["lists"])

        captured = capsys.readouterr()
        assert "work" in captured.out
        assert "groceries" in captured.out

    def test_shows_message_when_empty(self, todos_env, capsys):
        main(["lists"])

        captured = capsys.readouterr()
        assert "no lists yet" in captured.out

    def test_lists_shows_nested_sublist(self, todos_env, capsys):
        main(["new-list", "work"])
        main(["new-list", "work.meetings"])
        capsys.readouterr()

        main(["lists"])

        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        parent_line = next(line for line in lines if line.strip() == "work")
        child_line = next(
            line
            for line in lines
            if line.strip().endswith("meetings") and line.strip() != "meetings"
        )

        assert lines.index(child_line) > lines.index(parent_line)

    def test_lists_unrelated_sibling(self, todos_env, capsys):
        main(["new-list", "work"])
        main(["new-list", "work-log"])
        main(["new-list", "work.meetings"])
        capsys.readouterr()

        main(["lists"])

        captured = capsys.readouterr()
        lines = [line.strip() for line in captured.out.splitlines()]
        parent_index = lines.index("work")
        child_index = next(
            i
            for i, line in enumerate(lines)
            if line.endswith("meetings") and line != "meetings"
        )

        assert child_index == parent_index + 1


class TestNewListRmList:
    def test_new_list_creates_empty_list(self, todos_env, capsys):
        exit_code = main(["new-list", "groceries"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "created list 'groceries'" in captured.out

    def test_new_list_rejects_reserved_name(self, todos_env, capsys):
        exit_code = main(["new-list", "add"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "reserved" in captured.err

    def test_new_list_rejects_excessive_depth(self, todos_env, capsys):
        exit_code = main(["new-list", "work.meetings.boring.extra"])

        captured = capsys.readouterr()

        assert exit_code == 1
        assert "nested too deep" in captured.err

    def test_new_list_with_color(self, todos_env, capsys):
        exit_code = main(["new-list", "groceries", "-c", "coral"])

        assert exit_code == 0
        assert load_list(todos_env, "groceries").color is Color.CORAL

    def test_new_list_with_color_shown_in_lists(self, todos_env, capsys):
        main(["new-list", "groceries", "-c", "coral"])
        capsys.readouterr()

        exit_code = main(["lists"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "groceries" in captured.out

    def test_new_list_rejects_invalid_color(self, todos_env, capsys):
        exit_code = main(["new-list", "groceries", "-c", "notacolor"])

        captured = capsys.readouterr()

        assert exit_code == 2
        assert "invalid choice" in captured.err

    def test_rm_list_deletes_with_confirmation(
        self, todos_env, monkeypatch, capsys
    ):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        main(["new-list", "groceries"])
        capsys.readouterr()

        rm_exit_code = main(["rm-list", "groceries"])
        capsys.readouterr()

        main(["lists"])
        lists_captured = capsys.readouterr()

        assert rm_exit_code == 0
        assert "groceries" not in lists_captured.out

    def test_new_sublist_creates_missing_parent(self, todos_env, capsys):
        exit_code = main(["new-list", "work.meetings"])
        capsys.readouterr()

        main(["lists"])
        lists_captured = capsys.readouterr()

        assert exit_code == 0
        assert "work" in lists_captured.out
        assert "meetings" in lists_captured.out

    def test_rm_list_cascades(self, todos_env, monkeypatch, capsys):
        prompts = []
        monkeypatch.setattr(
            "builtins.input", lambda p: prompts.append(p) or "y"
        )
        main(["work", "add", "task"])
        main(["work.meetings", "add", "sub-task"])
        capsys.readouterr()

        main(["rm-list", "work"])
        capsys.readouterr()

        main(["lists"])
        lists_captured = capsys.readouterr()

        assert "work" not in lists_captured.out
        assert "meetings" not in lists_captured.out
        assert "work.meetings" in prompts[0]


class TestEditListCommand:
    def test_changes_color(self, todos_env, capsys):
        main(["new-list", "work"])
        capsys.readouterr()

        exit_code = main(["edit-list", "work", "-c", "teal"])

        capsys.readouterr()

        assert exit_code == 0
        assert load_list(todos_env, "work").color is Color.TEAL

    def test_colored_list_items_still_render(self, todos_env, capsys):
        main(["new-list", "work"])
        main(["work", "add", "task"])
        main(["edit-list", "work", "-c", "teal"])
        capsys.readouterr()

        exit_code = main(["work", "list"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_missing_list_errors(self, todos_env, capsys):
        exit_code = main(["edit-list", "ghost", "-c", "teal"])

        captured = capsys.readouterr()

        assert exit_code == 1
        assert "does not exist" in captured.err

    def test_rejects_invalid_color(self, todos_env, capsys):
        main(["new-list", "work"])
        capsys.readouterr()

        exit_code = main(["edit-list", "work", "-c", "notacolor"])

        captured = capsys.readouterr()

        assert exit_code == 2
        assert "invalid choice" in captured.err

    def test_requires_color_flag(self, todos_env, capsys):
        main(["new-list", "work"])
        capsys.readouterr()

        exit_code = main(["edit-list", "work"])

        captured = capsys.readouterr()

        assert exit_code == 2
        assert "required" in captured.err


class TestDefaultListAction:
    def test_bare_invocation_shows_inbox(self, todos_env, capsys):
        exit_code = main([])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "inbox" in captured.out

    def test_list_name_alone_shows_items(self, todos_env, capsys):
        main(["work", "add", "task"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_list_name_with_tag_filter(self, todos_env, capsys):
        main(["work", "add", "a", "-t", "urgent"])
        main(["work", "add", "b", "-t", "later"])
        capsys.readouterr()

        main(["work", "-t", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" not in captured.out

    def test_shows_child_section(self, todos_env, capsys):
        main(["work", "add", "task"])
        main(["work.meetings", "add", "sub-task"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()

        assert exit_code == 0
        assert "task" in captured.out
        assert "sub-task" in captured.out
        assert "meetings" in captured.out

    def test_grandchild_shown_under_top_ancestor(self, todos_env, capsys):
        main(["work.meetings.notes", "add", "deep-task"])
        capsys.readouterr()

        main(["work"])
        top_captured = capsys.readouterr()

        main(["work.meetings"])
        mid_captured = capsys.readouterr()

        assert "deep-task" in top_captured.out
        assert "meetings" in top_captured.out
        assert "notes" in top_captured.out
        assert "deep-task" in mid_captured.out

    def test_tag_filter_applies_to_child_sections(self, todos_env, capsys):
        main(["work", "add", "a", "-t", "urgent"])
        main(["work.meetings", "add", "b", "-t", "urgent"])
        main(["work.meetings", "add", "c", "-t", "later"])
        capsys.readouterr()

        main(["work", "-t", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" in captured.out
        assert "c" not in captured.out

    def test_empty_child_section_shown_without_filter(self, todos_env, capsys):
        main(["new-list", "work.meetings"])
        capsys.readouterr()

        main(["work"])

        captured = capsys.readouterr()
        assert "meetings" in captured.out


class TestImplicitAdd:
    def test_bare_text_adds_to_inbox(self, todos_env, capsys):
        exit_code = main(["this is a task"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'inbox'" in captured.out

    def test_list_and_text_adds_to_list(self, todos_env, capsys):
        exit_code = main(["list1", "task 2"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'list1'" in captured.out

    def test_existing_list_name_still_shows_list(self, todos_env, capsys):
        main(["work", "add", "task"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_bare_inbox_shows_inbox_even_when_empty(self, todos_env, capsys):
        exit_code = main(["inbox"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "inbox" in captured.out

    def test_list_and_text_with_flags(self, todos_env, capsys):
        exit_code = main(["work", "task", "-t", "urgent"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'work'" in captured.out

    def test_bare_text_with_flags_adds_to_inbox(self, todos_env, capsys):
        exit_code = main(["buy milk", "-p", "high"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'inbox'" in captured.out
