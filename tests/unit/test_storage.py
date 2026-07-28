from pathlib import Path

import pytest

from todo_cli.models import TodoList
from todo_cli.storage import (
    CorruptedListFileError,
    ListAlreadyExistsError,
    ListNotFoundError,
    ReservedNameError,
    create_list,
    delete_list,
    list_all_lists,
    list_exists,
    load_list,
    load_or_create_list,
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

    def test_delete_list_removes_file(self, tmp_path):
        create_list(tmp_path, "work", reserved_names=frozenset())

        delete_list(tmp_path, "work")

        assert not list_exists(tmp_path, "work")

    def test_delete_list_raises_for_missing(self, tmp_path):
        with pytest.raises(ListNotFoundError):
            delete_list(tmp_path, "ghost")

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
