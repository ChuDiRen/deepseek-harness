# -*- coding: utf-8 -*-
"""ADBManager 单元测试（mock subprocess）"""
import io
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from bigbear_android.adb import (
    ADBManager,
    ADBCommandError,
    ADBNotFoundError,
    DeviceNotFoundError,
)


# ===== 设备列表 =====

def test_list_devices_parses_adb_devices_l_output():
    """正确解析 adb devices -l 输出"""
    fake_stdout = (
        "List of devices attached\n"
        "emulator-5554   device product:sdk_google_phone_x86 model:Pixel_5_API_30 device:raven\n"
        "ABCDEF123456    device product:berlin model:Redmi_Note_8 device:berlin usb:2-1.4\n"
        "unauth-device   unauthorized\n"
    )
    fake_result = MagicMock(returncode=0, stdout=fake_stdout, stderr="")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        devices = mgr.list_devices()

    assert len(devices) == 2
    assert devices[0]["serial"] == "emulator-5554"
    assert devices[0]["state"] == "device"
    assert devices[0]["model"] == "Pixel_5_API_30"
    assert devices[1]["serial"] == "ABCDEF123456"
    assert devices[1]["usb"] == "2-1.4"


def test_list_devices_adb_failure_raises():
    """adb devices 失败时抛 ADBCommandError"""
    fake_result = MagicMock(returncode=1, stdout="", stderr="daemon not running")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        with pytest.raises(ADBCommandError):
            mgr.list_devices()


def test_list_devices_empty_returns_empty_list():
    """无设备时返回空列表"""
    fake_result = MagicMock(returncode=0, stdout="List of devices attached\n", stderr="")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        devices = mgr.list_devices()
    assert devices == []


# ===== 设备选择 =====

def test_select_device_no_serial_uses_first():
    """无 serial 时选首个 device"""
    fake_stdout = "List of devices attached\nemulator-5554   device product:x model:y\n"
    fake_result = MagicMock(returncode=0, stdout=fake_stdout, stderr="")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        serial = mgr.select_device()
    assert serial == "emulator-5554"
    assert mgr.device_serial == "emulator-5554"


def test_select_device_explicit_serial():
    """显式 serial 时直接使用，不调用 list_devices"""
    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        serial = mgr.select_device(serial="custom-device-1")
    assert serial == "custom-device-1"
    assert mgr.device_serial == "custom-device-1"


def test_select_device_no_devices_raises():
    """无设备时抛 DeviceNotFoundError"""
    fake_result = MagicMock(returncode=0, stdout="List of devices attached\n", stderr="")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        with pytest.raises(DeviceNotFoundError):
            mgr.select_device()


# ===== 命令执行 =====

def test_shell_executes_with_serial():
    """shell 命令自动加上 -s serial"""
    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        mgr.device_serial = "test-serial"
        mgr._connected = True
        rc, out, err = mgr.shell("echo", "hello")
        assert rc == 0
        assert out == "output"
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == ["/usr/bin/adb", "-s", "test-serial", "shell", "echo", "hello"]


def test_shell_timeout_raises():
    """shell 超时时抛 ADBCommandError"""
    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", side_effect=subprocess.TimeoutExpired("adb", 5)):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        mgr.device_serial = "test-serial"
        mgr._connected = True
        with pytest.raises(ADBCommandError):
            mgr.shell("sleep", "10", timeout=5)


def test_exec_out_returns_bytes():
    """exec-out 返回原始字节"""
    fake_bytes = b"\x89PNG\r\n\x1a\nfake_png_content"

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=fake_bytes, stderr=b"")
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        mgr.device_serial = "test-serial"
        mgr._connected = True
        data = mgr.exec_out("screencap", "-p")
    assert data == fake_bytes


# ===== 屏幕尺寸 =====

def test_get_screen_size_caches():
    """屏幕尺寸会被缓存"""
    fake_result = MagicMock(returncode=0, stdout="Physical size: 1080x1920\n", stderr="")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        mgr.device_serial = "test-serial"
        mgr._connected = True

        size1 = mgr.get_screen_size()
        size2 = mgr.get_screen_size()  # 第二次应命中缓存
    assert size1 == (1080, 1920)
    assert size2 == (1080, 1920)


def test_get_screen_size_unparseable_raises():
    """无法解析的输出抛错"""
    fake_result = MagicMock(returncode=0, stdout="unexpected format", stderr="")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        mgr.device_serial = "test-serial"
        mgr._connected = True
        with pytest.raises(ADBCommandError):
            mgr.get_screen_size()


# ===== 截图 =====

def _make_png_bytes(width: int = 100, height: int = 100) -> bytes:
    """生成测试用 PNG 字节"""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_screencap_base64_returns_jpeg_by_default():
    """默认返回 JPEG base64"""
    png_bytes = _make_png_bytes(200, 400)
    fake_result = MagicMock(returncode=0, stdout=png_bytes, stderr=b"")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        mgr.device_serial = "test-serial"
        mgr._connected = True
        img_b64, pil_img = mgr.screencap_base64(use_jpeg=True)

    import base64
    assert isinstance(img_b64, str)
    # JPEG 解码后 mode 为 RGB
    decoded = base64.b64decode(img_b64)
    assert decoded[:3] == b"\xff\xd8\xff"  # JPEG magic bytes
    assert pil_img.size == (200, 400)
    assert pil_img.mode == "RGB"


def test_screencap_base64_returns_png_when_disabled():
    """use_jpeg=False 时返回 PNG"""
    png_bytes = _make_png_bytes()
    fake_result = MagicMock(returncode=0, stdout=png_bytes, stderr=b"")

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        mgr.device_serial = "test-serial"
        mgr._connected = True
        img_b64, _ = mgr.screencap_base64(use_jpeg=False)

    import base64
    decoded = base64.b64decode(img_b64)
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


def test_screencap_retries_on_failure():
    """截图失败时自动重试"""
    png_bytes = _make_png_bytes()

    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"), \
         patch("bigbear_android.adb.subprocess.run") as mock_run:
        # 前两次失败，第三次成功
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=b"", stderr=b"error"),
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # exec-out 失败但 PNG 为空也算成功路径
            MagicMock(returncode=0, stdout=png_bytes, stderr=b""),
        ]
        ADBManager.reset_instance()
        mgr = ADBManager.get_instance()
        mgr.device_serial = "test-serial"
        mgr._connected = True
        img_b64, _ = mgr.screencap_base64(max_retries=2)
    assert img_b64


# ===== ADB 查找 =====

def test_adb_not_found_in_path_raises():
    """adb 不在 PATH 中时抛 ADBNotFoundError"""
    with patch("bigbear_android.adb.shutil.which", return_value=None), \
         patch("bigbear_android.adb.os.getenv", return_value=None):
        with pytest.raises(ADBNotFoundError):
            ADBManager()


def test_adb_custom_path_used():
    """通过 ANDROID_ADB_PATH 指定路径"""
    with patch("bigbear_android.adb.os.getenv", return_value="/custom/path/adb"), \
         patch("bigbear_android.adb.Path.is_file", return_value=True):
        mgr = ADBManager()
        assert mgr._adb_path == "/custom/path/adb"


# ===== 单例 =====

def test_singleton_returns_same_instance():
    """get_instance 返回同一实例"""
    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"):
        ADBManager.reset_instance()
        a = ADBManager.get_instance()
        b = ADBManager.get_instance()
    assert a is b


def test_reset_instance_clears_singleton():
    """reset_instance 清空单例"""
    with patch("bigbear_android.adb.shutil.which", return_value="/usr/bin/adb"):
        a = ADBManager.get_instance()
        ADBManager.reset_instance()
        b = ADBManager.get_instance()
    assert a is not b


# ===== IME / 应用管理 / 广播 =====

def test_is_installed_true_when_package_listed():
    """pm list packages 包含包名时返回 True"""
    fake_result = MagicMock(returncode=0, stdout="package:com.android.adbkeyboard\n", stderr="")
    with patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        mgr = ADBManager.__new__(ADBManager)
        mgr.device_serial = "test_serial"
        mgr._adb_path = "/usr/bin/adb"
        mgr._connected = True
        assert mgr.is_installed("com.android.adbkeyboard") is True


def test_is_installed_false_when_not_listed():
    fake_result = MagicMock(returncode=0, stdout="package:com.other.app\n", stderr="")
    with patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        mgr = ADBManager.__new__(ADBManager)
        mgr.device_serial = "test_serial"
        mgr._adb_path = "/usr/bin/adb"
        mgr._connected = True
        assert mgr.is_installed("com.android.adbkeyboard") is False


def test_is_installed_false_on_command_failure():
    fake_result = MagicMock(returncode=1, stdout="", stderr="")
    with patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        mgr = ADBManager.__new__(ADBManager)
        mgr.device_serial = "test_serial"
        mgr._adb_path = "/usr/bin/adb"
        mgr._connected = True
        assert mgr.is_installed("com.android.adbkeyboard") is False


def test_get_current_ime_returns_stripped():
    """get_current_ime 返回去掉换行的 IME ID"""
    fake_result = MagicMock(returncode=0, stdout="com.baidu.input_vivo/.ImeVivoService\n", stderr="")
    with patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        mgr = ADBManager.__new__(ADBManager)
        mgr.device_serial = "test_serial"
        mgr._adb_path = "/usr/bin/adb"
        mgr._connected = True
        assert mgr.get_current_ime() == "com.baidu.input_vivo/.ImeVivoService"


def test_set_ime_raises_on_failure():
    """set_ime 在 rc != 0 时抛 ADBCommandError"""
    fake_result = MagicMock(returncode=1, stdout="", stderr="IME not found")
    with patch("bigbear_android.adb.subprocess.run", return_value=fake_result):
        mgr = ADBManager.__new__(ADBManager)
        mgr.device_serial = "test_serial"
        mgr._adb_path = "/usr/bin/adb"
        mgr._connected = True
        with pytest.raises(ADBCommandError):
            mgr.set_ime("com.android.adbkeyboard/.AdbIME")


def test_broadcast_passes_extras_correctly():
    """broadcast 把 extras 转为 --es key value 参数"""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return MagicMock(returncode=0, stdout="Broadcast completed: result=0", stderr="")

    with patch("bigbear_android.adb.subprocess.run", side_effect=fake_run):
        mgr = ADBManager.__new__(ADBManager)
        mgr.device_serial = "test_serial"
        mgr._adb_path = "/usr/bin/adb"
        mgr._connected = True
        rc, stdout, stderr = mgr.broadcast("ADB_INPUT_TEXT", msg="别墅")

    assert rc == 0
    assert "result=0" in stdout
    # 验证命令构造：adb shell am broadcast -a ADB_INPUT_TEXT --es msg 别墅
    cmd = captured["cmd"]
    assert "am" in cmd
    assert "broadcast" in cmd
    assert "ADB_INPUT_TEXT" in cmd
    assert "--es" in cmd
    assert "msg" in cmd
    assert "别墅" in cmd