import pytest


@pytest.fixture
def taskli_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKLI_PATH", str(tmp_path))

    return tmp_path
