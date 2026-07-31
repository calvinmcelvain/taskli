from pathlib import Path

import pytest

from todo_cli.models import Color, TodoList
from todo_cli.storage import (
    CorruptedListFileError,
    InvalidListNameError,
    ListAlreadyExistsError,
    ListNotFoundError,
    ReservedNameError,
    TooManyAncestorListsError,
    ancestor_chain,
    child_list_names,
    create_list,
    delete_list,
    descendant_list_names,
    list_all_lists,
    list_exists,
    list_file_path,
    load_list,
    load_or_create_list,
    parent_list_name,
    resolve_storage_dir,
    save_list,
)


class TestResolveStorageDir:
    def test_uses_env_var_override(self, todos_env):
        result = resolve_storage_dir()

        assert result == todos_env

    def test_defaults_to_home_dotfolder(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TODOS_PATH", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = resolve_storage_dir()

        assert result == tmp_path / ".todos"


class TestListHierarchyHelpers:
    def test_parent_list_name_top_level(self):
        assert parent_list_name("work") is None

    def test_parent_list_name_nested(self):
        assert parent_list_name("work.meetings") == "work"

    def test_parent_list_name_deeply_nested(self):
        assert parent_list_name("work.meetings.notes") == "work.meetings"

    def test_child_list_names_excludes_grandchildren(self):
        names = [
            "work",
            "work.meetings",
            "work.meetings.notes",
            "personal",
        ]

        assert child_list_names("work", names) == ["work.meetings"]

    def test_descendant_list_names_includes_all_depths(self):
        names = [
            "work",
            "work.meetings",
            "work.meetings.notes",
            "personal",
        ]

        assert descendant_list_names("work", names) == [
            "work.meetings",
            "work.meetings.notes",
        ]

    def test_descendant_list_names_excludes_unrelated_sibling(self):
        names = ["work", "workshop"]

        assert descendant_list_names("work", names) == []

    def test_ancestor_chain_nested(self):
        assert ancestor_chain("a.b.c") == ["a", "a.b"]

    def test_ancestor_chain_top_level(self):
        assert ancestor_chain("a") == []


class TestListLifecycle:
    def test_create_list_persists_empty_list(self, tmp_path):
        todo_list = create_list(tmp_path, "work", reserved_names=frozenset())

        assert isinstance(todo_list, TodoList)
        assert list_exists(tmp_path, "work")

    def test_create_list_rejects_reserved_name(self, tmp_path):
        with pytest.raises(ReservedNameError):
            create_list(tmp_path, "add", reserved_names=frozenset({"add"}))

    def test_create_list_rejects_duplicate(self, tmp_path):
        create_list(tmp_path, "work", reserved_names=frozenset())

        with pytest.raises(ListAlreadyExistsError):
            create_list(tmp_path, "work", reserved_names=frozenset())

    def test_create_list_without_color_defaults_to_none(self, tmp_path):
        todo_list = create_list(tmp_path, "work", reserved_names=frozenset())

        assert todo_list.color is None

    def test_create_list_with_color_persists_it(self, tmp_path):
        todo_list = create_list(
            tmp_path, "work", reserved_names=frozenset(), color=Color.CORAL
        )

        assert todo_list.color is Color.CORAL
        assert load_list(tmp_path, "work").color is Color.CORAL

    def test_list_file_path_rejects_trailing_dot(self, tmp_path):
        with pytest.raises(InvalidListNameError):
            list_file_path(tmp_path, "work.")

    def test_list_file_path_rejects_leading_dot(self, tmp_path):
        with pytest.raises(InvalidListNameError):
            list_file_path(tmp_path, ".meetings")

    def test_list_file_path_rejects_consecutive_dots(self, tmp_path):
        with pytest.raises(InvalidListNameError):
            list_file_path(tmp_path, "work..meetings")

    def test_list_file_path_allows_two_ancestor_levels(self, tmp_path):
        list_file_path(tmp_path, "work.meetings.boring")

    def test_list_file_path_rejects_excessive_depth(self, tmp_path):
        with pytest.raises(TooManyAncestorListsError):
            list_file_path(tmp_path, "work.meetings.boring.extra")

    def test_create_list_auto_creates_missing_parent(self, tmp_path):
        create_list(tmp_path, "work.meetings", reserved_names=frozenset())

        assert list_exists(tmp_path, "work")
        assert list_exists(tmp_path, "work.meetings")
        assert load_list(tmp_path, "work").items == []

    def test_create_list_does_not_reset_existing_parent(self, tmp_path):
        parent = create_list(tmp_path, "work", reserved_names=frozenset())
        parent.add_item("existing task")
        save_list(tmp_path, parent)

        create_list(tmp_path, "work.meetings", reserved_names=frozenset())

        assert load_list(tmp_path, "work").items[0].text == "existing task"

    def test_create_list_rejects_reserved_ancestor(self, tmp_path):
        with pytest.raises(ReservedNameError):
            create_list(tmp_path, "add.foo", reserved_names=frozenset({"add"}))

    def test_delete_list_removes_file(self, tmp_path):
        create_list(tmp_path, "work", reserved_names=frozenset())

        delete_list(tmp_path, "work")

        assert not list_exists(tmp_path, "work")

    def test_delete_list_raises_for_missing(self, tmp_path):
        with pytest.raises(ListNotFoundError):
            delete_list(tmp_path, "ghost")

    def test_delete_list_cascades_to_descendants(self, tmp_path):
        create_list(tmp_path, "work", reserved_names=frozenset())
        create_list(tmp_path, "work.meetings", reserved_names=frozenset())
        create_list(tmp_path, "work.meetings.notes", reserved_names=frozenset())

        deleted = delete_list(tmp_path, "work")

        assert deleted == ["work.meetings", "work.meetings.notes"]
        assert not list_exists(tmp_path, "work")
        assert not list_exists(tmp_path, "work.meetings")
        assert not list_exists(tmp_path, "work.meetings.notes")

    def test_delete_list_does_not_cascade_to_sibling(self, tmp_path):
        create_list(tmp_path, "work", reserved_names=frozenset())
        create_list(tmp_path, "workshop", reserved_names=frozenset())

        delete_list(tmp_path, "work")

        assert list_exists(tmp_path, "workshop")

    def test_list_all_lists_sorted(self, tmp_path):
        create_list(tmp_path, "work", reserved_names=frozenset())
        create_list(tmp_path, "abc", reserved_names=frozenset())

        assert list_all_lists(tmp_path) == ["abc", "work"]


class TestLoadList:
    def test_auto_creates_default_list(self, tmp_path):
        todo_list = load_list(tmp_path, "inbox")

        assert todo_list.name == "inbox"
        assert list_exists(tmp_path, "inbox")

    def test_raises_for_missing_non_default_list(self, tmp_path):
        with pytest.raises(ListNotFoundError):
            load_list(tmp_path, "work")

    def test_round_trips_saved_items(self, tmp_path):
        todo_list = create_list(tmp_path, "work", reserved_names=frozenset())
        todo_list.add_item("task")
        save_list(tmp_path, todo_list)

        reloaded = load_list(tmp_path, "work")

        assert len(reloaded.items) == 1
        assert reloaded.items[0].text == "task"

    def test_raises_for_corrupted_file(self, tmp_path):
        (tmp_path / "broken.json").write_text("not valid json")

        with pytest.raises(CorruptedListFileError):
            load_list(tmp_path, "broken")


class TestLoadOrCreateList:
    def test_creates_when_missing(self, tmp_path):
        todo_list = load_or_create_list(tmp_path, "work")

        assert todo_list.name == "work"
        assert list_exists(tmp_path, "work")

    def test_loads_existing(self, tmp_path):
        created = create_list(tmp_path, "work", reserved_names=frozenset())
        created.add_item("task")
        save_list(tmp_path, created)

        loaded = load_or_create_list(tmp_path, "work")

        assert len(loaded.items) == 1

    def test_creates_missing_parent_chain(self, tmp_path):
        todo_list = load_or_create_list(tmp_path, "work.meetings")

        assert todo_list.name == "work.meetings"
        assert list_exists(tmp_path, "work")
        assert list_exists(tmp_path, "work.meetings")
