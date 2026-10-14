import os

from bigbear_device_record.cli import build_parser, _make_vision_config


VISION_ENV_KEYS = (
    "DEVICE_VISION_API_KEY",
    "DEVICE_VISION_BASE_URL",
    "DEVICE_VISION_MODEL",
)


def clear_vision_env(monkeypatch):
    for key in VISION_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_parser_record_subcommand():
    parser = build_parser()
    args = parser.parse_args(["record", "--platform", "pc"])
    assert args.command == "record"
    assert args.platform == "pc"
    assert args.fps == 2
    assert args.port == 8765
    assert args.host == "127.0.0.1"
    assert args.enable_vision is False


def test_parser_record_with_explicit_args():
    parser = build_parser()
    args = parser.parse_args([
        "record", "--platform", "android",
        "--device-id", "emu-5554",
        "--output", "/tmp/x",
        "--port", "9000",
        "--fps", "5",
        "--enable-vision",
    ])
    assert args.platform == "android"
    assert args.device_id == "emu-5554"
    assert args.output == "/tmp/x"
    assert args.port == 9000
    assert args.fps == 5
    assert args.enable_vision is True


def test_vision_config_disabled():
    cfg = _make_vision_config(enable=False)
    assert cfg is None


def test_vision_config_enabled_from_env(monkeypatch):
    clear_vision_env(monkeypatch)
    monkeypatch.setenv("DEVICE_VISION_API_KEY", "k123")
    monkeypatch.setenv("DEVICE_VISION_BASE_URL", "https://x")
    monkeypatch.setenv("DEVICE_VISION_MODEL", "m1")
    cfg = _make_vision_config(enable=True)
    assert cfg == {"api_key": "k123", "base_url": "https://x", "model": "m1"}


def test_vision_config_ignores_legacy_env(monkeypatch):
    clear_vision_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "k123")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://x")
    monkeypatch.setenv("VISION_API_KEY", "k456")
    monkeypatch.setenv("VISION_BASE_URL", "https://y")
    cfg = _make_vision_config(enable=True)
    assert cfg is None


def test_vision_config_enabled_but_missing_env(monkeypatch):
    clear_vision_env(monkeypatch)
    cfg = _make_vision_config(enable=True)
    assert cfg is None


def test_load_cwd_env_uses_only_cwd(monkeypatch, tmp_path):
    from bigbear_device_record import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEVICE_VISION_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("DEVICE_VISION_API_KEY=cwd-key\n", encoding="utf-8")

    assert cli._load_cwd_env() == env_path
    assert os.environ["DEVICE_VISION_API_KEY"] == "cwd-key"


def test_load_cwd_env_preserves_system_env(monkeypatch, tmp_path):
    from bigbear_device_record import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEVICE_VISION_API_KEY", "system-key")
    (tmp_path / ".env").write_text("DEVICE_VISION_API_KEY=cwd-key\n", encoding="utf-8")

    cli._load_cwd_env()

    assert os.environ["DEVICE_VISION_API_KEY"] == "system-key"


def test_load_cwd_env_does_not_accept_output_directory():
    from bigbear_device_record import cli

    assert cli._load_cwd_env.__code__.co_argcount == 0


def test_load_cwd_env_ignores_missing_or_directory(monkeypatch, tmp_path):
    from bigbear_device_record import cli

    monkeypatch.chdir(tmp_path)
    assert cli._load_cwd_env() is None
    (tmp_path / ".env").mkdir()
    assert cli._load_cwd_env() is None


def test_vision_config_debug_output_does_not_expose_api_key(monkeypatch):
    from bigbear_device_record import cli

    messages = []
    secret = "super-secret-key"
    monkeypatch.setenv("DEVICE_VISION_API_KEY", secret)
    monkeypatch.setenv("DEVICE_VISION_BASE_URL", "https://vision.example")
    monkeypatch.setattr(cli, "debug", messages.append)

    cli._make_vision_config(enable=True)

    assert secret not in "\n".join(messages)
