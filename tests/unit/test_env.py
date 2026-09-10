from pathlib import Path

from taskli.env import resolve_storage_dir, scan_list_names


class TestResolveStorageDir:
    def test_uses_env_var_override(self, taskli_env):
        result = resolve_storage_dir()

        assert result == taskli_env

    def test_defaults_to_home_dotfolder(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TASKLI_PATH", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = resolve_storage_dir()

        assert result == tmp_path / ".taskli"

    def test_creates_dir_when_missing(self, monkeypatch, tmp_path):
        target = tmp_path / "nested" / "store"
        monkeypatch.setenv("TASKLI_PATH", str(target))

        result = resolve_storage_dir()

        assert result == target
        assert target.is_dir()


class TestScanListNames:
    def test_returns_sorted_stems(self, tmp_path):
        (tmp_path / "work.json").write_text("{}")
        (tmp_path / "abc.json").write_text("{}")

        assert scan_list_names(tmp_path) == ["abc", "work"]

    def test_excludes_config_file(self, tmp_path):
        (tmp_path / "work.json").write_text("{}")
        (tmp_path / ".taskli.json").write_text("{}")

        assert scan_list_names(tmp_path) == ["work"]

    def test_empty_dir_returns_empty(self, tmp_path):
        assert scan_list_names(tmp_path) == []
