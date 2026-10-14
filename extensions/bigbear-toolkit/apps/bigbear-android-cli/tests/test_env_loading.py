import os

import pytest

from bigbear_android import cli


ENV_KEY = "ANDROID_AI_API_KEY"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(ENV_KEY, raising=False)


def test_load_cwd_env_loads_cwd_file(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(f"{ENV_KEY}=cwd-key\n", encoding="utf-8")

    assert cli._load_cwd_env() == env_path
    assert os.environ[ENV_KEY] == "cwd-key"


def test_load_cwd_env_does_not_override_system_env(monkeypatch, tmp_path):
    monkeypatch.setenv(ENV_KEY, "system-key")
    (tmp_path / ".env").write_text(f"{ENV_KEY}=cwd-key\n", encoding="utf-8")

    cli._load_cwd_env()

    assert os.environ[ENV_KEY] == "system-key"


def test_load_cwd_env_ignores_missing_or_directory_path(tmp_path):
    assert cli._load_cwd_env() is None
    (tmp_path / ".env").mkdir()
    assert cli._load_cwd_env() is None


def test_load_cwd_env_does_not_search_parent(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(f"{ENV_KEY}=parent-key\n", encoding="utf-8")
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    assert cli._load_cwd_env() is None
    assert ENV_KEY not in os.environ


def test_load_config_does_not_load_dotenv_implicitly(tmp_path):
    (tmp_path / ".env").write_text(f"{ENV_KEY}=cwd-key\n", encoding="utf-8")

    assert cli.load_config()["api_key"] == ""
