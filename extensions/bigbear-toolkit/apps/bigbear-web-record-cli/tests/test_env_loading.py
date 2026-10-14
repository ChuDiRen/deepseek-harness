import os
import sys

from bigbear_web_record import cli


ENV_KEY = "WEB_VISION_API_KEY"


def test_load_cwd_env_uses_only_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(ENV_KEY, raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(f"{ENV_KEY}=cwd-key\n", encoding="utf-8")

    assert cli._load_cwd_env() == env_path
    assert os.environ[ENV_KEY] == "cwd-key"


def test_load_cwd_env_preserves_system_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(ENV_KEY, "system-key")
    (tmp_path / ".env").write_text(f"{ENV_KEY}=cwd-key\n", encoding="utf-8")

    cli._load_cwd_env()

    assert os.environ[ENV_KEY] == "system-key"


def test_load_cwd_env_does_not_accept_output_directory():
    assert cli._load_cwd_env.__code__.co_argcount == 0


def test_load_cwd_env_ignores_missing_or_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert cli._load_cwd_env() is None
    (tmp_path / ".env").mkdir()
    assert cli._load_cwd_env() is None


def test_debug_output_does_not_expose_vision_api_key(monkeypatch, tmp_path):
    from bigbear_web_record.recorder import browser as browser_module

    class FakeRecorder:
        browser = None
        _record_count = 0

        def __init__(self, *args, **kwargs):
            pass

        async def start(self, cdp_port):
            pass

        def save_current_recording(self):
            return 0, 0

    messages = []
    secret = "super-secret-key"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WEB_VISION_API_KEY", secret)
    monkeypatch.setenv("WEB_VISION_BASE_URL", "https://vision.example")
    monkeypatch.setattr(browser_module, "BrowserRecorder", FakeRecorder)
    monkeypatch.setattr(cli, "debug", messages.append)
    monkeypatch.setattr(
        sys,
        "argv",
        ["bigbear-web-record", "record", "https://example.com", "--enable-vision"],
    )

    cli.main()

    assert secret not in "\n".join(messages)
