import pytest

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
    move,
    new_list,
    prune,
    remove_items,
    rename,
    set_config,
    set_list_color,
    storage_path,
)
from taskli.models import Color, Status, TaskliList
from taskli.storage import load_config, load_list


@pytest.fixture
def config(taskli_env):
    return load_config(taskli_env)


class TestAdd:
    def test_creates_list_and_returns_result(self, taskli_env, config):
        result = add("work", ["task one"], [], "medium", config)

        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.messages == ["added #1 to 'work'."]
        assert isinstance(result.item_view, TaskliList)
        assert len(result.item_view.items) == 1

    def test_one_message_per_item(self, taskli_env, config):
        result = add("work", ["a", "b"], [], "medium", config)

        assert result.messages == [
            "added #1 to 'work'.",
            "added #2 to 'work'.",
        ]


class TestEdit:
    def test_updates_item_text(self, taskli_env, config):
        add("work", ["old"], [], "medium", config)

        result = edit("work", 1, "new", None, [], [], config)

        assert result.messages == ["updated #1 in 'work'."]
        assert result.item_view.items[0].text == "new"


class TestMarkDone:
    def test_marks_and_returns_view(self, taskli_env, config):
        add("work", ["task"], [], "medium", config)

        result = mark_done("work", [1], config)

        assert result.exit_code == 0
        assert result.messages == ["marked #1 done in 'work'."]
        assert result.item_view.items[0].status is Status.DONE

    def test_missing_id_taints_exit_and_warns(self, taskli_env, config):
        add("work", ["task"], [], "medium", config)

        result = mark_done("work", [1, 99], config)

        assert result.exit_code == 1
        assert result.messages == ["marked #1 done in 'work'."]
        assert len(result.warnings) == 1
        assert "99" in result.warnings[0]


class TestMarkUndone:
    def test_resets_status_to_todo(self, taskli_env, config):
        add("work", ["task"], [], "medium", config)
        mark_done("work", [1], config)

        result = mark_undone("work", [1], config)

        assert result.item_view.items[0].status is Status.TODO


class TestMarkInProgress:
    def test_sets_status(self, taskli_env, config):
        add("work", ["task"], [], "medium", config)

        result = mark_in_progress("work", [1], config)

        assert result.item_view.items[0].status is Status.IN_PROGRESS


class TestRemoveItems:
    def test_removes_named_ids(self, taskli_env, config):
        add("work", ["a", "b", "c"], [], "medium", config)

        result = remove_items("work", [1, 2], config)

        assert result.exit_code == 0
        assert [item.text for item in result.item_view.items] == ["c"]

    def test_missing_id_taints_exit(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)

        result = remove_items("work", [99], config)

        assert result.exit_code == 1
        assert len(result.warnings) == 1


class TestMove:
    def test_moves_and_returns_target_view(self, taskli_env, config):
        add("src", ["task"], [], "medium", config)

        result = move("src", "dst", [], config)

        assert result.item_view.name == "dst"
        assert [i.text for i in result.item_view.items] == ["task"]
        assert load_list(taskli_env, "src").items == []


class TestCopy:
    def test_copies_leaving_source_intact(self, taskli_env, config):
        add("src", ["task"], [], "medium", config)

        result = copy("src", "dst", [], config)

        assert [i.text for i in result.item_view.items] == ["task"]
        assert len(load_list(taskli_env, "src").items) == 1


class TestPrune:
    def test_returns_tree_view_and_message(self, taskli_env, config):
        add("work", ["task"], [], "medium", config)
        mark_done("work", [1], config)

        result = prune("work", False, True, config)

        assert result.tree_view is not None
        assert result.messages == ["pruned 1 item(s) from 'work'."]
        assert load_list(taskli_env, "work").items == []


class TestSetListColor:
    def test_recolor_returns_view(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)

        result = set_list_color("work", "teal", config)

        assert result.item_view.color == Color.TEAL
        assert load_list(taskli_env, "work").color == Color.TEAL


class TestRename:
    def test_renames_and_reports(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)

        result = rename("work", "office", config)

        assert result.messages == ["renamed 'work' to 'office'."]
        assert "office" in [name for name, _ in list_entries()]

    def test_noop_when_same_name(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)

        result = rename("work", "work", config)

        assert "already named" in result.messages[0]


class TestDeletePrompt:
    def test_names_descendants(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)
        add("work.sub", ["b"], [], "medium", config)

        prompt = delete_prompt("work", config)

        assert "work.sub" in prompt
        assert "sublist(s)" in prompt

    def test_simple_when_no_descendants(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)

        prompt = delete_prompt("work", config)

        assert prompt == "delete list 'work' and all its items?"


class TestDeleteConfirmed:
    def test_removes_list_and_reports(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)

        result = delete_confirmed("work", config)

        assert result.messages == ["deleted list 'work'."]
        assert "work" not in [name for name, _ in list_entries()]


class TestSetConfig:
    def test_persists_value(self, taskli_env, config):
        result = set_config("auto_prune", "true")

        assert result.messages == ["set 'auto_prune' to 'true'."]
        assert load_config(taskli_env).auto_prune is True

    def test_default_sort_resorts_every_list(self, taskli_env, config):
        add("work", ["low task"], [], "low", config)
        add("work", ["high task"], [], "high", config)

        set_config("default_sort", "priority")

        assert [item.text for item in load_list(taskli_env, "work").items] == [
            "high task",
            "low task",
        ]


class TestListEntries:
    def test_pairs_name_with_color(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)
        set_list_color("work", "teal", config)

        entries = list_entries()

        assert entries == [("work", Color.TEAL)]


class TestHasAnyLists:
    def test_false_on_fresh_env(self, taskli_env):
        assert has_any_lists() is False

    def test_true_once_a_list_exists(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)

        assert has_any_lists() is True
        
        
class TestListNames:
    def test_returns_names_sorted(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)
        add("home", ["b"], [], "medium", config)

        names = list_names()

        assert names == ["home", "work"]

    def test_empty_when_no_lists(self, taskli_env):
        assert list_names() == []


class TestListView:
    def test_returns_single_list_without_descendants(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)
        add("work.sub", ["b"], [], "medium", config)

        views = list_view("work", None, None, False)

        assert [v.name for v in views] == ["work"]

    def test_includes_descendants_when_asked(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)
        add("work.sub", ["b"], [], "medium", config)

        views = list_view("work", None, None, True)

        assert [v.name for v in views] == ["work", "work.sub"]

    def test_filters_by_tag(self, taskli_env, config):
        add("work", ["tagged"], ["urgent"], "medium", config)
        add("work", ["plain"], [], "medium", config)

        views = list_view("work", "urgent", None, False)

        assert [i.text for i in views[0].items] == ["tagged"]

    def test_descendants_filter_drops_empty_keeps_ancestors_by_tag(
        self, taskli_env, config
    ):
        add("work", ["plain"], [], "medium", config)
        add("work.a", ["hit"], ["urgent"], "medium", config)
        add("work.b", ["miss"], [], "medium", config)

        views = list_view("work", "urgent", None, True)

        assert [v.name for v in views] == ["work", "work.a"]

    def test_descendants_filter_drops_empty_keeps_ancestors_by_priority(
        self, taskli_env, config
    ):
        add("work", ["plain"], [], "medium", config)
        add("work.a", ["hit"], [], "high", config)
        add("work.b", ["miss"], [], "medium", config)

        views = list_view("work", None, "high", True)

        assert [v.name for v in views] == ["work", "work.a"]

    def test_descendants_filter_no_matches_returns_empty_by_tag(
        self, taskli_env, config
    ):
        add("work", ["plain"], [], "medium", config)
        add("work.sub", ["also plain"], [], "medium", config)

        views = list_view("work", "ghost", None, True)

        assert views == []

    def test_descendants_filter_no_matches_returns_empty_by_priority(
        self, taskli_env, config
    ):
        add("work", ["plain"], [], "medium", config)
        add("work.sub", ["also plain"], [], "medium", config)

        views = list_view("work", None, "high", True)

        assert views == []

    def test_without_descendants_keeps_single_list_by_tag(
        self, taskli_env, config
    ):
        add("work", ["plain"], [], "medium", config)

        views = list_view("work", "ghost", None, False)

        assert [v.name for v in views] == ["work"]

    def test_without_descendants_keeps_single_list_by_priority(
        self, taskli_env, config
    ):
        add("work", ["plain"], [], "medium", config)

        views = list_view("work", None, "high", False)

        assert [v.name for v in views] == ["work"]


class TestAllViews:
    def test_one_group_per_root(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)
        add("home", ["b"], [], "medium", config)

        groups = all_views(None, None)

        assert len(groups) == 2

    def test_empty_when_no_lists(self, taskli_env):
        assert all_views(None, None) == []

    def test_tag_drops_root_with_no_matches(self, taskli_env, config):
        add("alpha", ["hit"], ["urgent"], "medium", config)
        add("alpha.sub", ["nope"], [], "medium", config)
        add("beta", ["miss"], [], "medium", config)
        add("beta.sub", ["miss too"], [], "medium", config)

        groups = all_views("urgent", None)

        names = [tl.name for group in groups for tl in group]
        assert "alpha" in names
        assert "alpha.sub" not in names
        assert "beta" not in names
        assert "beta.sub" not in names

    def test_tag_keeps_ancestor_chain_for_deep_match(self, taskli_env, config):
        add("proj", ["top plain"], [], "medium", config)
        add("proj.mid", ["mid plain"], [], "medium", config)
        add("proj.mid.leaf", ["deep hit"], ["urgent"], "medium", config)

        groups = all_views("urgent", None)

        names = [tl.name for group in groups for tl in group]
        assert names == ["proj", "proj.mid", "proj.mid.leaf"]

    def test_priority_drops_root_with_no_matches(self, taskli_env, config):
        add("alpha", ["hit"], [], "high", config)
        add("beta", ["miss"], [], "medium", config)

        groups = all_views(None, "high")

        names = [tl.name for group in groups for tl in group]
        assert names == ["alpha"]

    def test_no_filter_keeps_empty_descendant(self, taskli_env, config):
        add("work", ["a"], [], "medium", config)
        new_list("work.sub", None, config)

        groups = all_views(None, None)

        names = [tl.name for group in groups for tl in group]
        assert "work.sub" in names


class TestStoragePath:
    def test_returns_env_dir(self, taskli_env):
        assert storage_path() == taskli_env
