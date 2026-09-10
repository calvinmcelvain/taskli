import argparse
import subprocess
import sys
from datetime import date, datetime, timedelta

import pytest

from taskli.__version__ import __version__
from taskli.cli import MODIFIER_FLAGS, _complete_list_names, main
from taskli.models import registry
from taskli.models.attributes import Color, Priority, Status
from taskli.storage import config_file_path, load_config, load_list
from utils import resource_text


class TestColdImport:
    def test_import_skips_pydantic_and_rich(self):
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                "import taskli.cli, sys;"
                " sys.exit(1 if ('pydantic' in sys.modules"
                " or 'rich' in sys.modules) else 0)",
            ],
            capture_output=True,
        )

        assert result.returncode == 0, result.stderr.decode()


class TestAdd:
    def test_creates_list_if_missing(self, taskli_env, capsys):
        exit_code = main(["work", "-a", "task", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'work'" in captured.out

    def test_defaults_to_inbox(self, taskli_env, capsys):
        exit_code = main(["-a", "task"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'inbox'" in captured.out

    def test_repeated_add_flags(self, taskli_env, capsys):
        exit_code = main(["-a", "buy", "milk", "-a", "buy", "eggs"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'inbox'" in captured.out
        assert "added #2 to 'inbox'" in captured.out

    def test_repeated_flag_shares(self, taskli_env, capsys):
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
                "--tag",
                "urgent",
            ]
        )
        capsys.readouterr()

        task_list = load_list(taskli_env, "inbox")

        assert len(task_list.items) == 2
        assert all(item.priority == Priority.HIGH for item in task_list.items)
        assert all(item.tags == ["urgent"] for item in task_list.items)

    def test_unquoted_bare_text_errors(self, taskli_env, capsys):
        exit_code = main(["buy", "milk"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "unrecognized arguments" in captured.err

    def test_quoted_bare_text_errors(self, taskli_env, capsys):
        exit_code = main(["buy milk"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err

    def test_combining_two_action_flags_errors(self, taskli_env, capsys):
        exit_code = main(["-a", "task", "-d", "1"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "cannot be combined with" in captured.err

    def test_uses_configured_default_priority(self, taskli_env, capsys):
        main(["--config", "default_priority", "high"])
        capsys.readouterr()

        main(["-a", "task"])
        capsys.readouterr()

        task_list = load_list(taskli_env, "inbox")
        assert task_list.items[0].priority == Priority.HIGH

    def test_add_sorts_and_reindexes_by_default_sort(self, taskli_env, capsys):
        main(["--config", "default_sort", "priority"])
        main(["work", "--new"])
        main(["work", "-a", "low", "task", "-p", "low"])
        capsys.readouterr()

        exit_code = main(["work", "-a", "high", "task", "-p", "high"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'work'" in captured.out

        task_list = load_list(taskli_env, "work")
        assert [item.text for item in task_list.items] == [
            "high task",
            "low task",
        ]


class TestSubtasks:
    def test_under_nests_new_item(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        capsys.readouterr()

        exit_code = main(["work", "-a", "child", "--under", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1.1 to 'work'" in captured.out
        child = load_list(taskli_env, "work").items[0].children[0]
        assert child.text == "child"
        assert child.id == "1.1"

    def test_view_shows_nested_path(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "child", "--under", "1"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "1.1" in captured.out
        assert "child" in captured.out

    def test_done_marks_nested_item(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "child", "--under", "1"])
        capsys.readouterr()

        exit_code = main(["work", "-d", "1.1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "marked #1.1 done in 'work'" in captured.out
        assert load_list(taskli_env, "work").items[0].children[0].done is True

    def test_remove_parent_cascades_to_children(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "child", "--under", "1"])
        capsys.readouterr()

        exit_code = main(["work", "-rm", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "removed #1 from 'work'" in captured.out
        assert load_list(taskli_env, "work").items == []

    @pytest.mark.parametrize(
        "argv",
        [
            ["work", "-d", "1", "--under", "1"],
            ["work", "--under", "1"],
            ["work", "--config", "--under", "1"],
        ],
        ids=["done", "view", "config"],
    )
    def test_under_rejected_outside_add_and_edit(
        self, taskli_env, capsys, argv
    ):
        exit_code = main(argv)

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "error:" in captured.err

    def test_edit_under_renests_existing_item(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "orphan"])
        capsys.readouterr()

        exit_code = main(["work", "-e", "2", "--under", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "updated #1.1 in 'work'" in captured.out
        child = load_list(taskli_env, "work").items[0].children[0]
        assert child.text == "orphan"
        assert child.id == "1.1"

    def test_edit_under_empty_unnests_to_top_level(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "child", "--under", "1"])
        capsys.readouterr()

        exit_code = main(["work", "-e", "1.1", "--under", ""])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "updated #2 in 'work'" in captured.out
        items = load_list(taskli_env, "work").items
        assert len(items) == 2
        assert items[0].children == []

    def test_edit_under_preserves_done_state(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "task"])
        main(["work", "-d", "2"])
        capsys.readouterr()

        exit_code = main(["work", "-e", "2", "--under", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "updated #1.1 in 'work'" in captured.out
        assert load_list(taskli_env, "work").items[0].children[0].done is True

    def test_edit_under_self_is_rejected(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-e", "1", "--under", "1"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "error:" in captured.err

    def test_edit_under_missing_parent_is_rejected(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-e", "1", "--under", "9"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "error:" in captured.err

    def test_edit_under_applies_modifiers_in_same_call(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "parent"])
        main(["work", "-a", "mover"])
        before = load_list(taskli_env, "work").items[1].modified_at
        capsys.readouterr()

        exit_code = main(["work", "-e", "2", "-p", "high", "--under", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "updated #1.1 in 'work'" in captured.out
        child = load_list(taskli_env, "work").items[0].children[0]
        assert child.text == "mover"
        assert child.priority is Priority.HIGH
        assert child.modified_at != before

    def test_edit_under_orders_new_sibling_by_default_sort(
        self, taskli_env, capsys
    ):
        main(["work", "--config", "default_sort", "priority"])
        main(["work", "-a", "parent", "-p", "high"])
        main(["work", "-a", "low child", "-p", "low", "--under", "1"])
        main(["work", "-a", "mover", "-p", "medium"])
        capsys.readouterr()

        exit_code = main(["work", "-e", "2", "--under", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "updated #1.1 in 'work'" in captured.out
        children = load_list(taskli_env, "work").items[0].children
        assert [c.text for c in children] == ["mover", "low child"]


class TestView:
    def test_shows_added_items(self, taskli_env, capsys):
        main(["work", "-a", "task", "--tag", "urgent"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_filters_by_tag(self, taskli_env, capsys):
        main(["work", "-a", "a", "--tag", "urgent"])
        main(["work", "-a", "b", "--tag", "later"])
        capsys.readouterr()

        main(["work", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" not in captured.out

    def test_filters_by_priority(self, taskli_env, capsys):
        main(["work", "-a", "a", "-p", "high"])
        main(["work", "-a", "b", "-p", "low"])
        capsys.readouterr()

        main(["work", "-p", "high"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" not in captured.out

    def test_filters_by_tag_and_priority(self, taskli_env, capsys):
        main(["work", "-a", "both", "--tag", "urgent", "-p", "high"])
        main(["work", "-a", "tag only", "--tag", "urgent", "-p", "low"])
        main(["work", "-a", "prio only", "--tag", "later", "-p", "high"])
        capsys.readouterr()

        main(["work", "--tag", "urgent", "-p", "high"])

        captured = capsys.readouterr()
        assert "both" in captured.out
        assert "tag only" not in captured.out
        assert "prio only" not in captured.out

    def test_sorts_by_configured_default_sort(self, taskli_env, capsys):
        main(["-a", "z-task", "-p", "high"])
        main(["-a", "a-task", "-p", "low"])
        capsys.readouterr()

        main(["--config", "default_sort", "priority"])
        capsys.readouterr()

        main([])

        captured = capsys.readouterr()
        assert captured.out.index("a-task") > captured.out.index("z-task")

    def test_default_view_does_not_resort(self, taskli_env, capsys):
        main(["--config", "default_sort", "priority"])
        main(["work", "--new"])
        main(["work", "-a", "first", "-p", "high"])
        main(["work", "-a", "second", "-p", "low"])
        # swap priorities so stored order and sort order now disagree.
        main(["work", "-e", "1", "-p", "low"])
        main(["work", "-e", "2", "-p", "high"])
        capsys.readouterr()

        main(["work"])
        captured = capsys.readouterr()
        assert captured.out.index("first") < captured.out.index("second")

    def test_auto_prunes_done_items_on_view(self, taskli_env, capsys):
        main(["-a", "task"])
        main(["-d", "1"])
        capsys.readouterr()

        main(["--config", "auto_prune", "true"])
        capsys.readouterr()

        main([])
        capsys.readouterr()

        task_list = load_list(taskli_env, "inbox")
        assert task_list.items == []

    def test_missing_list_raises(self, taskli_env, capsys):
        exit_code = main(["ghost"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err


class TestDoneUndoneRemove:
    def test_marks_done_and_undone(self, taskli_env, capsys):
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

    def test_marks_multiple_ids_in_one_call(self, taskli_env, capsys):
        main(["work", "-a", "a"])
        main(["work", "-a", "b"])
        capsys.readouterr()

        exit_code = main(["work", "-d", "1", "2"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "marked #1 done" in captured.out
        assert "marked #2 done" in captured.out

    def test_bad_id_warns_and_continues(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-d", "1", "99"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "marked #1 done" in captured.out
        assert "warning:" in captured.out
        assert "no item with id 99" in captured.out

    def test_marks_in_progress(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-i", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "marked #1 in progress" in captured.out

    def test_marks_multiple_ids_in_progress_in_one_call(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "a"])
        main(["work", "-a", "b"])
        capsys.readouterr()

        exit_code = main(["work", "-i", "1", "2"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "marked #1 in progress" in captured.out
        assert "marked #2 in progress" in captured.out

    def test_in_progress_bad_id_warns_and_continues(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-i", "1", "99"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "marked #1 in progress" in captured.out
        assert "warning:" in captured.out
        assert "no item with id 99" in captured.out

    def test_undone_resets_in_progress_item(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["work", "-i", "1"])
        capsys.readouterr()

        exit_code = main(["work", "-u", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "marked #1 not done" in captured.out

    def test_rm_removes_item(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        rm_exit_code = main(["work", "-rm", "1"])
        capsys.readouterr()

        main(["work"])
        list_captured = capsys.readouterr()

        assert rm_exit_code == 0
        assert "task" not in list_captured.out

    def test_rm_multiple_ids_removes_correct_items(self, taskli_env, capsys):
        main(["work", "-a", "a"])
        main(["work", "-a", "b"])
        main(["work", "-a", "c"])
        capsys.readouterr()

        exit_code = main(["work", "-rm", "1", "2"])

        capsys.readouterr()
        assert exit_code == 0
        task_list = load_list(taskli_env, "work")
        assert [item.text for item in task_list.items] == ["c"]

    def test_rm_mixed_good_bad_id(self, taskli_env, capsys):
        main(["work", "-a", "a"])
        main(["work", "-a", "b"])
        main(["work", "-a", "c"])
        capsys.readouterr()

        exit_code = main(["work", "-rm", "2", "99"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "warning:" in captured.out
        assert "no item with id 99" in captured.out
        task_list = load_list(taskli_env, "work")
        assert [item.text for item in task_list.items] == ["a", "c"]

    def test_rm_duplicate_id_deduped(self, taskli_env, capsys):
        main(["work", "-a", "a"])
        main(["work", "-a", "b"])
        main(["work", "-a", "c"])
        capsys.readouterr()

        exit_code = main(["work", "-rm", "1", "1"])

        capsys.readouterr()
        assert exit_code == 0
        task_list = load_list(taskli_env, "work")
        assert [item.text for item in task_list.items] == ["b", "c"]

    def test_rm_non_adjacent_ids(self, taskli_env, capsys):
        main(["work", "-a", "a"])
        main(["work", "-a", "b"])
        main(["work", "-a", "c"])
        main(["work", "-a", "d"])
        capsys.readouterr()

        exit_code = main(["work", "-rm", "1", "3"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.index("removed #1") < captured.out.index(
            "removed #3"
        )
        task_list = load_list(taskli_env, "work")
        assert [item.text for item in task_list.items] == ["b", "d"]


class TestCombinedActions:
    def test_all_four_flags_in_one_call(self, taskli_env, capsys):
        for text in ("a", "b", "c", "d", "e"):
            main(["work", "-a", text])
        capsys.readouterr()

        exit_code = main(
            ["work", "-d", "1", "4", "-i", "2", "-u", "3", "-rm", "5"]
        )

        captured = capsys.readouterr()
        assert exit_code == 0
        for fragment in (
            "marked #1 done",
            "marked #4 done",
            "marked #2 in progress",
            "marked #3 not done",
            "removed #5",
        ):
            assert fragment in captured.out
        task_list = load_list(taskli_env, "work")
        statuses = [item.status for item in task_list.items]
        assert statuses == [
            Status.DONE,
            Status.IN_PROGRESS,
            Status.TODO,
            Status.DONE,
        ]

    def test_mark_then_remove_same_call(self, taskli_env, capsys):
        for text in ("a", "b", "c"):
            main(["work", "-a", text])
        capsys.readouterr()

        exit_code = main(["work", "-d", "1", "-rm", "3"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "marked #1 done" in captured.out
        assert "removed #3" in captured.out

    def test_cross_flag_duplicate_id_errors(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-d", "2", "-i", "2"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "id 2 given to more than one action flag." in captured.err

    def test_cross_flag_duplicate_id_errors_reversed(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-rm", "2", "-d", "2"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "id 2 given to more than one action flag." in captured.err

    def test_within_flag_duplicate_stays_silent(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-d", "1", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.count("marked #1 done") == 1

    @pytest.mark.parametrize(
        "other",
        [
            ["-a", "x"],
            ["-e", "1"],
            ["-D", "1"],
            ["-mv", "other"],
            ["--copy", "other"],
        ],
        ids=["add", "edit", "details", "move", "copy"],
    )
    def test_conflict_with_other_item_action_errors(
        self, taskli_env, capsys, other
    ):
        exit_code = main(["work", "-d", "1", *other])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "cannot be combined with" in captured.err

    def test_modifier_rejected(self, taskli_env, capsys):
        exit_code = main(["work", "-d", "1", "-i", "2", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "no modifiers are valid" in captured.err

    def test_missing_id_across_flags_taints_exit(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-d", "1", "-i", "99"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "99" in captured.out
        task_list = load_list(taskli_env, "work")
        assert task_list.items[0].status is Status.DONE


class TestEdit:
    def test_edit_updates_text(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        edit_exit_code = main(["work", "-e", "1", "--text", "new"])
        capsys.readouterr()

        main(["work"])
        list_captured = capsys.readouterr()

        assert edit_exit_code == 0
        assert "new" in list_captured.out

    def test_tag_replaces_existing_tags(self, taskli_env, capsys):
        main(["work", "-a", "task", "--tag", "a"])
        capsys.readouterr()

        main(["work", "-e", "1", "--tag", "b"])
        capsys.readouterr()

        task_list = load_list(taskli_env, "work")
        assert task_list.items[0].tags == ["b"]

    def test_add_tag_merges_with_existing_tags(self, taskli_env, capsys):
        main(["work", "-a", "task", "--tag", "a"])
        capsys.readouterr()

        main(["work", "-e", "1", "--add-tag", "b"])
        capsys.readouterr()

        task_list = load_list(taskli_env, "work")
        assert task_list.items[0].tags == ["a", "b"]

    def test_tag_and_add_tag_together_errors(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-e", "1", "--tag", "a", "--add-tag", "b"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "error:" in captured.err


class TestDue:
    def test_add_sets_due_from_keyword(self, taskli_env, capsys):
        expected = date.today() + timedelta(days=1)

        exit_code = main(["work", "-a", "ship", "--due", "tomorrow"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'work'" in captured.out
        item = load_list(taskli_env, "work").items[0]
        assert item.due_date.date() == expected

    def test_add_sets_due_from_relative_span(self, taskli_env):
        expected = date.today() + timedelta(days=7)

        exit_code = main(["work", "-a", "ship", "--due", "next week"])

        assert exit_code == 0
        item = load_list(taskli_env, "work").items[0]
        assert item.due_date.date() == expected

    def test_add_sets_due_from_explicit_date(self, taskli_env):
        exit_code = main(["work", "-a", "taxes", "--due", "04-15-2026"])

        assert exit_code == 0
        item = load_list(taskli_env, "work").items[0]
        assert item.due_date == datetime(2026, 4, 15)

    def test_edit_sets_due(self, taskli_env, capsys):
        main(["work", "-a", "taxes"])
        capsys.readouterr()
        expected = date.today() + timedelta(days=3)

        exit_code = main(["work", "-e", "1", "--due", "3 days"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "updated #1 in 'work'" in captured.out
        item = load_list(taskli_env, "work").items[0]
        assert item.due_date.date() == expected

    def test_rejects_unparseable_value(self, taskli_env, capsys):
        exit_code = main(["work", "-a", "x", "--due", "someday"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "MM-DD-YYYY" in captured.out + captured.err

    def test_rejects_overdue_on_set_path(self, taskli_env, capsys):
        exit_code = main(["work", "-a", "x", "--due", "overdue"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "MM-DD-YYYY" in captured.out + captured.err

    def test_bad_value_does_not_create_list(self, taskli_env, capsys):
        exit_code = main(["fresh", "-a", "x", "--due", "someday"])

        capsys.readouterr()
        assert exit_code == 1
        assert not (taskli_env / "fresh.json").exists()

    def test_filter_overdue_matches_only_past_due(self, taskli_env, capsys):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        main(["work", "-a", "alpha", "--due", past])
        main(["work", "-a", "bravo", "--due", "today"])
        main(["work", "-a", "charlie"])
        capsys.readouterr()

        exit_code = main(["work", "--due", "overdue"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "alpha" in captured.out
        assert "bravo" not in captured.out
        assert "charlie" not in captured.out

    def test_filter_today_matches_only_today(self, taskli_env, capsys):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        main(["work", "-a", "alpha", "--due", past])
        main(["work", "-a", "bravo", "--due", "today"])
        main(["work", "-a", "charlie"])
        capsys.readouterr()

        exit_code = main(["work", "--due", "today"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "bravo" in captured.out
        assert "alpha" not in captured.out
        assert "charlie" not in captured.out

    def test_config_default_sort_by_due_orders_none_last(
        self, taskli_env, capsys
    ):
        later = (date.today() + timedelta(days=5)).strftime("%m-%d-%Y")
        main(["work", "-a", "whenever"])
        main(["work", "-a", "later", "--due", later])
        main(["work", "-a", "soon", "--due", "tomorrow"])
        capsys.readouterr()

        exit_code = main(["--config", "default_sort", "due_date"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "set 'default_sort' to 'due_date'" in captured.out
        texts = [item.text for item in load_list(taskli_env, "work").items]
        assert texts == ["soon", "later", "whenever"]


class TestReminders:
    def test_banner_on_view_with_overdue_item(self, taskli_env, capsys):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        main(["work", "-a", "alpha", "--due", past])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "1 overdue" in captured.err

    def test_no_banner_when_disabled(self, taskli_env, capsys):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        main(["work", "-a", "alpha", "--due", past])
        main(["--config", "show_reminders", "false"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.err == ""

    def test_banner_counts_nested_subtask(self, taskli_env, capsys):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        main(["work", "-a", "parent"])
        main(["work", "-a", "child", "--under", "1", "--due", past])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "1 overdue" in captured.err


class TestAgenda:
    def test_default_window_uses_configured_default(self, taskli_env, capsys):
        soon = (date.today() + timedelta(days=3)).strftime("%m-%d-%Y")
        far = (date.today() + timedelta(days=10)).strftime("%m-%d-%Y")
        main(["work", "-a", "soon", "--due", soon])
        main(["work", "-a", "far", "--due", far])
        capsys.readouterr()

        exit_code = main(["--agenda"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "soon" in captured.out
        assert "far" not in captured.out

    def test_window_today(self, taskli_env, capsys):
        main(["work", "-a", "alpha", "--due", "today"])
        main(["work", "-a", "bravo", "--due", "tomorrow"])
        capsys.readouterr()

        exit_code = main(["--agenda", "today"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "alpha" in captured.out
        assert "bravo" not in captured.out

    def test_window_week(self, taskli_env, capsys):
        main(["work", "-a", "alpha", "--due", "tomorrow"])
        far = (date.today() + timedelta(days=10)).strftime("%m-%d-%Y")
        main(["work", "-a", "bravo", "--due", far])
        capsys.readouterr()

        exit_code = main(["--agenda", "week"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "alpha" in captured.out
        assert "bravo" not in captured.out

    def test_window_overdue(self, taskli_env, capsys):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        main(["work", "-a", "alpha", "--due", past])
        main(["work", "-a", "bravo", "--due", "today"])
        capsys.readouterr()

        exit_code = main(["--agenda", "overdue"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "alpha" in captured.out
        assert "bravo" not in captured.out

    def test_window_n_days(self, taskli_env, capsys):
        in_range = (date.today() + timedelta(days=3)).strftime("%m-%d-%Y")
        out_of_range = (date.today() + timedelta(days=5)).strftime("%m-%d-%Y")
        main(["work", "-a", "alpha", "--due", in_range])
        main(["work", "-a", "bravo", "--due", out_of_range])
        capsys.readouterr()

        exit_code = main(["--agenda", "3"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "alpha" in captured.out
        assert "bravo" not in captured.out

    def test_config_default_window_picked_up(self, taskli_env, capsys):
        main(["work", "-a", "alpha", "--due", "today"])
        far = (date.today() + timedelta(days=5)).strftime("%m-%d-%Y")
        main(["work", "-a", "bravo", "--due", far])
        main(["--config", "agenda_window", "today"])
        capsys.readouterr()

        exit_code = main(["--agenda"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "alpha" in captured.out
        assert "bravo" not in captured.out

    def test_bad_window_token_exits_one(self, taskli_env, capsys):
        exit_code = main(["--agenda", "someday"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "today, week, overdue" in captured.out + captured.err

    def test_rejects_modifiers(self, taskli_env, capsys):
        exit_code = main(["--agenda", "--priority", "high"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "no modifiers are valid with --agenda." in captured.err

    def test_conflicts_with_sibling_list_flag(self, taskli_env, capsys):
        exit_code = main(["--agenda", "--lists"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "not allowed with" in captured.err

    def test_wins_over_item_action(self, taskli_env, capsys):
        exit_code = main(["--agenda", "-a", "x"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "warning:" in captured.out
        assert "multiple option groups" in captured.out

    def test_items_across_lists_sorted_chronologically(
        self, taskli_env, capsys
    ):
        later = (date.today() + timedelta(days=2)).strftime("%m-%d-%Y")
        sooner = (date.today() + timedelta(days=1)).strftime("%m-%d-%Y")
        main(["work", "-a", "later-task", "--due", later])
        main(["groceries", "-a", "sooner-task", "--due", sooner])
        capsys.readouterr()

        exit_code = main(["--agenda", "week"])

        captured = capsys.readouterr()
        assert exit_code == 0
        sooner_pos = captured.out.index("sooner-task")
        later_pos = captured.out.index("later-task")
        assert sooner_pos < later_pos

    def test_subtask_with_due_date_shows_up(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        soon = (date.today() + timedelta(days=1)).strftime("%m-%d-%Y")
        main(["work", "-a", "child", "--under", "1", "--due", soon])
        capsys.readouterr()

        exit_code = main(["--agenda", "week"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "child" in captured.out


class TestDesc:
    def test_add_sets_description(self, taskli_env, capsys):
        exit_code = main(
            ["work", "-a", "migrate", "--desc", "blue/green first"]
        )

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'work'" in captured.out
        item = load_list(taskli_env, "work").items[0]
        assert item.description == "blue/green first"

    def test_edit_replaces_description(self, taskli_env, capsys):
        main(["work", "-a", "migrate", "--desc", "old note"])
        capsys.readouterr()

        exit_code = main(["work", "-e", "1", "--desc", "updated note"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "updated #1 in 'work'" in captured.out
        item = load_list(taskli_env, "work").items[0]
        assert item.description == "updated note"

    def test_edit_empty_string_clears_description(self, taskli_env):
        main(["work", "-a", "migrate", "--desc", "old note"])

        exit_code = main(["work", "-e", "1", "--desc", ""])

        assert exit_code == 0
        item = load_list(taskli_env, "work").items[0]
        assert item.description is None


class TestDetails:
    def test_shows_task_detail(self, taskli_env, capsys):
        main(["work", "-a", "ship it"])
        capsys.readouterr()

        exit_code = main(["work", "-D", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "ship it" in captured.out
        assert "work / 1" in captured.out

    def test_alias(self, taskli_env, capsys):
        main(["work", "-a", "ship it"])
        capsys.readouterr()

        exit_code = main(["work", "--details", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "ship it" in captured.out

    def test_subtask_target(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "child", "--under", "1"])
        capsys.readouterr()

        exit_code = main(["work", "-D", "1.1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "child" in captured.out

    def test_unknown_id_exits_1(self, taskli_env, capsys):
        main(["work", "-a", "ship it"])
        capsys.readouterr()

        exit_code = main(["work", "-D", "9"])

        assert exit_code == 1

    def test_rejects_modifier(self, taskli_env):
        exit_code = main(["work", "-D", "1", "-p", "high"])

        assert exit_code == 2


class TestMoveCopy:
    def test_move_and_copy_are_mutually_exclusive_with_add(
        self, taskli_env, capsys
    ):
        exit_code = main(["work", "-a", "task", "-mv", "groceries"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "not allowed with argument" in captured.err

    def test_move_rejects_malformed_id(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-mv", "groceries", "1.x"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "item path" in captured.err

    def test_copy_rejects_malformed_id(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "--copy", "groceries", "1.x"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "item path" in captured.err

    def test_move_accepts_dotted_id(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "child", "--under", "1"])
        capsys.readouterr()

        exit_code = main(["work", "-mv", "groceries", "1.1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "moved #1.1 from 'work' to 'groceries'" in captured.out
        assert load_list(taskli_env, "work").items[0].children == []
        assert [i.text for i in load_list(taskli_env, "groceries").items] == [
            "child"
        ]

    def test_copy_accepts_dotted_id(self, taskli_env, capsys):
        main(["work", "-a", "parent"])
        main(["work", "-a", "child", "--under", "1"])
        capsys.readouterr()

        exit_code = main(["work", "--copy", "groceries", "1.1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "copied #1.1 from 'work' to 'groceries'" in captured.out
        assert [i.text for i in load_list(taskli_env, "groceries").items] == [
            "child"
        ]

    @pytest.mark.parametrize(
        "argv",
        [
            ["work", "-mv", "groceries", "1", "--tag", "urgent"],
            ["work", "-mv", "groceries", "1", "-p", "high"],
            ["work", "-mv", "groceries", "1", "--all"],
            ["work", "--copy", "groceries", "1", "--text", "new"],
            ["work", "--copy", "groceries", "1", "--add-tag", "urgent"],
        ],
        ids=[
            "move-tag",
            "move-priority",
            "move-all",
            "copy-text",
            "copy-add-tag",
        ],
    )
    def test_modifier_rejected_for_move_or_copy(
        self, taskli_env, capsys, argv
    ):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(argv)

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "error:" in captured.err

    def test_move_creates_target_list_if_missing(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-mv", "groceries", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "moved #1 from 'work' to 'groceries'" in captured.out
        assert load_list(taskli_env, "work").items == []
        assert [i.text for i in load_list(taskli_env, "groceries").items] == [
            "task"
        ]

    def test_move_resets_done_state_in_target(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["work", "-d", "1"])
        capsys.readouterr()

        main(["work", "-mv", "groceries", "1"])
        capsys.readouterr()

        moved = load_list(taskli_env, "groceries").items[0]
        assert moved.done is False
        assert moved.completed_at is None

    def test_move_no_ids_moves_every_item(self, taskli_env, capsys):
        main(["work", "-a", "a"])
        main(["work", "-a", "b"])
        capsys.readouterr()

        exit_code = main(["work", "-mv", "groceries"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "moved #1" in captured.out
        assert "moved #2" in captured.out
        assert load_list(taskli_env, "work").items == []
        assert len(load_list(taskli_env, "groceries").items) == 2

    def test_move_bad_id_warns_and_continues(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "-mv", "groceries", "1", "99"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "moved #1" in captured.out
        assert "warning:" in captured.out
        assert "no item with id 99" in captured.out
        assert load_list(taskli_env, "work").items == []

    def test_move_resorts_target(self, taskli_env, capsys):
        main(["--config", "default_sort", "priority"])
        main(["groceries", "--new"])
        main(["groceries", "-a", "low task", "-p", "low"])
        main(["work", "-a", "high task", "-p", "high"])
        capsys.readouterr()

        main(["work", "-mv", "groceries", "1"])
        capsys.readouterr()

        task_list = load_list(taskli_env, "groceries")
        assert [item.text for item in task_list.items] == [
            "high task",
            "low task",
        ]

    def test_copy_leaves_source_unchanged(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "--copy", "groceries", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "copied #1 from 'work' to 'groceries'" in captured.out
        assert [i.text for i in load_list(taskli_env, "work").items] == [
            "task"
        ]
        assert [i.text for i in load_list(taskli_env, "groceries").items] == [
            "task"
        ]

    def test_copy_no_ids_copies_every_item(self, taskli_env, capsys):
        main(["work", "-a", "a"])
        main(["work", "-a", "b"])
        capsys.readouterr()

        exit_code = main(["work", "--copy", "groceries"])

        capsys.readouterr()
        assert exit_code == 0
        assert len(load_list(taskli_env, "work").items) == 2
        assert len(load_list(taskli_env, "groceries").items) == 2

    def test_copy_bad_id_warns_and_continues(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "--copy", "groceries", "1", "99"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "copied #1" in captured.out
        assert "warning:" in captured.out
        assert "no item with id 99" in captured.out

    def test_move_missing_source_list_raises(self, taskli_env, capsys):
        exit_code = main(["ghost", "-mv", "groceries", "1"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err


class TestPrune:
    def test_removes_done_items(self, taskli_env, capsys):
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

    def test_reports_count_in_message(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["work", "-d", "1"])
        capsys.readouterr()

        main(["work", "--prune"])

        captured = capsys.readouterr()
        assert "pruned 1 item" in captured.out

    def test_no_done_items(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        prune_exit_code = main(["work", "--prune"])
        prune_captured = capsys.readouterr()

        main(["work"])
        list_captured = capsys.readouterr()

        assert prune_exit_code == 0
        assert "pruned 0 item" in prune_captured.out
        assert "task" in list_captured.out

    def test_missing_list_raises(self, taskli_env, capsys):
        exit_code = main(["ghost", "--prune"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err

    def test_implicit_inbox(self, taskli_env, capsys):
        main(["-a", "task"])
        main(["-d", "1"])
        capsys.readouterr()

        main(["--prune"])
        capsys.readouterr()

        main([])
        list_captured = capsys.readouterr()

        assert "task" not in list_captured.out

    def test_all_prunes_every_list_without_target(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["work", "-d", "1"])
        main(["groceries", "-a", "buy milk"])
        main(["groceries", "-d", "1"])
        capsys.readouterr()

        exit_code = main(["--prune", "--all"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.count("pruned 1 item") == 2
        assert load_list(taskli_env, "work").items == []
        assert load_list(taskli_env, "groceries").items == []

    def test_all_with_target_scopes_to_its_subtree(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["work", "-d", "1"])
        main(["work.meetings", "-a", "sub-task"])
        main(["work.meetings", "-d", "1"])
        main(["groceries", "-a", "buy milk"])
        main(["groceries", "-d", "1"])
        capsys.readouterr()

        exit_code = main(["work", "--prune", "--all"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.count("pruned 1 item") == 2
        assert load_list(taskli_env, "work").items == []
        assert load_list(taskli_env, "work.meetings").items == []
        assert len(load_list(taskli_env, "groceries").items) == 1

    def test_all_with_missing_target_raises(self, taskli_env, capsys):
        exit_code = main(["ghost", "--prune", "--all"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err


class TestListsCommand:
    def test_shows_all_list_names(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["groceries", "--new"])
        capsys.readouterr()

        main(["--lists"])

        captured = capsys.readouterr()
        assert "work" in captured.out
        assert "groceries" in captured.out

    def test_shows_message_when_empty(self, taskli_env, capsys):
        main(["--lists"])

        captured = capsys.readouterr()
        assert "no lists yet" in captured.out

    def test_shows_nested_sublist(self, taskli_env, capsys):
        main(["work", "--new"])
        main(["work.meetings", "--new"])
        capsys.readouterr()

        main(["--lists"])

        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        parent_line = next(line for line in lines if line.strip() == "work")
        child_line = next(
            line
            for line in lines
            if line.strip().endswith("meetings") and line.strip() != "meetings"
        )

        assert lines.index(child_line) > lines.index(parent_line)

    def test_similarly_prefixed_sibling(self, taskli_env, capsys):
        main(["work", "--new"])
        main(["work-log", "--new"])
        main(["work.meetings", "--new"])
        capsys.readouterr()

        main(["--lists"])

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
    def test_shows_every_list_items(self, taskli_env, capsys):
        main(["work", "-a", "finish report"])
        main(["groceries", "-a", "buy milk"])
        capsys.readouterr()

        main(["--all"])

        captured = capsys.readouterr()
        assert "work" in captured.out
        assert "finish report" in captured.out
        assert "groceries" in captured.out
        assert "buy milk" in captured.out

    def test_shows_message_when_empty(self, taskli_env, capsys):
        main(["--all"])

        captured = capsys.readouterr()
        assert "no lists yet" in captured.out

    def test_shows_sublist_under_parent(self, taskli_env, capsys):
        main(["work", "-a", "finish report"])
        main(["work.meetings", "-a", "sync with design"])
        capsys.readouterr()

        main(["--all"])

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

    def test_with_target_scopes_to_its_subtree(self, taskli_env, capsys):
        main(["work", "-a", "finish report"])
        main(["work.meetings", "-a", "sync with design"])
        main(["groceries", "-a", "buy milk"])
        capsys.readouterr()

        main(["work", "--all"])

        captured = capsys.readouterr()
        assert "finish report" in captured.out
        assert "sync with design" in captured.out
        assert "groceries" not in captured.out
        assert "buy milk" not in captured.out

    def test_tag_filter_hides_lists_without_matches(self, taskli_env, capsys):
        main(["alpha", "-a", "keep me", "--tag", "urgent"])
        main(["beta", "-a", "drop me"])
        capsys.readouterr()

        main(["--all", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert "keep me" in captured.out
        assert "drop me" not in captured.out
        assert "beta" not in captured.out

    def test_priority_filter_hides_lists_without_matches(
        self, taskli_env, capsys
    ):
        main(["alpha", "-a", "keep me", "--priority", "high"])
        main(["beta", "-a", "drop me", "--priority", "medium"])
        capsys.readouterr()

        main(["--all", "--priority", "high"])

        captured = capsys.readouterr()
        assert "keep me" in captured.out
        assert "drop me" not in captured.out
        assert "beta" not in captured.out

    def test_target_all_with_tag_prunes_to_matching_subtree(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "plain top", "--tag", "later"])
        main(["work.meetings", "-a", "standup", "--tag", "urgent"])
        main(["work.other", "-a", "plain other", "--tag", "later"])
        capsys.readouterr()

        main(["work", "--all", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert "meetings" in captured.out
        assert "standup" in captured.out
        assert "work" in captured.out
        assert "plain top" not in captured.out
        assert "plain other" not in captured.out

    def test_target_all_filter_matching_nothing_reports_by_tag(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "task", "--priority", "medium"])
        capsys.readouterr()

        exit_code = main(["work", "--all", "--tag", "ghost"])

        captured = capsys.readouterr()
        assert "no items match the given filter." in captured.out
        assert exit_code == 0

    def test_target_all_filter_matching_nothing_reports_by_priority(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "task", "--priority", "medium"])
        capsys.readouterr()

        exit_code = main(["work", "--all", "--priority", "low"])

        captured = capsys.readouterr()
        assert "no items match the given filter." in captured.out
        assert exit_code == 0

    def test_all_filter_matching_nothing_reports_by_tag(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "task", "--priority", "medium"])
        main(["home", "-a", "chore", "--priority", "medium"])
        capsys.readouterr()

        exit_code = main(["--all", "--tag", "ghost"])

        captured = capsys.readouterr()
        assert "no items match the given filter." in captured.out
        assert "no lists yet" not in captured.out
        assert exit_code == 0

    def test_all_filter_matching_nothing_reports_by_priority(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "task", "--priority", "medium"])
        main(["home", "-a", "chore", "--priority", "medium"])
        capsys.readouterr()

        exit_code = main(["--all", "--priority", "low"])

        captured = capsys.readouterr()
        assert "no items match the given filter." in captured.out
        assert "no lists yet" not in captured.out
        assert exit_code == 0

    def test_all_filter_on_empty_storage_reports_no_lists(
        self, taskli_env, capsys
    ):
        exit_code = main(["--all", "--tag", "ghost"])

        captured = capsys.readouterr()
        assert "no lists yet" in captured.out
        assert "no items match" not in captured.out
        assert exit_code == 0


class TestNewList:
    def test_creates_empty_list(self, taskli_env, capsys):
        exit_code = main(["groceries", "--new"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "created list 'groceries'" in captured.out

    def test_rejects_excessive_depth(self, taskli_env, capsys):
        exit_code = main(["work.meetings.boring.extra", "--new"])

        captured = capsys.readouterr()

        assert exit_code == 1
        assert "nested too deep" in captured.err

    def test_new_list_creates_with_color(self, taskli_env, capsys):
        exit_code = main(["groceries", "--new", "--color", "coral"])

        assert exit_code == 0
        assert load_list(taskli_env, "groceries").color is Color.CORAL

    def test_uses_configured_default_color(self, taskli_env, capsys):
        main(["--config", "default_color", "teal"])
        capsys.readouterr()

        main(["groceries", "--new"])
        capsys.readouterr()

        task_list = load_list(taskli_env, "groceries")
        assert task_list.color == Color.TEAL

    def test_new_list_rejects_invalid_color(self, taskli_env, capsys):
        exit_code = main(["groceries", "--new", "--color", "notacolor"])

        captured = capsys.readouterr()

        assert exit_code == 2
        assert "invalid choice" in captured.err

    def test_sublist_inherits_parent_color(self, taskli_env, capsys):
        main(["work", "--new", "--color", "blue"])
        capsys.readouterr()

        main(["work.meetings", "--new"])
        capsys.readouterr()

        assert load_list(taskli_env, "work.meetings").color is Color.BLUE

    def test_explicit_color_overrides_inheritance(self, taskli_env, capsys):
        main(["work", "--new", "--color", "blue"])
        capsys.readouterr()

        main(["work.other", "--new", "--color", "red"])
        capsys.readouterr()

        assert load_list(taskli_env, "work.other").color is Color.RED

    def test_inheritance_disabled_falls_back_to_default(
        self, taskli_env, capsys
    ):
        main(["--config", "inherit_sublist_color", "false"])
        main(["work", "--new", "--color", "blue"])
        capsys.readouterr()

        main(["work.notes", "--new"])
        capsys.readouterr()

        assert load_list(taskli_env, "work.notes").color is Color.WHITE

    def test_new_sublist_creates_missing_parent(self, taskli_env, capsys):
        exit_code = main(["work.meetings", "--new"])
        capsys.readouterr()

        main(["--lists"])
        lists_captured = capsys.readouterr()

        assert exit_code == 0
        assert "work" in lists_captured.out
        assert "meetings" in lists_captured.out


class TestDeleteList:
    def test_deletes_with_confirmation(self, taskli_env, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        main(["groceries", "--new"])
        capsys.readouterr()

        rm_exit_code = main(["groceries", "--delete"])
        capsys.readouterr()

        main(["--lists"])
        lists_captured = capsys.readouterr()

        assert rm_exit_code == 0
        assert "groceries" not in lists_captured.out

    def test_cascades_to_children(self, taskli_env, monkeypatch, capsys):
        prompts = []
        monkeypatch.setattr(
            "builtins.input", lambda p: prompts.append(p) or "y"
        )
        main(["work", "-a", "task"])
        main(["work.meetings", "-a", "sub-task"])
        capsys.readouterr()

        main(["work", "--delete"])
        capsys.readouterr()

        main(["--lists"])
        lists_captured = capsys.readouterr()

        assert "work" not in lists_captured.out
        assert "meetings" not in lists_captured.out
        assert "work.meetings" in prompts[0]

    def test_missing_list_errors(self, taskli_env, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "y")

        exit_code = main(["ghost", "--delete"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err


class TestRenameList:
    def test_renames_list(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "--rename", "job"])

        captured = capsys.readouterr()
        main(["--lists"])
        lists_captured = capsys.readouterr()

        assert exit_code == 0
        assert "renamed 'work' to 'job'" in captured.out
        assert "job" in lists_captured.out
        assert "work" not in lists_captured.out
        assert load_list(taskli_env, "job").items[0].text == "task"

    def test_cascades_to_children(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["work.meetings", "-a", "sub-task"])
        capsys.readouterr()

        exit_code = main(["work", "--rename", "job"])

        captured = capsys.readouterr()
        main(["--lists"])
        lists_captured = capsys.readouterr()

        assert exit_code == 0
        assert "renamed 'work' to 'job' and 1 sublist(s)" in captured.out
        assert "job" in lists_captured.out
        assert "meetings" in lists_captured.out
        assert "work" not in lists_captured.out
        assert load_list(taskli_env, "job.meetings").items[0].text == (
            "sub-task"
        )

    def test_missing_list_errors(self, taskli_env, capsys):
        exit_code = main(["ghost", "--rename", "job"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "does not exist" in captured.err

    def test_existing_target_errors(self, taskli_env, capsys):
        main(["work", "--new"])
        main(["job", "--new"])
        capsys.readouterr()

        exit_code = main(["work", "--rename", "job"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "already exists" in captured.err

    def test_self_rename_is_noop(self, taskli_env, capsys):
        main(["work", "--new"])
        capsys.readouterr()

        exit_code = main(["work", "--rename", "work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "already named 'work'" in captured.out

    def test_default_list_follows_rename(self, taskli_env, capsys):
        main(["work", "--new"])
        main(["--config", "default_list", "work"])
        capsys.readouterr()

        main(["work", "--rename", "job"])
        capsys.readouterr()

        exit_code = main(["-a", "task"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'job'" in captured.out

    def test_rejects_modifiers(self, taskli_env, capsys):
        exit_code = main(["work", "--rename", "job", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "no modifiers are valid" in captured.err


class TestColorCommand:
    def test_changes_color(self, taskli_env, capsys):
        main(["work", "--new"])
        capsys.readouterr()

        exit_code = main(["work", "--color", "teal"])

        capsys.readouterr()

        assert exit_code == 0
        assert load_list(taskli_env, "work").color is Color.TEAL

    def test_missing_list_errors(self, taskli_env, capsys):
        exit_code = main(["ghost", "--color", "teal"])

        captured = capsys.readouterr()

        assert exit_code == 1
        assert "does not exist" in captured.err

    def test_rejects_invalid_color(self, taskli_env, capsys):
        main(["work", "--new"])
        capsys.readouterr()

        exit_code = main(["work", "--color", "notacolor"])

        captured = capsys.readouterr()

        assert exit_code == 2
        assert "invalid choice" in captured.err


class TestConfigCommand:
    def test_no_args_lists_all_keys(self, taskli_env, capsys):
        exit_code = main(["--config"])

        captured = capsys.readouterr()

        assert exit_code == 0
        assert "auto_prune" in captured.out
        assert "default_color" in captured.out

    def test_key_only_prints_current_value(self, taskli_env, capsys):
        exit_code = main(["--config", "default_list"])

        captured = capsys.readouterr()

        assert exit_code == 0
        assert captured.out.strip() == "inbox"

    def test_key_and_value_sets_and_persists(self, taskli_env, capsys):
        exit_code = main(["--config", "auto_prune", "true"])

        captured = capsys.readouterr()

        assert exit_code == 0
        assert "set 'auto_prune' to 'true'" in captured.out
        assert load_config(taskli_env).auto_prune is True

    def test_sets_default_color(self, taskli_env, capsys):
        exit_code = main(["--config", "default_color", "teal"])

        capsys.readouterr()

        assert exit_code == 0
        assert load_config(taskli_env).default_color == Color.TEAL

    def test_unknown_key_errors(self, taskli_env, capsys):
        exit_code = main(["--config", "nope", "x"])

        captured = capsys.readouterr()

        assert exit_code == 1
        assert "not a config key" in captured.err

    def test_invalid_value_errors(self, taskli_env, capsys):
        exit_code = main(["--config", "auto_prune", "sortof"])

        captured = capsys.readouterr()

        assert exit_code == 1
        assert "not a valid value for 'auto_prune'" in captured.err

    def test_default_sort_change_resorts_all_lists(self, taskli_env, capsys):
        main(["work", "--new"])
        main(["work", "-a", "low task", "-p", "low"])
        main(["work", "-a", "high task", "-p", "high"])
        capsys.readouterr()

        exit_code = main(["--config", "default_sort", "priority"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "set 'default_sort' to 'priority'" in captured.out

        task_list = load_list(taskli_env, "work")
        assert [item.text for item in task_list.items] == [
            "high task",
            "low task",
        ]
        assert [item.id for item in task_list.items] == ["1", "2"]


class TestDefaultListAction:
    def test_bare_invocation_shows_inbox(self, taskli_env, capsys):
        exit_code = main([])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "inbox" in captured.out

    def test_bare_invocation_uses_configured_default_list(
        self, taskli_env, capsys
    ):
        main(["--config", "default_list", "work"])
        capsys.readouterr()

        exit_code = main(["-a", "task"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "added #1 to 'work'" in captured.out

    def test_bare_invocation_excludes_descendants(self, taskli_env, capsys):
        main(["-a", "task"])
        main(["inbox.notes", "-a", "sub-task"])
        capsys.readouterr()

        exit_code = main([])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out
        assert "sub-task" not in captured.out
        assert "notes" not in captured.out

    def test_list_name_shows_items(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_list_name_with_tag_filter(self, taskli_env, capsys):
        main(["work", "-a", "a", "--tag", "urgent"])
        main(["work", "-a", "b", "--tag", "later"])
        capsys.readouterr()

        main(["work", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" not in captured.out


class TestSublistDelimiter:
    def test_accepts_configured_delimiter_for_nested_name(
        self, taskli_env, capsys
    ):
        main(["--config", "sublist_delimiter", "/"])
        capsys.readouterr()

        exit_code = main(["work/meetings", "--new"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "created list 'work/meetings'" in captured.out
        assert load_list(taskli_env, "work.meetings").name == "work.meetings"

    def test_lists_shows_tree_structure_regardless_of_delimiter(
        self, taskli_env, capsys
    ):
        main(["--config", "sublist_delimiter", "/"])
        main(["work/meetings", "--new"])
        capsys.readouterr()

        exit_code = main(["--lists"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "work" in captured.out
        assert "meetings" in captured.out
        assert "work/meetings" not in captured.out

    def test_renders_nested_list_view_title_with_configured_delimiter(
        self, taskli_env, capsys
    ):
        main(["--config", "sublist_delimiter", "/"])
        main(["work/meetings", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work/meetings"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "work/meetings" in captured.out
        assert "work.meetings" not in captured.out

    def test_shows_child_section(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["work.meetings", "-a", "sub-task"])
        capsys.readouterr()

        exit_code = main(["work", "--all"])

        captured = capsys.readouterr()

        assert exit_code == 0
        assert "task" in captured.out
        assert "sub-task" in captured.out
        assert "meetings" in captured.out

    def test_grandchild_shown_under_parent(self, taskli_env, capsys):
        main(["work.meetings.notes", "-a", "deep-task"])
        capsys.readouterr()

        main(["work", "--all"])
        top_captured = capsys.readouterr()

        main(["work.meetings", "--all"])
        mid_captured = capsys.readouterr()

        assert "deep-task" in top_captured.out
        assert "meetings" in top_captured.out
        assert "notes" in top_captured.out
        assert "deep-task" in mid_captured.out

    def test_tag_filter_applies_to_sublists(self, taskli_env, capsys):
        main(["work", "-a", "a", "--tag", "urgent"])
        main(["work.meetings", "-a", "b", "--tag", "urgent"])
        main(["work.meetings", "-a", "c", "--tag", "later"])
        capsys.readouterr()

        main(["work", "--all", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" in captured.out
        assert "c" not in captured.out

    def test_tag_filter_ignores_descendants_without_all(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "a", "--tag", "urgent"])
        main(["work.meetings", "-a", "b", "--tag", "urgent"])
        capsys.readouterr()

        main(["work", "--tag", "urgent"])

        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" not in captured.out

    def test_empty_child_section_shown_without_filter(
        self, taskli_env, capsys
    ):
        main(["work.meetings", "--new"])
        capsys.readouterr()

        main(["work", "--all"])

        captured = capsys.readouterr()
        assert "meetings" in captured.out

    def test_default_view_excludes_descendants(self, taskli_env, capsys):
        main(["work", "-a", "task"])
        main(["work.meetings", "-a", "sub-task"])
        capsys.readouterr()

        main(["work"])

        captured = capsys.readouterr()
        assert "task" in captured.out
        assert "sub-task" not in captured.out
        assert "meetings" not in captured.out


class TestOptionGroupPriority:
    def test_list_mgmt_wins_over_item_action(self, taskli_env, capsys):
        exit_code = main(["groceries", "--new", "-a", "buy milk"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "warning:" in captured.out
        assert "multiple option groups" in captured.out
        assert "created list 'groceries'" in captured.out
        assert "added" not in captured.out

    def test_list_mgmt_wins_over_config(self, taskli_env, capsys):
        exit_code = main(["--lists", "--config"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "warning:" in captured.out
        assert "no lists yet" in captured.out
        assert "auto_prune" not in captured.out

    def test_item_action_wins_over_config(self, taskli_env, capsys):
        exit_code = main(["--config", "-a", "x"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "warning:" in captured.out
        assert "added #1 to 'inbox'" in captured.out

    def test_delete_wins_over_done_which_never_runs(
        self, taskli_env, monkeypatch, capsys
    ):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        main(["groceries", "-a", "buy milk"])
        capsys.readouterr()

        exit_code = main(["groceries", "--delete", "-d", "1"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "deleted list 'groceries'" in captured.out
        assert "marked" not in captured.out
        assert "does not exist" not in captured.err


class TestFlagCombinations:
    @pytest.mark.parametrize(
        "argv",
        [
            ["work", "-d", "1", "--tag", "urgent"],
            ["work", "-u", "1", "-p", "high"],
            ["work", "-rm", "1", "--text", "new"],
            ["work", "--prune", "-p", "high"],
            ["work", "--new", "-p", "high"],
            ["work", "-a", "task", "--all"],
            ["work", "-e", "1", "--all"],
            ["work", "-d", "1", "--due", "today"],
            ["work", "--prune", "--due", "today"],
            ["work", "-mv", "groceries", "--due", "today"],
            ["work", "--desc", "x"],
        ],
        ids=[
            "done-tag",
            "undone-priority",
            "remove-text",
            "prune-priority",
            "new-priority",
            "add-all",
            "edit-all",
            "done-due",
            "prune-due",
            "move-due",
            "view-desc",
        ],
    )
    def test_modifier_rejected_for_op(self, taskli_env, capsys, argv):
        exit_code = main(argv)

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "error:" in captured.err

    def test_empty_desc_on_view_is_ignored_not_rejected(
        self, taskli_env, capsys
    ):
        main(["work", "-a", "task"])
        capsys.readouterr()

        exit_code = main(["work", "--desc", ""])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "task" in captured.out

    def test_config_with_three_args_errors(self, taskli_env, capsys):
        exit_code = main(["--config", "a", "b", "c"])

        assert exit_code == 2

    def test_help_exits_zero(self, taskli_env, capsys):
        exit_code = main(["--help"])

        assert exit_code == 0


class TestVersion:
    def test_prints_version(self, taskli_env, capsys):
        exit_code = main(["--version"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert __version__ in captured.out


class TestPath:
    def test_prints_storage_dir(self, taskli_env, capsys, tmp_path):
        exit_code = main(["--path"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.strip() == str(tmp_path)


class TestMigrate:
    def test_migrates_stale_files_and_reports(self, taskli_env, capsys):
        (taskli_env / "inbox.json").write_text(
            resource_text("list_v0_legacy.json")
        )
        config_file_path(taskli_env).write_text(
            resource_text("config_v0_legacy.json")
        )

        exit_code = main(["--migrate"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "migrated 'config'." in captured.out
        assert "migrated 'inbox'." in captured.out

    def test_second_run_reports_all_current(self, taskli_env, capsys):
        (taskli_env / "inbox.json").write_text(
            resource_text("list_v0_legacy.json")
        )
        config_file_path(taskli_env).write_text(
            resource_text("config_v0_legacy.json")
        )
        main(["--migrate"])
        capsys.readouterr()

        exit_code = main(["--migrate"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "'inbox' already current." in captured.out
        assert "'config' already current." in captured.out

    def test_stale_list_view_points_at_migrate(self, taskli_env, capsys):
        (taskli_env / "inbox.json").write_text(
            resource_text("list_v0_legacy.json")
        )

        exit_code = main(["inbox"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "--migrate" in captured.out + captured.err

    def test_stale_config_read_exits_one(self, taskli_env, capsys):
        config_file_path(taskli_env).write_text(
            resource_text("config_v0_legacy.json")
        )

        exit_code = main(["--config"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "--migrate" in captured.out + captured.err

    def test_rejects_modifiers(self, taskli_env, capsys):
        exit_code = main(["--migrate", "--tag", "x"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "error:" in captured.err


class TestModifierRegistryParity:
    def test_flags_are_registry_attributes(self):
        assert set(MODIFIER_FLAGS) <= set(registry.ATTRIBUTES)

    def test_every_filterable_attr_has_a_flag_dest(self):
        # _dispatch indexes MODIFIER_FLAGS[name].filter_dest for every
        # registry.filterable() name; a gap would KeyError at runtime.
        for name in registry.filterable():
            assert MODIFIER_FLAGS[name].filter_dest is not None

    def test_every_modifier_attr_has_a_flag(self):
        # _modifier_values iterates MODIFIER_FLAGS for every attribute
        # carrying modifier_ops; a gap would drop that modifier silently.
        for name, attr in registry.ATTRIBUTES.items():
            if attr.modifier_ops:
                assert name in MODIFIER_FLAGS

    def test_color_is_not_an_item_modifier(self):
        assert registry.ATTRIBUTES["color"].modifier_ops == frozenset()


class TestCompletion:
    def test_autocomplete_invoked(self, taskli_env, monkeypatch, capsys):
        calls = []
        monkeypatch.setattr(
            "taskli.cli.argcomplete.autocomplete",
            lambda parser, *a, **kw: calls.append(parser),
        )

        main(["--version"])

        capsys.readouterr()
        assert len(calls) == 1
        assert isinstance(calls[0], argparse.ArgumentParser)

    def test_complete_list_names_returns_seeded_names(self, taskli_env):
        main(["alpha", "-a", "first"])
        main(["beta", "-a", "second"])

        names = _complete_list_names("", argparse.Namespace())

        assert names == ["alpha", "beta"]
