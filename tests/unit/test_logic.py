import pytest

from taskli.exceptions import InvalidModifierValueError
from taskli.logic import (
    CommandResult,
    add,
    all_views,
    copy,
    delete_confirmed,
    delete_prompt,
    edit,
    has_any_lists,
    list_entries,
    list_names,
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
from taskli.models import Color, Filter, Priority, Status, TaskliList
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


class TestEdit:
    def test_updates_item_text(self, taskli_env, config):
        add("work", ["old"], {}, config)

        result = edit("work", 1, {"text": "new"}, config)

        assert result.messages == ["updated #1 in 'work'."]
        assert result.item_view.items[0].text == "new"

    def test_add_tag_appends_to_existing_tags(self, taskli_env, config):
        add("work", ["x"], {"tags": ["a"]}, config)

        result = edit("work", 1, {"add_tag": ["b"]}, config)

        assert result.item_view.items[0].tags == ["a", "b"]


class TestMarkDone:
    def test_marks_and_returns_view(self, taskli_env, config):
        add("work", ["task"], {}, config)

        result = mark_done("work", [1], config)

        assert result.exit_code == 0
        assert result.messages == ["marked #1 done in 'work'."]
        assert result.item_view.items[0].status is Status.DONE

    def test_missing_id_taints_exit_and_warns(self, taskli_env, config):
        add("work", ["task"], {}, config)

        result = mark_done("work", [1, 99], config)

        assert result.exit_code == 1
        assert result.messages == ["marked #1 done in 'work'."]
        assert len(result.warnings) == 1
        assert "99" in result.warnings[0]


class TestMarkUndone:
    def test_resets_status_to_todo(self, taskli_env, config):
        add("work", ["task"], {}, config)
        mark_done("work", [1], config)

        result = mark_undone("work", [1], config)

        assert result.item_view.items[0].status is Status.TODO


class TestMarkInProgress:
    def test_sets_status(self, taskli_env, config):
        add("work", ["task"], {}, config)

        result = mark_in_progress("work", [1], config)

        assert result.item_view.items[0].status is Status.IN_PROGRESS


class TestRemoveItems:
    def test_removes_named_ids(self, taskli_env, config):
        add("work", ["a", "b", "c"], {}, config)

        result = remove_items("work", [1, 2], config)

        assert result.exit_code == 0
        assert [item.text for item in result.item_view.items] == ["c"]

    def test_missing_id_taints_exit(self, taskli_env, config):
        add("work", ["a"], {}, config)

        result = remove_items("work", [99], config)

        assert result.exit_code == 1
        assert len(result.warnings) == 1

    def test_non_adjacent_ids_keep_user_order(self, taskli_env, config):
        add("work", ["a", "b", "c", "d"], {}, config)

        result = remove_items("work", [1, 3], config)

        assert result.exit_code == 0
        assert [item.text for item in result.item_view.items] == ["b", "d"]
        assert result.messages == [
            "removed #1 from 'work'.",
            "removed #3 from 'work'.",
        ]

    def test_duplicate_id_acts_once(self, taskli_env, config):
        add("work", ["a", "b", "c"], {}, config)

        result = remove_items("work", [1, 1], config)

        assert result.exit_code == 0
        assert [item.text for item in result.item_view.items] == ["b", "c"]
        assert len(result.messages) == 1
        assert result.warnings == []


class TestMove:
    def test_moves_and_returns_target_view(self, taskli_env, config):
        add("src", ["task"], {}, config)

        result = move("src", "dst", [], config)

        assert result.item_view.name == "dst"
        assert [i.text for i in result.item_view.items] == ["task"]
        assert load_list(taskli_env, "src").items == []

    def test_missing_id_taints_exit_and_moves_rest(self, taskli_env, config):
        add("src", ["task"], {}, config)

        result = move("src", "dst", [1, 99], config)

        assert result.exit_code == 1
        assert len(result.messages) == 1
        assert len(result.warnings) == 1
        assert load_list(taskli_env, "src").items == []

    def test_duplicate_id_moves_once(self, taskli_env, config):
        add("src", ["a", "b"], {}, config)

        result = move("src", "dst", [1, 1], config)

        assert len(result.messages) == 1
        assert len(load_list(taskli_env, "dst").items) == 1


class TestCopy:
    def test_copies_leaving_source_intact(self, taskli_env, config):
        add("src", ["task"], {}, config)

        result = copy("src", "dst", [], config)

        assert [i.text for i in result.item_view.items] == ["task"]
        assert len(load_list(taskli_env, "src").items) == 1

    def test_duplicate_id_copies_once(self, taskli_env, config):
        add("src", ["a", "b"], {}, config)

        result = copy("src", "dst", [1, 1], config)

        assert len(result.messages) == 1
        assert len(load_list(taskli_env, "dst").items) == 1


class TestPrune:
    def test_returns_tree_view_and_message(self, taskli_env, config):
        add("work", ["task"], {}, config)
        mark_done("work", [1], config)

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


class TestListNames:
    def test_returns_names_sorted(self, taskli_env, config):
        add("work", ["a"], {}, config)
        add("home", ["b"], {}, config)

        names = list_names()

        assert names == ["home", "work"]

    def test_empty_when_no_lists(self, taskli_env):
        assert list_names() == []


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
