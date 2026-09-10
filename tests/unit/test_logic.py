from datetime import date, timedelta

import pytest

from taskli.exceptions import InvalidModifierValueError, ItemNotFoundError
from taskli.logic import (
    CommandResult,
    add,
    agenda,
    all_views,
    batch_actions,
    check_reminders,
    copy,
    delete_confirmed,
    delete_prompt,
    edit,
    has_any_lists,
    item_details,
    list_entries,
    list_view,
    mark_done,
    mark_in_progress,
    mark_undone,
    migrate,
    move,
    new_list,
    prune,
    remove_items,
    rename,
    set_config,
    set_list_color,
    storage_path,
)
from taskli.models.attributes import Color, Priority, Status
from taskli.models.query import Filter
from taskli.models.tasks import TaskliItem, TaskliList
from taskli.storage import load_config, load_list
from utils import priority_criterion, resource_text, tag_criterion


@pytest.fixture
def config(taskli_env):
    return load_config(taskli_env)


class TestAdd:
    def test_creates_list_and_returns_result(self, taskli_env, config):
        result = add("work", ["task one"], {}, config)

        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.messages == ["added #1 to 'work'."]
        assert isinstance(result.item_view, TaskliList)
        assert len(result.item_view.items) == 1

    def test_one_message_per_item(self, taskli_env, config):
        result = add("work", ["a", "b"], {}, config)

        assert result.messages == [
            "added #1 to 'work'.",
            "added #2 to 'work'.",
        ]

    def test_rejects_bad_modifier_value(self, taskli_env, config):
        with pytest.raises(InvalidModifierValueError):
            add("work", ["x"], {"priority": "nonsense"}, config)

    def test_two_items_dont_share_tag_list(self, taskli_env, config):
        result = add("work", ["a", "b"], {"tags": ["t"]}, config)

        first, second = result.item_view.items
        assert first.tags is not second.tags
        assert first.tags == second.tags == ["t"]

    def test_auto_created_sublist_inherits_parent_color(
        self, taskli_env, config
    ):
        new_list("work", "blue", config)

        add("work.meetings", ["sync"], {}, config)

        assert load_list(taskli_env, "work.meetings").color is Color.BLUE

    def test_parent_path_nests_item(self, taskli_env, config):
        add("work", ["parent"], {}, config)

        result = add("work", ["child"], {}, config, parent_path="1")

        assert result.messages == ["added #1.1 to 'work'."]
        child = result.item_view.items[0].children[0]
        assert child.text == "child"
        assert child.id == "1.1"


class TestEdit:
    def test_updates_item_text(self, taskli_env, config):
        add("work", ["old"], {}, config)

        result = edit("work", "1", {"text": "new"}, config)

        assert result.messages == ["updated #1 in 'work'."]
        assert result.item_view.items[0].text == "new"

    def test_add_tag_appends_to_existing_tags(self, taskli_env, config):
        add("work", ["x"], {"tags": ["a"]}, config)

        result = edit("work", "1", {"add_tag": ["b"]}, config)

        assert result.item_view.items[0].tags == ["a", "b"]


class TestMarkDone:
    def test_marks_and_returns_view(self, taskli_env, config):
        add("work", ["task"], {}, config)

        result = mark_done("work", ["1"], config)

        assert result.exit_code == 0
        assert result.messages == ["marked #1 done in 'work'."]
        assert result.item_view.items[0].status is Status.DONE

    def test_missing_id_taints_exit_and_warns(self, taskli_env, config):
        add("work", ["task"], {}, config)

        result = mark_done("work", ["1", "99"], config)

        assert result.exit_code == 1
        assert result.messages == ["marked #1 done in 'work'."]
        assert len(result.warnings) == 1
        assert "99" in result.warnings[0]

    def test_marks_nested_path_partial_success(self, taskli_env, config):
        add("work", ["parent"], {}, config)
        add("work", ["child"], {}, config, parent_path="1")

        result = mark_done("work", ["1.1", "1.9"], config)

        assert result.exit_code == 1
        assert result.messages == ["marked #1.1 done in 'work'."]
        assert len(result.warnings) == 1
        assert result.item_view.items[0].children[0].status is Status.DONE

    def test_marks_ancestor_and_descendant_both(self, taskli_env, config):
        add("work", ["parent"], {}, config)
        add("work", ["child"], {}, config, parent_path="1")

        result = mark_done("work", ["1", "1.1"], config)

        assert result.exit_code == 0
        assert result.messages == [
            "marked #1 done in 'work'.",
            "marked #1.1 done in 'work'.",
        ]
        parent = result.item_view.items[0]
        assert parent.status is Status.DONE
        assert parent.children[0].status is Status.DONE


class TestMarkUndone:
    def test_resets_status_to_todo(self, taskli_env, config):
        add("work", ["task"], {}, config)
        mark_done("work", ["1"], config)

        result = mark_undone("work", ["1"], config)

        assert result.item_view.items[0].status is Status.TODO


class TestMarkInProgress:
    def test_sets_status(self, taskli_env, config):
        add("work", ["task"], {}, config)

        result = mark_in_progress("work", ["1"], config)

        assert result.item_view.items[0].status is Status.IN_PROGRESS


class TestRemoveItems:
    def test_removes_named_ids(self, taskli_env, config):
        add("work", ["a", "b", "c"], {}, config)

        result = remove_items("work", ["1", "2"], config)

        assert result.exit_code == 0
        assert [item.text for item in result.item_view.items] == ["c"]

    def test_missing_id_taints_exit(self, taskli_env, config):
        add("work", ["a"], {}, config)

        result = remove_items("work", ["99"], config)

        assert result.exit_code == 1
        assert len(result.warnings) == 1

    def test_removes_nested_path(self, taskli_env, config):
        add("work", ["parent"], {}, config)
        add("work", ["child"], {}, config, parent_path="1")

        result = remove_items("work", ["1.1"], config)

        assert result.exit_code == 0
        assert result.messages == ["removed #1.1 from 'work'."]
        assert result.item_view.items[0].children == []

    def test_non_adjacent_ids_keep_user_order(self, taskli_env, config):
        add("work", ["a", "b", "c", "d"], {}, config)

        result = remove_items("work", ["1", "3"], config)

        assert result.exit_code == 0
        assert [item.text for item in result.item_view.items] == ["b", "d"]
        assert result.messages == [
            "removed #1 from 'work'.",
            "removed #3 from 'work'.",
        ]

    def test_duplicate_id_acts_once(self, taskli_env, config):
        add("work", ["a", "b", "c"], {}, config)

        result = remove_items("work", ["1", "1"], config)

        assert result.exit_code == 0
        assert [item.text for item in result.item_view.items] == ["b", "c"]
        assert len(result.messages) == 1
        assert result.warnings == []

    def test_ancestor_covers_descendant(self, taskli_env, config):
        add("work", ["parent"], {}, config)
        add("work", ["child"], {}, config, parent_path="1")

        result = remove_items("work", ["1", "1.1"], config)

        assert result.exit_code == 0
        assert result.messages == ["removed #1 from 'work'."]
        assert result.item_view.items == []
        assert result.warnings == []

    def test_ancestor_covers_descendant_reverse(self, taskli_env, config):
        add("work", ["parent"], {}, config)
        add("work", ["child"], {}, config, parent_path="1")

        result = remove_items("work", ["1.1", "1"], config)

        assert result.exit_code == 0
        assert result.messages == ["removed #1 from 'work'."]
        assert result.item_view.items == []


class TestBatchActions:
    def test_marks_run_before_removals(self, taskli_env, config):
        add("work", ["a", "b", "c", "d"], {}, config)

        result = batch_actions(
            "work", config, done=["1"], in_progress=["2"], remove=["4"]
        )

        assert result.exit_code == 0
        assert result.messages == [
            "marked #1 done in 'work'.",
            "marked #2 in progress in 'work'.",
            "removed #4 from 'work'.",
        ]
        items = result.item_view.items
        assert [item.text for item in items] == ["a", "b", "c"]
        assert items[0].status is Status.DONE
        assert items[1].status is Status.IN_PROGRESS

    def test_missing_id_taints_exit_other_groups_applied(
        self, taskli_env, config
    ):
        add("work", ["a", "b"], {}, config)

        result = batch_actions("work", config, done=["1"], remove=["99"])

        assert result.exit_code == 1
        assert result.messages == ["marked #1 done in 'work'."]
        assert len(result.warnings) == 1
        assert result.item_view.items[0].status is Status.DONE

    def test_ancestor_removal_after_descendant_mark(self, taskli_env, config):
        add("work", ["parent"], {}, config)
        add("work", ["child"], {}, config, parent_path="1")

        result = batch_actions("work", config, done=["1.1"], remove=["1"])

        assert result.exit_code == 0
        assert result.messages == [
            "marked #1.1 done in 'work'.",
            "removed #1 from 'work'.",
        ]
        assert result.item_view.items == []

    def test_empty_call_is_noop(self, taskli_env, config):
        add("work", ["a"], {}, config)

        result = batch_actions("work", config)

        assert result.exit_code == 0
        assert result.messages == []
        assert [item.text for item in result.item_view.items] == ["a"]


class TestMove:
    def test_moves_and_returns_target_view(self, taskli_env, config):
        add("src", ["task"], {}, config)

        result = move("src", "dst", [], config)

        assert result.item_view.name == "dst"
        assert [i.text for i in result.item_view.items] == ["task"]
        assert load_list(taskli_env, "src").items == []

    def test_missing_id_taints_exit_and_moves_rest(self, taskli_env, config):
        add("src", ["task"], {}, config)

        result = move("src", "dst", ["1", "99"], config)

        assert result.exit_code == 1
        assert len(result.messages) == 1
        assert len(result.warnings) == 1
        assert load_list(taskli_env, "src").items == []

    def test_duplicate_id_moves_once(self, taskli_env, config):
        add("src", ["a", "b"], {}, config)

        result = move("src", "dst", ["1", "1"], config)

        assert len(result.messages) == 1
        assert len(load_list(taskli_env, "dst").items) == 1

    def test_nested_path_partial_success(self, taskli_env, config):
        add("src", ["parent"], {}, config)
        add("src", ["child"], {}, config, parent_path="1")

        result = move("src", "dst", ["1.1", "1.9"], config)

        assert result.exit_code == 1
        assert len(result.messages) == 1
        assert len(result.warnings) == 1
        assert [i.text for i in load_list(taskli_env, "dst").items] == [
            "child"
        ]
        assert load_list(taskli_env, "src").items[0].children == []

    def test_ancestor_and_child_moves_once(self, taskli_env, config):
        add("src", ["parent"], {}, config)
        add("src", ["child"], {}, config, parent_path="1")

        result = move("src", "dst", ["1", "1.1"], config)

        assert result.exit_code == 0
        assert len(result.messages) == 1
        assert load_list(taskli_env, "src").items == []

        target = load_list(taskli_env, "dst")
        assert [i.text for i in target.items] == ["parent"]
        assert [c.text for c in target.items[0].children] == ["child"]


class TestCopy:
    def test_copies_leaving_source_intact(self, taskli_env, config):
        add("src", ["task"], {}, config)

        result = copy("src", "dst", [], config)

        assert [i.text for i in result.item_view.items] == ["task"]
        assert len(load_list(taskli_env, "src").items) == 1

    def test_duplicate_id_copies_once(self, taskli_env, config):
        add("src", ["a", "b"], {}, config)

        result = copy("src", "dst", ["1", "1"], config)

        assert len(result.messages) == 1
        assert len(load_list(taskli_env, "dst").items) == 1

    def test_copies_nested_path_partial_success(self, taskli_env, config):
        add("src", ["parent"], {}, config)
        add("src", ["child"], {}, config, parent_path="1")

        result = copy("src", "dst", ["1.1", "1.9"], config)

        assert result.exit_code == 1
        assert len(result.warnings) == 1
        assert [i.text for i in result.item_view.items] == ["child"]
        assert len(load_list(taskli_env, "src").items[0].children) == 1

    def test_ancestor_and_child_copies_once(self, taskli_env, config):
        add("src", ["parent"], {}, config)
        add("src", ["child"], {}, config, parent_path="1")

        result = copy("src", "dst", ["1", "1.1"], config)

        assert result.exit_code == 0

        target = load_list(taskli_env, "dst")
        assert [i.text for i in target.items] == ["parent"]
        assert [c.text for c in target.items[0].children] == ["child"]


class TestPrune:
    def test_returns_tree_view_and_message(self, taskli_env, config):
        add("work", ["task"], {}, config)
        mark_done("work", ["1"], config)

        result = prune("work", False, True, config)

        assert result.tree_view is not None
        assert result.messages == ["pruned 1 item(s) from 'work'."]
        assert load_list(taskli_env, "work").items == []


class TestSetListColor:
    def test_recolor_returns_view(self, taskli_env, config):
        add("work", ["a"], {}, config)

        result = set_list_color("work", "teal", config)

        assert result.item_view.color == Color.TEAL
        assert load_list(taskli_env, "work").color == Color.TEAL


class TestRename:
    def test_renames_and_reports(self, taskli_env, config):
        add("work", ["a"], {}, config)

        result = rename("work", "office", config)

        assert result.messages == ["renamed 'work' to 'office'."]
        assert "office" in [name for name, _ in list_entries()]

    def test_noop_when_same_name(self, taskli_env, config):
        add("work", ["a"], {}, config)

        result = rename("work", "work", config)

        assert "already named" in result.messages[0]


class TestDeletePrompt:
    def test_names_descendants(self, taskli_env, config):
        add("work", ["a"], {}, config)
        add("work.sub", ["b"], {}, config)

        prompt = delete_prompt("work", config)

        assert "work.sub" in prompt
        assert "sublist(s)" in prompt

    def test_simple_when_no_descendants(self, taskli_env, config):
        add("work", ["a"], {}, config)

        prompt = delete_prompt("work", config)

        assert prompt == "delete list 'work' and all its items?"


class TestDeleteConfirmed:
    def test_removes_list_and_reports(self, taskli_env, config):
        add("work", ["a"], {}, config)

        result = delete_confirmed("work", config)

        assert result.messages == ["deleted list 'work'."]
        assert "work" not in [name for name, _ in list_entries()]


class TestSetConfig:
    def test_persists_value(self, taskli_env, config):
        result = set_config("auto_prune", "true")

        assert result.messages == ["set 'auto_prune' to 'true'."]
        assert load_config(taskli_env).auto_prune is True

    def test_persists_inherit_sublist_color(self, taskli_env, config):
        set_config("inherit_sublist_color", "false")

        assert load_config(taskli_env).inherit_sublist_color is False

    def test_default_sort_resorts_every_list(self, taskli_env, config):
        add("work", ["low task"], {"priority": "low"}, config)
        add("work", ["high task"], {"priority": "high"}, config)

        set_config("default_sort", "priority")

        assert [item.text for item in load_list(taskli_env, "work").items] == [
            "high task",
            "low task",
        ]


class TestListEntries:
    def test_pairs_name_with_color(self, taskli_env, config):
        add("work", ["a"], {}, config)
        set_list_color("work", "teal", config)

        entries = list_entries()

        assert entries == [("work", Color.TEAL)]


class TestHasAnyLists:
    def test_false_on_fresh_env(self, taskli_env):
        assert has_any_lists() is False

    def test_true_once_a_list_exists(self, taskli_env, config):
        add("work", ["a"], {}, config)

        assert has_any_lists() is True


class TestCheckReminders:
    def test_counts_overdue_item(self, taskli_env, config):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        add("work", ["alpha"], {"due_date": past}, config)

        assert check_reminders() == (1, 0)

    def test_counts_due_today_item(self, taskli_env, config):
        add("work", ["alpha"], {"due_date": "today"}, config)

        assert check_reminders() == (0, 1)

    def test_excludes_done_items(self, taskli_env, config):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        add("work", ["alpha"], {"due_date": past}, config)
        mark_done("work", ["1"], config)

        assert check_reminders() == (0, 0)

    def test_counts_nested_subtask(self, taskli_env, config):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        add("work", ["parent"], {}, config)
        add(
            "work",
            ["child"],
            {"due_date": past},
            config,
            parent_path="1",
        )

        assert check_reminders() == (1, 0)

    def test_skips_unloadable_list(self, taskli_env):
        (taskli_env / "broken.json").write_text("not json")

        assert check_reminders() == (0, 0)


class TestAgenda:
    def test_today_window_includes_only_today(self, taskli_env, config):
        add("work", ["due today"], {"due_date": "today"}, config)
        add("work", ["due tomorrow"], {"due_date": "tomorrow"}, config)

        rows = agenda("today", config)

        assert [item.text for _, item in rows] == ["due today"]

    def test_week_window_includes_up_to_seven_days(self, taskli_env, config):
        add("work", ["in range"], {"due_date": "7 days"}, config)
        add("work", ["out of range"], {"due_date": "8 days"}, config)

        rows = agenda("week", config)

        assert [item.text for _, item in rows] == ["in range"]

    def test_digit_window_includes_up_to_n_days(self, taskli_env, config):
        add("work", ["in range"], {"due_date": "3 days"}, config)
        add("work", ["out of range"], {"due_date": "4 days"}, config)

        rows = agenda("3", config)

        assert [item.text for _, item in rows] == ["in range"]

    def test_overdue_window_includes_only_past(self, taskli_env, config):
        past = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")
        add("work", ["late"], {"due_date": past}, config)
        add("work", ["due today"], {"due_date": "today"}, config)

        rows = agenda("overdue", config)

        assert [item.text for _, item in rows] == ["late"]

    def test_override_beats_config_default(self, taskli_env, config):
        config.agenda_window = "today"
        add("work", ["in range"], {"due_date": "3 days"}, config)

        rows = agenda("3", config)

        assert [item.text for _, item in rows] == ["in range"]

    def test_falls_back_to_config_default(self, taskli_env, config):
        config.agenda_window = "today"
        add("work", ["due today"], {"due_date": "today"}, config)
        add("work", ["due tomorrow"], {"due_date": "tomorrow"}, config)

        rows = agenda(None, config)

        assert [item.text for _, item in rows] == ["due today"]

    def test_empty_when_nothing_matches(self, taskli_env, config):
        add("work", ["far off"], {"due_date": "30 days"}, config)

        assert agenda("today", config) == []

    def test_orders_chronologically_across_lists(self, taskli_env, config):
        add("alpha", ["later"], {"due_date": "3 days"}, config)
        add("zebra", ["sooner"], {"due_date": "today"}, config)

        rows = agenda("week", config)

        assert [item.text for _, item in rows] == ["sooner", "later"]

    def test_includes_subtask(self, taskli_env, config):
        add("work", ["parent"], {}, config)
        add(
            "work",
            ["child"],
            {"due_date": "today"},
            config,
            parent_path="1",
        )

        rows = agenda("today", config)

        assert [item.text for _, item in rows] == ["child"]

    def test_skips_unloadable_list(self, taskli_env, config):
        add("work", ["due today"], {"due_date": "today"}, config)
        (taskli_env / "broken.json").write_text("not json")

        rows = agenda("today", config)

        assert [item.text for _, item in rows] == ["due today"]


class TestItemDetails:
    def test_returns_list_and_item(self, taskli_env, config):
        add("work", ["ship it"], {}, config)

        task_list, item = item_details("work", "1")

        assert isinstance(task_list, TaskliList)
        assert isinstance(item, TaskliItem)
        assert item.id == "1"
        assert item.text == "ship it"

    def test_resolves_subtask_id(self, taskli_env, config):
        add("work", ["parent"], {}, config)
        add("work", ["child"], {}, config, parent_path="1")

        _, item = item_details("work", "1.1")

        assert isinstance(item, TaskliItem)
        assert item.id == "1.1"
        assert item.text == "child"

    def test_unknown_id_raises(self, taskli_env, config):
        add("work", ["only one"], {}, config)

        with pytest.raises(ItemNotFoundError):
            item_details("work", "9")


class TestListView:
    def test_returns_single_list_without_descendants(self, taskli_env, config):
        add("work", ["a"], {}, config)
        add("work.sub", ["b"], {}, config)

        views = list_view("work", Filter(), False)

        assert [v.name for v in views] == ["work"]

    def test_includes_descendants_when_asked(self, taskli_env, config):
        add("work", ["a"], {}, config)
        add("work.sub", ["b"], {}, config)

        views = list_view("work", Filter(), True)

        assert [v.name for v in views] == ["work", "work.sub"]

    def test_filters_by_tag(self, taskli_env, config):
        add("work", ["tagged"], {"tags": ["urgent"]}, config)
        add("work", ["plain"], {}, config)

        views = list_view("work", Filter((tag_criterion("urgent"),)), False)

        assert [i.text for i in views[0].items] == ["tagged"]

    def test_descendants_filter_drops_empty_keeps_ancestors_by_tag(
        self, taskli_env, config
    ):
        add("work", ["plain"], {}, config)
        add("work.a", ["hit"], {"tags": ["urgent"]}, config)
        add("work.b", ["miss"], {}, config)

        views = list_view("work", Filter((tag_criterion("urgent"),)), True)

        assert [v.name for v in views] == ["work", "work.a"]

    def test_descendants_filter_drops_empty_keeps_ancestors_by_priority(
        self, taskli_env, config
    ):
        add("work", ["plain"], {}, config)
        add("work.a", ["hit"], {"priority": "high"}, config)
        add("work.b", ["miss"], {}, config)

        views = list_view(
            "work", Filter((priority_criterion(Priority.HIGH),)), True
        )

        assert [v.name for v in views] == ["work", "work.a"]

    def test_descendants_filter_no_matches_returns_empty_by_tag(
        self, taskli_env, config
    ):
        add("work", ["plain"], {}, config)
        add("work.sub", ["also plain"], {}, config)

        views = list_view("work", Filter((tag_criterion("ghost"),)), True)

        assert views == []

    def test_descendants_filter_no_matches_returns_empty_by_priority(
        self, taskli_env, config
    ):
        add("work", ["plain"], {}, config)
        add("work.sub", ["also plain"], {}, config)

        views = list_view(
            "work", Filter((priority_criterion(Priority.HIGH),)), True
        )

        assert views == []

    def test_without_descendants_keeps_single_list_by_tag(
        self, taskli_env, config
    ):
        add("work", ["plain"], {}, config)

        views = list_view("work", Filter((tag_criterion("ghost"),)), False)

        assert [v.name for v in views] == ["work"]

    def test_without_descendants_keeps_single_list_by_priority(
        self, taskli_env, config
    ):
        add("work", ["plain"], {}, config)

        views = list_view(
            "work", Filter((priority_criterion(Priority.HIGH),)), False
        )

        assert [v.name for v in views] == ["work"]


class TestAllViews:
    def test_one_group_per_root(self, taskli_env, config):
        add("work", ["a"], {}, config)
        add("home", ["b"], {}, config)

        groups = all_views(Filter())

        assert len(groups) == 2

    def test_empty_when_no_lists(self, taskli_env):
        assert all_views(Filter()) == []

    def test_tag_drops_root_with_no_matches(self, taskli_env, config):
        add("alpha", ["hit"], {"tags": ["urgent"]}, config)
        add("alpha.sub", ["nope"], {}, config)
        add("beta", ["miss"], {}, config)
        add("beta.sub", ["miss too"], {}, config)

        groups = all_views(Filter((tag_criterion("urgent"),)))

        names = [tl.name for group in groups for tl in group]
        assert "alpha" in names
        assert "alpha.sub" not in names
        assert "beta" not in names
        assert "beta.sub" not in names

    def test_tag_keeps_ancestor_chain_for_deep_match(self, taskli_env, config):
        add("proj", ["top plain"], {}, config)
        add("proj.mid", ["mid plain"], {}, config)
        add("proj.mid.leaf", ["deep hit"], {"tags": ["urgent"]}, config)

        groups = all_views(Filter((tag_criterion("urgent"),)))

        names = [tl.name for group in groups for tl in group]
        assert names == ["proj", "proj.mid", "proj.mid.leaf"]

    def test_priority_drops_root_with_no_matches(self, taskli_env, config):
        add("alpha", ["hit"], {"priority": "high"}, config)
        add("beta", ["miss"], {}, config)

        groups = all_views(Filter((priority_criterion(Priority.HIGH),)))

        names = [tl.name for group in groups for tl in group]
        assert names == ["alpha"]

    def test_no_filter_keeps_empty_descendant(self, taskli_env, config):
        add("work", ["a"], {}, config)
        new_list("work.sub", None, config)

        groups = all_views(Filter())

        names = [tl.name for group in groups for tl in group]
        assert "work.sub" in names


class TestMigrate:
    def test_migrates_stale_list_and_reloads(self, taskli_env):
        (taskli_env / "inbox.json").write_text(
            resource_text("list_v0_legacy.json")
        )

        result = migrate()

        assert result.exit_code == 0
        assert "migrated 'inbox'." in result.messages
        assert isinstance(load_list(taskli_env, "inbox"), TaskliList)

    def test_all_current_reports_no_change(self, taskli_env, config):
        result = migrate()

        assert result.exit_code == 0
        assert result.messages == ["'config' already current."]


class TestStoragePath:
    def test_returns_env_dir(self, taskli_env):
        assert storage_path() == taskli_env
