import json
from datetime import datetime
from pathlib import Path

import pytest

from taskli.migrations import CURRENT_CONFIG_VERSION, CURRENT_LIST_VERSION
from taskli.models import Color, Config, Priority, Status, TaskliList
from taskli.storage import (
    CorruptedConfigFileError,
    CorruptedListFileError,
    InvalidListNameError,
    ListAlreadyExistsError,
    ListNotFoundError,
    OutdatedConfigFileError,
    OutdatedListFileError,
    TooManyAncestorListsError,
    config_file_path,
    create_list,
    delete_list,
    list_all_lists,
    list_exists,
    list_file_path,
    load_config,
    load_list,
    load_or_create_list,
    migrate_all,
    rename_list,
    resolve_storage_dir,
    resort_all_lists,
    save_config,
    save_list,
)
from utils import add_item, resource_text, sort


class TestResolveStorageDir:
    def test_uses_env_var_override(self, taskli_env):
        result = resolve_storage_dir()

        assert result == taskli_env

    def test_defaults_to_home_dotfolder(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TASKLI_PATH", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = resolve_storage_dir()

        assert result == tmp_path / ".taskli"


class TestConfigLifecycle:
    def test_config_file_path_is_dotfile(self, tmp_path):
        assert config_file_path(tmp_path) == tmp_path / ".taskli.json"

    def test_config_file_excluded_from_list_all_lists(self, tmp_path):
        save_config(tmp_path, Config())
        create_list(tmp_path, "work")

        assert list_all_lists(tmp_path) == ["work"]

    def test_load_config_creates_defaults_when_missing(self, tmp_path):
        config = load_config(tmp_path)

        assert isinstance(config, Config)
        assert config_file_path(tmp_path).exists()

    def test_load_config_round_trips(self, tmp_path):
        config = load_config(tmp_path)
        config.set_value("auto_prune", "true")
        save_config(tmp_path, config)

        reloaded = load_config(tmp_path)

        assert reloaded.auto_prune is True

    def test_load_config_raises_for_corrupted_file(self, tmp_path):
        config_file_path(tmp_path).write_text("not valid json")

        with pytest.raises(CorruptedConfigFileError):
            load_config(tmp_path)

    def test_load_config_raises_for_non_dict_json(self, tmp_path):
        config_file_path(tmp_path).write_text("null")

        with pytest.raises(CorruptedConfigFileError):
            load_config(tmp_path)

    def test_load_config_raises_for_bad_default_sort(self, tmp_path):
        config_file_path(tmp_path).write_text(
            json.dumps(
                {
                    "version": CURRENT_CONFIG_VERSION,
                    "default_sort": "bogus",
                }
            )
        )

        with pytest.raises(CorruptedConfigFileError):
            load_config(tmp_path)

    def test_load_config_raises_for_outdated_file(self, tmp_path):
        config_file_path(tmp_path).write_text(
            resource_text("config_v0_legacy.json")
        )

        with pytest.raises(OutdatedConfigFileError, match="tk --migrate"):
            load_config(tmp_path)

    def test_save_config_stamps_current_version(self, tmp_path):
        save_config(tmp_path, Config())

        raw = json.loads(config_file_path(tmp_path).read_text())

        assert raw["version"] == CURRENT_CONFIG_VERSION


class TestListLifecycle:
    def test_create_list_persists_empty_list(self, tmp_path):
        task_list = create_list(tmp_path, "work")

        assert isinstance(task_list, TaskliList)
        assert list_exists(tmp_path, "work")

    def test_create_list_rejects_duplicate(self, tmp_path):
        create_list(tmp_path, "work")

        with pytest.raises(ListAlreadyExistsError):
            create_list(tmp_path, "work")

    def test_create_list_without_color_defaults_to_none(self, tmp_path):
        task_list = create_list(tmp_path, "work")

        assert task_list.color is None

    def test_create_list_with_color_persists_it(self, tmp_path):
        task_list = create_list(tmp_path, "work", color=Color.CORAL)

        assert task_list.color is Color.CORAL
        assert load_list(tmp_path, "work").color is Color.CORAL

    @pytest.mark.parametrize(
        "name",
        ["work.", ".meetings", "work..meetings"],
        ids=["trailing-dot", "leading-dot", "consecutive-dots"],
    )
    def test_list_file_path_rejects_malformed_name(self, tmp_path, name):
        with pytest.raises(InvalidListNameError):
            list_file_path(tmp_path, name)

    def test_list_file_path_allows_two_ancestor_levels(self, tmp_path):
        list_file_path(tmp_path, "work.meetings.boring")

    def test_list_file_path_rejects_excessive_depth(self, tmp_path):
        with pytest.raises(TooManyAncestorListsError):
            list_file_path(tmp_path, "work.meetings.boring.extra")

    def test_create_list_auto_creates_missing_parent(self, tmp_path):
        create_list(tmp_path, "work.meetings")

        assert list_exists(tmp_path, "work")
        assert list_exists(tmp_path, "work.meetings")
        assert load_list(tmp_path, "work").items == []

    def test_create_list_does_not_reset_existing_parent(self, tmp_path):
        parent = create_list(tmp_path, "work")
        parent.add_item("existing task")
        save_list(tmp_path, parent)

        create_list(tmp_path, "work.meetings")

        assert load_list(tmp_path, "work").items[0].text == "existing task"

    def test_delete_list_removes_file(self, tmp_path):
        create_list(tmp_path, "work")

        delete_list(tmp_path, "work")

        assert not list_exists(tmp_path, "work")

    def test_delete_list_raises_for_missing(self, tmp_path):
        with pytest.raises(ListNotFoundError):
            delete_list(tmp_path, "ghost")

    def test_delete_list_cascades_to_descendants(self, tmp_path):
        create_list(tmp_path, "work")
        create_list(tmp_path, "work.meetings")
        create_list(tmp_path, "work.meetings.notes")

        deleted = delete_list(tmp_path, "work")

        assert deleted == ["work.meetings", "work.meetings.notes"]
        assert not list_exists(tmp_path, "work")
        assert not list_exists(tmp_path, "work.meetings")
        assert not list_exists(tmp_path, "work.meetings.notes")

    def test_delete_list_does_not_cascade_to_sibling(self, tmp_path):
        create_list(tmp_path, "work")
        create_list(tmp_path, "workshop")

        delete_list(tmp_path, "work")

        assert list_exists(tmp_path, "workshop")

    def test_rename_list_moves_file(self, tmp_path):
        task_list = create_list(tmp_path, "work")
        task_list.add_item("existing task")
        save_list(tmp_path, task_list)

        rename_list(tmp_path, "work", "job")

        assert not list_exists(tmp_path, "work")
        assert list_exists(tmp_path, "job")
        renamed = load_list(tmp_path, "job")
        assert renamed.name == "job"
        assert renamed.items[0].text == "existing task"

    def test_rename_list_returns_renamed_pairs(self, tmp_path):
        create_list(tmp_path, "work")

        renamed = rename_list(tmp_path, "work", "job")

        assert renamed == [("work", "job")]

    def test_rename_list_raises_for_missing_source(self, tmp_path):
        with pytest.raises(ListNotFoundError):
            rename_list(tmp_path, "ghost", "job")

    def test_rename_list_raises_for_existing_target(self, tmp_path):
        create_list(tmp_path, "work")
        create_list(tmp_path, "job")

        with pytest.raises(ListAlreadyExistsError):
            rename_list(tmp_path, "work", "job")

    def test_rename_list_cascades_to_descendants(self, tmp_path):
        create_list(tmp_path, "work")
        create_list(tmp_path, "work.meetings")
        create_list(tmp_path, "work.meetings.notes")

        renamed = rename_list(tmp_path, "work", "job")

        assert renamed == [
            ("work", "job"),
            ("work.meetings", "job.meetings"),
            ("work.meetings.notes", "job.meetings.notes"),
        ]
        assert not list_exists(tmp_path, "work")
        assert not list_exists(tmp_path, "work.meetings")
        assert not list_exists(tmp_path, "work.meetings.notes")
        assert list_exists(tmp_path, "job")
        assert list_exists(tmp_path, "job.meetings")
        assert list_exists(tmp_path, "job.meetings.notes")

    def test_rename_list_raises_for_colliding_descendant_target(
        self, tmp_path
    ):
        create_list(tmp_path, "work")
        create_list(tmp_path, "work.meetings")
        create_list(tmp_path, "job.meetings")

        with pytest.raises(ListAlreadyExistsError):
            rename_list(tmp_path, "work", "job")

        assert list_exists(tmp_path, "work")
        assert list_exists(tmp_path, "work.meetings")

    def test_rename_list_self_rename_is_noop(self, tmp_path):
        create_list(tmp_path, "work")

        renamed = rename_list(tmp_path, "work", "work")

        assert renamed == []
        assert list_exists(tmp_path, "work")

    def test_rename_list_does_not_affect_sibling(self, tmp_path):
        create_list(tmp_path, "work")
        create_list(tmp_path, "workshop")

        rename_list(tmp_path, "work", "job")

        assert list_exists(tmp_path, "workshop")

    def test_list_all_lists_sorted(self, tmp_path):
        create_list(tmp_path, "work")
        create_list(tmp_path, "abc")

        assert list_all_lists(tmp_path) == ["abc", "work"]


class TestLoadList:
    def test_auto_creates_default_list(self, tmp_path):
        task_list = load_list(tmp_path, "inbox")

        assert task_list.name == "inbox"
        assert list_exists(tmp_path, "inbox")

    def test_raises_for_missing_non_default_list(self, tmp_path):
        with pytest.raises(ListNotFoundError):
            load_list(tmp_path, "work")

    def test_round_trips_saved_items(self, tmp_path):
        task_list = create_list(tmp_path, "work")
        task_list.add_item("task")
        save_list(tmp_path, task_list)

        reloaded = load_list(tmp_path, "work")

        assert len(reloaded.items) == 1
        assert reloaded.items[0].text == "task"

    def test_load_list_preserves_due_date_and_description(self, tmp_path):
        (tmp_path / "inbox.json").write_text(resource_text("list_v1.json"))

        items = {i.text: i for i in load_list(tmp_path, "inbox").items}

        assert items["renew the domain"].due_date == datetime(2020, 2, 1)
        assert items["write the changelog"].description == "some longer note"

    def test_raises_for_corrupted_file(self, tmp_path):
        (tmp_path / "broken.json").write_text("not valid json")

        with pytest.raises(CorruptedListFileError):
            load_list(tmp_path, "broken")

    def test_raises_for_non_dict_json(self, tmp_path):
        (tmp_path / "broken.json").write_text("[1, 2, 3]")

        with pytest.raises(CorruptedListFileError):
            load_list(tmp_path, "broken")

    def test_save_list_persists_items_in_id_order(self, tmp_path):
        task_list = TaskliList(name="work")
        task_list.add_item("a")
        task_list.add_item("b")
        task_list.items[0].id, task_list.items[1].id = (
            task_list.items[1].id,
            task_list.items[0].id,
        )

        save_list(tmp_path, task_list)
        reloaded = load_list(tmp_path, "work")

        assert [item.text for item in reloaded.items] == ["b", "a"]

    def test_load_list_reindexes_on_read(self, tmp_path):
        task_list = TaskliList(name="work")
        task_list.add_item("a")
        task_list.add_item("b")
        task_list.items[0].id = 5
        task_list.items[1].id = 9

        save_list(tmp_path, task_list)
        reloaded = load_list(tmp_path, "work")

        assert [item.id for item in reloaded.items] == [1, 2]

    def test_save_list_stamps_current_version(self, tmp_path):
        task_list = create_list(tmp_path, "work")
        task_list.add_item("task")

        save_list(tmp_path, task_list)

        raw = json.loads(list_file_path(tmp_path, "work").read_text())
        assert raw["version"] == CURRENT_LIST_VERSION

    def test_raises_for_unversioned_legacy_file(self, tmp_path):
        path = tmp_path / "work.json"
        path.write_text(
            json.dumps(
                {
                    "name": "work",
                    "items": [
                        {
                            "id": 1,
                            "text": "task",
                            "created_at": "2020-01-01T00:00:00",
                        }
                    ],
                }
            )
        )

        with pytest.raises(OutdatedListFileError, match="tk --migrate"):
            load_list(tmp_path, "work")

    def test_raises_for_legacy_done_bool_not_silently_todo(self, tmp_path):
        path = tmp_path / "work.json"
        path.write_text(
            json.dumps(
                {
                    "name": "work",
                    "items": [
                        {
                            "id": 1,
                            "text": "task",
                            "done": True,
                            "created_at": "2020-01-01T00:00:00",
                        }
                    ],
                }
            )
        )

        with pytest.raises(OutdatedListFileError):
            load_list(tmp_path, "work")

    def test_auto_creates_configured_default_list(self, tmp_path):
        config = load_config(tmp_path)
        config.default_list = "work"
        save_config(tmp_path, config)

        task_list = load_list(tmp_path, "work")

        assert isinstance(task_list, TaskliList)
        assert task_list.name == "work"


class TestLoadOrCreateList:
    def test_creates_when_missing(self, tmp_path):
        task_list = load_or_create_list(tmp_path, "work")

        assert task_list.name == "work"
        assert list_exists(tmp_path, "work")

    def test_loads_existing(self, tmp_path):
        created = create_list(tmp_path, "work")
        created.add_item("task")
        save_list(tmp_path, created)

        loaded = load_or_create_list(tmp_path, "work")

        assert len(loaded.items) == 1

    def test_creates_missing_parent_chain(self, tmp_path):
        task_list = load_or_create_list(tmp_path, "work.meetings")

        assert task_list.name == "work.meetings"
        assert list_exists(tmp_path, "work")
        assert list_exists(tmp_path, "work.meetings")


class TestResortAllLists:
    def test_resorts_and_reindexes_every_list(self, tmp_path):
        for name in ("work", "home"):
            task_list = create_list(tmp_path, name)
            add_item(task_list, "low", priority=Priority.LOW)
            add_item(task_list, "high", priority=Priority.HIGH)
            save_list(tmp_path, task_list)

        resort_all_lists(tmp_path, sort("priority"))

        for name in ("work", "home"):
            reloaded = load_list(tmp_path, name)
            assert [item.text for item in reloaded.items] == [
                "high",
                "low",
            ]
            assert [item.id for item in reloaded.items] == [1, 2]

    def test_skips_corrupted_list(self, tmp_path):
        task_list = create_list(tmp_path, "work")
        add_item(task_list, "low", priority=Priority.LOW)
        add_item(task_list, "high", priority=Priority.HIGH)
        save_list(tmp_path, task_list)
        (tmp_path / "broken.json").write_text("not valid json")

        resort_all_lists(tmp_path, sort("priority"))

        reloaded = load_list(tmp_path, "work")
        assert [item.text for item in reloaded.items] == ["high", "low"]


class TestMigrate:
    def test_migrates_legacy_list_and_config(self, tmp_path):
        (tmp_path / "inbox.json").write_text(
            resource_text("list_v0_legacy.json")
        )
        config_file_path(tmp_path).write_text(
            resource_text("config_v0_legacy.json")
        )

        results = migrate_all(tmp_path)

        assert results == [("config", "migrated"), ("inbox", "migrated")]

        task_list = load_list(tmp_path, "inbox")
        config = load_config(tmp_path)
        assert task_list.items[0].status == Status.DONE
        assert task_list.items[0].modified_at == task_list.items[0].created_at
        assert task_list.items[2].priority == Priority.HIGH
        assert config.default_priority == Priority.HIGH

    def test_reports_current_for_v1_file(self, tmp_path):
        (tmp_path / "inbox.json").write_text(resource_text("list_v1.json"))

        results = migrate_all(tmp_path)

        assert results == [("inbox", "current")]

    def test_reports_unreadable_for_corrupt_json(self, tmp_path):
        (tmp_path / "inbox.json").write_text("not valid json")

        results = migrate_all(tmp_path)

        assert results == [("inbox", "unreadable")]

    def test_non_dict_json_reported_without_aborting_walk(self, tmp_path):
        (tmp_path / "aaa.json").write_text("null")
        (tmp_path / "zzz.json").write_text(
            resource_text("list_v0_legacy.json")
        )

        results = migrate_all(tmp_path)

        assert results == [("aaa", "unreadable"), ("zzz", "migrated")]

    def test_reports_unreadable_when_migrated_form_fails_validation(
        self, tmp_path
    ):
        broken = {"name": "inbox", "items": [{"id": 1, "done": True}]}
        path = tmp_path / "inbox.json"
        path.write_text(json.dumps(broken))

        results = migrate_all(tmp_path)

        assert results == [("inbox", "unreadable")]
        assert json.loads(path.read_text()) == broken

    def test_malformed_item_structure_does_not_crash_walk(self, tmp_path):
        (tmp_path / "aaa.json").write_text('{"name": "aaa", "items": [null]}')
        (tmp_path / "zzz.json").write_text(
            resource_text("list_v0_legacy.json")
        )

        results = migrate_all(tmp_path)

        assert results == [("aaa", "unreadable"), ("zzz", "migrated")]

    def test_unresolvable_list_name_does_not_crash_walk(self, tmp_path):
        (tmp_path / "a.b.c.d.json").write_text('{"name": "a.b.c.d"}')
        (tmp_path / "zzz.json").write_text(
            resource_text("list_v0_legacy.json")
        )

        results = migrate_all(tmp_path)

        assert results == [("a.b.c.d", "unreadable"), ("zzz", "migrated")]

    def test_second_run_is_noop(self, tmp_path):
        (tmp_path / "inbox.json").write_text(
            resource_text("list_v0_legacy.json")
        )
        config_file_path(tmp_path).write_text(
            resource_text("config_v0_legacy.json")
        )
        migrate_all(tmp_path)

        results = migrate_all(tmp_path)

        assert results == [("config", "current"), ("inbox", "current")]
