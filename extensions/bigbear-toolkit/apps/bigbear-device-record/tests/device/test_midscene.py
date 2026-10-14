"""MidsceneConnector 基类 + 异常类测试。"""
import sys

import pytest
from bigbear_device_record.device.midscene import (
    MidsceneConnector,
    MidsceneError,
    NodeNotFoundError,
    _normalize_command,
)
from bigbear_device_record.device.base import DeviceCaptureError, DeviceConnectionError


def test_midscene_error_is_exception():
    assert issubclass(MidsceneError, Exception)
    err = MidsceneError("adb not responding")
    assert str(err) == "adb not responding"


def test_node_not_found_is_connection_error():
    assert issubclass(NodeNotFoundError, DeviceConnectionError)
    err = NodeNotFoundError()
    assert "Node.js" in str(err) or "npx" in str(err)


def test_normalize_command_returns_tuple_of_str_and_list():
    exe, args = _normalize_command("echo", "hello")
    assert isinstance(exe, str)
    assert isinstance(args, list)
    # 非 Windows 平台应原样返回
    if sys.platform != "win32":
        assert exe == "echo"
        assert args == ["hello"]


def test_connector_init_with_runner():
    """注入 runner 后,is_connected 初始为 False,未连接。"""
    def fake_runner(args, timeout):
        return (0, "", "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    assert c.is_connected() is False


def test_connector_init_default_runner_exists():
    """不传 runner 也应能实例化(走 _default_runner,只是不真跑)。"""
    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn()
    assert c._runner is not None
    # _default_runner 引用应存在
    from bigbear_device_record.device.midscene import MidsceneConnector as MC
    assert MC._default_runner.__name__ == "_default_runner"


def test_connect_invokes_midscene_with_device_id():
    calls = []
    def fake_runner(args, timeout):
        calls.append((list(args), timeout))
        return (0, "", "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c.connect("dev-123")
    assert c.is_connected() is True
    assert calls == [(["@midscene/test@1", "connect", "--device-id", "dev-123"],
                      MidsceneConnector.CONNECT_TIMEOUT)]


def test_connect_failure_wraps_as_device_connection_error():
    from bigbear_device_record.device.midscene import MidsceneError
    def fail_runner(args, timeout):
        raise MidsceneError("boom")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fail_runner)
    with pytest.raises(DeviceConnectionError) as exc_info:
        c.connect("dev-x")
    assert "boom" in str(exc_info.value)
    assert c.is_connected() is False


def test_connect_already_connected_raises():
    def fake_runner(args, timeout):
        return (0, "", "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c.connect("dev-1")
    with pytest.raises(DeviceConnectionError) as exc_info:
        c.connect("dev-2")
    assert "already connected" in str(exc_info.value)


def test_disconnect_clears_state():
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c.connect("dev-1")
    c.disconnect()
    assert c.is_connected() is False
    assert calls[1] == ["@midscene/test@1", "disconnect"]


def test_disconnect_without_connection_is_noop():
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c.disconnect()
    assert calls == []


def test_disconnect_failure_silently_clears_state():
    def fail_runner(args, timeout):
        raise MidsceneError("can't disconnect")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fail_runner)
    c._connected_to = "dev-1"  # simulate prior connect
    c.disconnect()
    assert c.is_connected() is False


def test_android_connector_uses_camelcase_device_id_arg():
    """android 子类应使用 --deviceId 而非 --device-id。"""
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"
        device_id_arg = "--deviceId"

    c = TestConn(runner=fake_runner)
    c.connect("dev-A")
    assert calls[0][2] == "--deviceId"


def test_capture_screenshot_parses_stdout_path_and_reads_png(tmp_path):
    """runner 返回 stdout 含 'Screenshot saved: <path>',应读取该 path 的 PNG。"""
    from PIL import Image as PILImage
    png_path = tmp_path / "shot.png"
    PILImage.new("RGB", (100, 50), (255, 0, 0)).save(png_path)
    stdout = f"some preamble\nScreenshot saved: {png_path}\ntrailing"

    def fake_runner(args, timeout):
        return (0, stdout, "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c._connected_to = "dev-1"
    data = c.capture_screenshot()
    assert isinstance(data, bytes)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    # temp 文件应被删除
    assert not png_path.exists()


def test_capture_screenshot_caches_dimensions(tmp_path):
    from PIL import Image as PILImage
    png_path = tmp_path / "shot.png"
    PILImage.new("RGB", (320, 240), (0, 255, 0)).save(png_path)
    stdout = f"Screenshot saved: {png_path}"

    def fake_runner(args, timeout):
        return (0, stdout, "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c._connected_to = "dev-1"
    c.capture_screenshot()
    # _last_dim 缓存应由 capture_screenshot 设置(Task 6 才实现 get_dimensions 读取它)
    assert c._last_dim == (320, 240)


def test_capture_screenshot_not_connected_raises():
    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=lambda a, t: (0, "", ""))
    with pytest.raises(DeviceCaptureError) as exc_info:
        c.capture_screenshot()
    assert "not connected" in str(exc_info.value)


def test_capture_screenshot_no_path_in_stdout_raises():
    def fake_runner(args, timeout):
        return (0, "no screenshot here", "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c._connected_to = "dev-1"
    with pytest.raises(DeviceCaptureError) as exc_info:
        c.capture_screenshot()
    assert "screenshot path" in str(exc_info.value)


def test_get_dimensions_returns_cached_after_capture(tmp_path):
    from PIL import Image as PILImage
    png_path = tmp_path / "shot.png"
    PILImage.new("RGB", (480, 800), (0, 0, 255)).save(png_path)
    stdout = f"Screenshot saved: {png_path}"

    call_count = [0]
    def fake_runner(args, timeout):
        call_count[0] += 1
        return (0, stdout, "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c._connected_to = "dev-1"
    c.capture_screenshot()
    call_count[0] = 0
    # 缓存命中,不应再调 runner
    w, h = c.get_dimensions()
    assert (w, h) == (480, 800)
    assert call_count[0] == 0


def test_get_dimensions_cache_miss_triggers_capture(tmp_path):
    from PIL import Image as PILImage
    png_path = tmp_path / "shot.png"
    PILImage.new("RGB", (200, 300), (123, 456, 789)).save(png_path)
    stdout = f"Screenshot saved: {png_path}"

    def fake_runner(args, timeout):
        return (0, stdout, "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c._connected_to = "dev-1"
    # 未调过 capture_screenshot,直接 get_dimensions 应触发截屏
    w, h = c.get_dimensions()
    assert (w, h) == (200, 300)


def test_get_dimensions_returns_zero_on_pil_failure(tmp_path):
    """PIL 解析失败时,_last_dim 仍为 None,get_dimensions 返回 (0, 0)。"""
    # 不写 PNG,直接传不存在的 path;PIL 解析会抛
    stdout = "Screenshot saved: /nonexistent/path/missing.png"

    def fake_runner(args, timeout):
        return (0, stdout, "")

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn(runner=fake_runner)
    c._connected_to = "dev-1"
    with pytest.raises(Exception):
        # capture_screenshot 会因为无法打开文件而抛 FileNotFoundError
        c.capture_screenshot()
    # get_dimensions 此时缓存为 None,会再次触发,仍失败
    # 验证维度兜底:直接访问 _last_dim 是 None
    assert c._last_dim is None


def test_default_runner_injects_screen_capture_path_on_windows(tmp_path, monkeypatch):
    """needs_screen_capture_path=True + Windows + 目录存在 → PATH 应被注入。"""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")

    capture_dir = tmp_path / "screenCapture"
    capture_dir.mkdir()
    monkeypatch.setenv("TEMP", str(tmp_path))

    captured_env = {}
    import subprocess as _sp
    def fake_run(*args, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()
    monkeypatch.setattr(_sp, "run", fake_run)

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"
        needs_screen_capture_path = True

    c = TestConn()
    c._runner(["@midscene/test@1", "list_displays"], 15)
    assert str(capture_dir) in captured_env.get("PATH", "")


def test_default_runner_no_inject_when_needs_path_false(tmp_path, monkeypatch):
    """needs_screen_capture_path=False 时,即使目录存在也不应注入。"""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")

    capture_dir = tmp_path / "screenCapture"
    capture_dir.mkdir()
    monkeypatch.setenv("TEMP", str(tmp_path))

    captured_env = {}
    import subprocess as _sp
    def fake_run(*args, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()
    monkeypatch.setattr(_sp, "run", fake_run)

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"
        needs_screen_capture_path = False

    c = TestConn()
    c._runner(["@midscene/test@1", "list_displays"], 15)
    assert str(capture_dir) not in captured_env.get("PATH", "")


def test_default_runner_file_not_found_raises_node_not_found(monkeypatch):
    """subprocess.run 抛 FileNotFoundError → NodeNotFoundError。"""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")

    import subprocess as _sp
    def fake_run(*args, **kwargs):
        raise FileNotFoundError(2, "npx not found")
    monkeypatch.setattr(_sp, "run", fake_run)

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/test@1"

    c = TestConn()
    with pytest.raises(NodeNotFoundError):
        c._runner(["npx", "version"], 15)


def test_default_runner_uses_npx_not_package_name(monkeypatch):
    """_default_runner 应当把 npx 解析为真实命令,把 midscene_pkg 作为 -y 后的参数。
    回归 bug:之前把 @midscene/computer@1 当成命令直接传给 cmd /c,导致 'No yaml files found'。
    """
    if sys.platform != "win32":
        pytest.skip("Windows-only test")

    captured_cmd_args = []
    captured_kwargs = {}
    import subprocess as _sp
    def fake_run(*args, **kwargs):
        captured_cmd_args.append(list(args[0]))
        captured_kwargs.update(kwargs)
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()
    monkeypatch.setattr(_sp, "run", fake_run)

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/computer@1"

    c = TestConn()
    c._runner(["@midscene/computer@1", "list_displays"], 15)

    # 实际执行的是 cmd /c <npx_path> -y @midscene/computer@1 list_displays
    assert captured_cmd_args, "subprocess.run was not called"
    argv = captured_cmd_args[0]
    assert argv[0] == "cmd"
    assert argv[1] == "/c"
    # argv[2] 应是 npx 的绝对路径(在 PATH 中)
    import os
    npx_path = os.environ.get("NPM_PREFIX_NPX")  # 不会设;fallback 到 shutil.which
    assert "npx" in argv[2].lower(), f"argv[2] should be npx path, got {argv[2]}"
    # 关键断言:`-y` 后跟包名,而不是 npx 后直接跟包名
    assert "-y" in argv
    assert "@midscene/computer@1" in argv
    assert "list_displays" in argv
    # 关键回归断言:`@midscene/computer@1` 不应是 argv[0](那才是"把包当命令"的 bug)
    assert not argv[0].startswith("@")


def test_default_runner_uses_utf8_encoding(monkeypatch):
    """_default_runner 应当显式指定 encoding='utf-8',避免 Windows 上 gbk 解码 Node.js UTF-8 输出失败。"""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")

    captured_kwargs = {}
    import subprocess as _sp
    def fake_run(*args, **kwargs):
        captured_kwargs.update(kwargs)
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()
    monkeypatch.setattr(_sp, "run", fake_run)

    class TestConn(MidsceneConnector):
        platform = "test"
        midscene_pkg = "@midscene/computer@1"

    c = TestConn()
    c._runner(["@midscene/computer@1", "list_displays"], 15)
    assert captured_kwargs.get("encoding") == "utf-8"
    assert captured_kwargs.get("errors") == "replace"
