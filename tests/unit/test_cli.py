from taskli.cli import main
from taskli.models import Color, Priority
from taskli.storage import load_list


class TestAdd:
    def test_creates_list_if_missing(self, todos_env, capsys):
        exit_code = main(["work", "-a", "task", "-t", "urgent"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'work'" in captured.out

    def test_add_to_inbox_by_default(self, todos_env, capsys):
        exit_code = main(["-a", "task"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'inbox'" in captured.out

    def test_repeated_add_flag_adds_each_item(self, todos_env, capsys):
        exit_code = main(["-a", "buy", "milk", "-a", "buy", "eggs"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'inbox'" in captured.out
        assert "added #2 to 'inbox'" in captured.out

    def test_repeated_add_flag_shares_priority_and_tags(
        self, todos_env, capsys
    ):
        main(
            [
                "-a",
                "buy",
                "milk",
                "-a",
                "buy",
                "eggs",
                "-p",
                "high",
                "-t",
                "urgent",
            ]
        )
        capsys.readouterr()

        todo_list = load_list(todos_env, "inbox")

        assert len(todo_list.items) == 2
        assert all(item.priority == Priority.HIGH for item in todo_list.items)
        assert all(item.tags == ["urgent"] for item in todo_list.items)

    def test_unquoted_bare_text_errors_unrecognized(self, todos_env, capsys):
        exit_code = main(["buy", "milk"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "unrecognized arguments" in captured.err

    def test_quoted_bare_text_errors_list_not_found(self, todos_env, capsys):
        exit_code = main(["buy milk"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err

    def test_former_action_word_is_now_a_valid_list_name(
        self, todos_env, capsys
    ):
        exit_code = main(["add", "-a", "buy milk"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'add'" in captured.out

    def test_tag_flag_invalid_outside_add_or_edit(self, todos_env, capsys):
        exit_code = main(["work", "-d", "1", "-t", "urgent"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "only valid with" in captured.err

    def test_priority_flag_invalid_outside_add_or_edit(
        self, todos_env, capsys
    ):
        exit_code = main(["work", "--prune", "-p", "high"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "only valid with" in captured.err

    def test_filter_tag_invalid_outside_view(self, todos_env, capsys):
        exit_code = main(["work", "-a", "task", "-f", "urgent"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "only valid with" in captured.err

    def test_text_flag_invalid_outside_edit(self, todos_env, capsys):
        exit_code = main(["work", "--text", "new"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "only valid with" in captured.err

    def test_combining_two_action_flags_errors(self, todos_env, capsys):
        exit_code = main(["-a", "task", "-d", "1"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "not allowed with argument" in captured.err


class TestListItems:
    def test_shows_added_items(self, todos_env, capsys):
        main(["work", "-a", "task", "-t", "urgent"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_filters_by_tag(self, todos_env, capsys):
        main(["work", "-a", "a", "-t", "urgent"])
        main(["work", "-a", "b", "-t", "later"])
        capsys.readouterr()

        main(["work", "-f", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" not in captured.out

    def test_explicit_list_flag_matches_default_view(self, todos_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-l"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_raises_clean_error_for_missing_list(self, todos_env, capsys):
        exit_code = main(["ghost"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err


class TestDoneUndone:
    def test_marks_done_and_undone(self, todos_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        done_exit_code = main(["work", "-d", "1"])
        done_captured = capsys.readouterr()

        undone_exit_code = main(["work", "-u", "1"])
        undone_captured = capsys.readouterr()

        assert done_exit_code == 0
        assert "marked #1 done" in done_captured.out
        assert undone_exit_code == 0
        assert "marked #1 not done" in undone_captured.out

    def test_raises_for_missing_item(self, todos_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-d", "999"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "no item with id 999" in captured.err


class TestEditRm:
    def test_edit_updates_text(self, todos_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        edit_exit_code = main(["work", "-e", "1", "--text", "new"])
        capsys.readouterr()

        main(["work"])
        list_captured = capsys.readouterr()

        assert edit_exit_code == 0
        assert "new" in list_captured.out

    def test_rm_removes_item(self, todos_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        rm_exit_code = main(["work", "-r", "1"])
        capsys.readouterr()

        main(["work"])
        list_captured = capsys.readouterr()

        assert rm_exit_code == 0
        assert "task" not in list_captured.out


class TestPrune:
    def test_prune_removes_done_items_only(self, todos_env, capsys):
        main(["work", "-a", "done task"])
        main(["work", "-a", "open task"])
        main(["work", "-d", "1"])
        capsys.readouterr()

        main(["work", "--prune"])
        capsys.readouterr()

        main(["work"])
        list_captured = capsys.readouterr()

        assert "done task" not in list_captured.out
        assert "open task" in list_captured.out

    def test_prune_reports_count_in_message(self, todos_env, capsys):
        main(["work", "-a", "task"])
        main(["work", "-d", "1"])
        capsys.readouterr()

        main(["work", "--prune"])

        captured = capsys.readouterr()
        assert "pruned 1 item" in captured.out

    def test_prune_noop_when_no_done_items(self, todos_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        prune_exit_code = main(["work", "--prune"])
        prune_captured = capsys.readouterr()

        main(["work"])
        list_captured = capsys.readouterr()

        assert prune_exit_code == 0
        assert "pruned 0 item" in prune_captured.out
        assert "task" in list_captured.out

    def test_prune_raises_clean_error_for_missing_list(
        self, todos_env, capsys
    ):
        exit_code = main(["ghost", "--prune"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err

    def test_prune_implicit_inbox(self, todos_env, capsys):
        main(["-a", "task"])
        main(["-d", "1"])
        capsys.readouterr()

        main(["--prune"])
        capsys.readouterr()

        main([])
        list_captured = capsys.readouterr()

        assert "task" not in list_captured.out


class TestTags:
    def test_shows_distinct_tags(self, todos_env, capsys):
        main(["work", "-a", "a", "-t", "urgent", "-t", "soon"])
        main(["work", "-a", "b", "-t", "urgent"])
        capsys.readouterr()

        main(["work", "--tags"])

        captured = capsys.readouterr()
        assert captured.out.split() == ["soon", "urgent"]


class TestListsCommand:
    def test_lists_all_list_names(self, todos_env, capsys):
        main(["work", "-a", "task"])
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


class TestAllCommand:
    def test_shows_every_list_items(self, todos_env, capsys):
        main(["work", "-a", "finish report"])
        main(["groceries", "-a", "buy milk"])
        capsys.readouterr()

        main(["all"])

        captured = capsys.readouterr()
        assert "work" in captured.out
        assert "finish report" in captured.out
        assert "groceries" in captured.out
        assert "buy milk" in captured.out

    def test_shows_message_when_empty(self, todos_env, capsys):
        main(["all"])

        captured = capsys.readouterr()
        assert "no lists yet" in captured.out

    def test_shows_sublist_under_parent(self, todos_env, capsys):
        main(["work", "-a", "finish report"])
        main(["work.meetings", "-a", "sync with design"])
        capsys.readouterr()

        main(["all"])

        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        parent_index = next(
            i for i, line in enumerate(lines) if line.strip() == "work"
        )
        child_index = next(
            i
            for i, line in enumerate(lines)
            if line.strip().endswith("meetings") and line.strip() != "meetings"
        )

        assert child_index > parent_index
        assert "sync with design" in captured.out


class TestNewListRmList:
    def test_new_list_creates_empty_list(self, todos_env, capsys):
        exit_code = main(["new-list", "groceries"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "created list 'groceries'" in captured.out

    def test_new_list_allows_former_action_word(self, todos_env, capsys):
        exit_code = main(["new-list", "add"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "created list 'add'" in captured.out

    def test_new_list_rejects_reserved_top_level_word(self, todos_env, capsys):
        exit_code = main(["new-list", "lists"])

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
        main(["work", "-a", "task"])
        main(["work.meetings", "-a", "sub-task"])
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
        main(["work", "-a", "task"])
        main(["edit-list", "work", "-c", "teal"])
        capsys.readouterr()

        exit_code = main(["work"])

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
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_list_name_with_tag_filter(self, todos_env, capsys):
        main(["work", "-a", "a", "-t", "urgent"])
        main(["work", "-a", "b", "-t", "later"])
        capsys.readouterr()

        main(["work", "-f", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" not in captured.out

    def test_shows_child_section(self, todos_env, capsys):
        main(["work", "-a", "task"])
        main(["work.meetings", "-a", "sub-task"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()

        assert exit_code == 0
        assert "task" in captured.out
        assert "sub-task" in captured.out
        assert "meetings" in captured.out

    def test_grandchild_shown_under_top_ancestor(self, todos_env, capsys):
        main(["work.meetings.notes", "-a", "deep-task"])
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
        main(["work", "-a", "a", "-t", "urgent"])
        main(["work.meetings", "-a", "b", "-t", "urgent"])
        main(["work.meetings", "-a", "c", "-t", "later"])
        capsys.readouterr()

        main(["work", "-f", "urgent"])

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
