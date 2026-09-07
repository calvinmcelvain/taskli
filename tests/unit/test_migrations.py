import copy

from taskli.migrations import (
    CURRENT_CONFIG_VERSION,
    CURRENT_LIST_VERSION,
    config_needs_migration,
    list_needs_migration,
    migrate_config,
    migrate_list,
)
from utils import resource_dict


class TestMigrateList:
    def test_transforms_legacy_item_shape(self):
        raw = resource_dict("list_v0_legacy.json")

        migrated = migrate_list(raw)

        done, undone, prioritized = migrated["items"]
        assert done["status"] == "done"
        assert "done" not in done
        assert undone["status"] == "todo"
        assert done["modified_at"] == done["created_at"]
        assert undone["modified_at"] == "2020-01-03T00:00:00"
        assert prioritized["priority"] == "high"
        assert done["id"] == "1"
        assert undone["id"] == "2"
        assert prioritized["id"] == "3"
        assert done["children"] == []
        assert undone["children"] == []
        assert prioritized["children"] == []

    def test_stamps_current_version(self):
        raw = resource_dict("list_v0_legacy.json")

        migrated = migrate_list(raw)

        assert migrated["version"] == CURRENT_LIST_VERSION

    def test_idempotent(self):
        raw = resource_dict("list_v0_legacy.json")

        once = migrate_list(raw)
        twice = migrate_list(once)

        assert twice == once

    def test_current_shape_without_version_is_stamped_noop(self):
        expected = resource_dict("list_v1.json")
        raw = resource_dict("list_v1.json")
        raw.pop("version")

        migrated = migrate_list(raw)

        assert migrated == expected

    def test_does_not_mutate_argument(self):
        raw = resource_dict("list_v0_legacy.json")
        original = copy.deepcopy(raw)

        migrate_list(raw)

        assert raw == original

    def test_needs_migration_true_for_legacy(self):
        raw = resource_dict("list_v0_legacy.json")

        assert list_needs_migration(raw) is True

    def test_needs_migration_false_for_current(self):
        raw = resource_dict("list_v1.json")

        assert list_needs_migration(raw) is False

    def test_null_version_treated_as_legacy(self):
        raw = {"version": None, "name": "inbox", "items": []}

        assert list_needs_migration(raw) is True

    def test_bool_version_treated_as_legacy(self):
        raw = {"version": True, "name": "inbox", "items": []}

        assert list_needs_migration(raw) is True

    def test_newer_version_is_not_stamped_backwards(self):
        raw = {"version": 5, "name": "inbox", "items": []}

        migrated = migrate_list(raw)

        assert migrated["version"] == 5


class TestMigrateConfig:
    def test_transforms_priority_dict_to_label(self):
        raw = resource_dict("config_v0_legacy.json")

        migrated = migrate_config(raw)

        assert migrated["default_priority"] == "high"

    def test_stamps_current_version(self):
        raw = resource_dict("config_v0_legacy.json")

        migrated = migrate_config(raw)

        assert migrated["version"] == CURRENT_CONFIG_VERSION

    def test_idempotent(self):
        raw = resource_dict("config_v0_legacy.json")

        once = migrate_config(raw)
        twice = migrate_config(once)

        assert twice == once

    def test_current_shape_without_version_is_stamped_noop(self):
        expected = resource_dict("config_v1.json")
        raw = resource_dict("config_v1.json")
        raw.pop("version")

        migrated = migrate_config(raw)

        assert migrated == expected

    def test_does_not_mutate_argument(self):
        raw = resource_dict("config_v0_legacy.json")
        original = copy.deepcopy(raw)

        migrate_config(raw)

        assert raw == original

    def test_needs_migration_true_for_legacy(self):
        raw = resource_dict("config_v0_legacy.json")

        assert config_needs_migration(raw) is True

    def test_needs_migration_false_for_current(self):
        raw = resource_dict("config_v1.json")

        assert config_needs_migration(raw) is False

    def test_null_version_treated_as_legacy(self):
        raw = {"version": None, "default_priority": "medium"}

        assert config_needs_migration(raw) is True

    def test_bool_version_treated_as_legacy(self):
        raw = {"version": True, "default_priority": "medium"}

        assert config_needs_migration(raw) is True

    def test_newer_version_is_not_stamped_backwards(self):
        raw = {"version": 5, "default_priority": "medium"}

        migrated = migrate_config(raw)

        assert migrated["version"] == 5
