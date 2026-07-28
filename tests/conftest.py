import pytest


@pytest.fixture
def todos_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TODOS_PATH", str(tmp_path))

    return tmp_path
