"""native.py 工具函数测试。"""
import json
import subprocess
import pytest
from bigbear_device_record.device.native import (
    ToolNotFoundError,
    _run,
    list_adb_devices,
    list_xcrun_devices,
    list_hdc_targets,
)
from bigbear_device_record.device.base import DeviceConnectionError
from bigbear_device_record.device.base import DeviceInfo


def test_tool_not_found_is_connection_error():
    assert issubclass(ToolNotFoundError, DeviceConnectionError)


def test_run_raises_tool_not_found_on_file_not_found(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError(2, "adb not found")
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", fake_run)
    with pytest.raises(ToolNotFoundError) as exc_info:
        _run(["adb", "devices"], 10)
    assert "adb" in str(exc_info.value)


def test_run_raises_connection_error_on_timeout(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["adb"], timeout=5)
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", fake_run)
    with pytest.raises(DeviceConnectionError) as exc_info:
        _run(["adb", "devices"], 5)
    assert "timed out" in str(exc_info.value)


def test_run_returns_completed_process(monkeypatch):
    class R:
        returncode = 0
        stdout = "hello"
        stderr = ""
    def fake_run(*args, **kwargs):
        return R()
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", fake_run)
    proc = _run(["adb", "devices"], 10)
    assert proc.returncode == 0
    assert proc.stdout == "hello"


def test_list_adb_devices_parses_typical_output(monkeypatch):
    sample = (
        "List of devices attached\n"
        "emulator-5554   device  product:sdk_google_phone_x86 model:Android_SDK_built_for_x86 device:generic\n"
        "ABC123XYZ       unauthorized\n"
        "* daemon not running\n"
    )
    class R:
        returncode = 0
        stdout = sample
        stderr = ""
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", lambda *a, **k: R())

    devices = list_adb_devices()
    assert len(devices) == 2
    assert devices[0].id == "emulator-5554"
    assert devices[0].state == "device"
    assert devices[0].name == "Android_SDK_built_for_x86"
    assert devices[0].platform == "android"
    assert devices[1].id == "ABC123XYZ"
    assert devices[1].state == "unauthorized"
    assert devices[1].name == "ABC123XYZ"  # 无 model 时回退到 serial


def test_list_adb_devices_empty_when_no_devices(monkeypatch):
    class R:
        returncode = 0
        stdout = "List of devices attached\n\n"
        stderr = ""
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", lambda *a, **k: R())
    assert list_adb_devices() == []


def test_list_adb_devices_raises_tool_not_found_on_nonzero(monkeypatch):
    class R:
        returncode = 1
        stdout = ""
        stderr = "adb: command not found"
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", lambda *a, **k: R())
    with pytest.raises(ToolNotFoundError) as exc_info:
        list_adb_devices()
    assert "adb failed" in str(exc_info.value)


def test_list_xcrun_devices_returns_empty_on_non_macos(monkeypatch):
    """非 macOS 直接返回 [],不报错。"""
    import platform as _plat
    monkeypatch.setattr(_plat, "system", lambda: "Windows")
    assert list_xcrun_devices() == []


def test_list_xcrun_devices_parses_json(monkeypatch):
    import platform as _plat
    monkeypatch.setattr(_plat, "system", lambda: "Darwin")

    sample = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-17-0": [
                {"udid": "AAAA-1111", "name": "iPhone 15", "state": "Booted",
                 "isAvailable": True},
                {"udid": "BBBB-2222", "name": "iPhone 14", "state": "Shutdown",
                 "isAvailable": True},
                {"udid": "CCCC-3333", "name": "iPhone 13", "state": "Shutdown",
                 "isAvailable": False},
            ]
        }
    }
    class R:
        returncode = 0
        stdout = json.dumps(sample)
        stderr = ""
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", lambda *a, **k: R())

    devices = list_xcrun_devices()
    # 第三个 isAvailable=False 应被过滤
    assert len(devices) == 2
    assert devices[0].id == "AAAA-1111"
    assert devices[0].name == "iPhone 15"
    assert devices[0].state == "device"
    assert devices[1].id == "BBBB-2222"
    assert devices[1].state == "offline"
    assert all(d.platform == "ios" for d in devices)


def test_list_xcrun_devices_raises_tool_not_found_on_nonzero(monkeypatch):
    import platform as _plat
    monkeypatch.setattr(_plat, "system", lambda: "Darwin")
    class R:
        returncode = 1
        stdout = ""
        stderr = "xcrun: error"
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", lambda *a, **k: R())
    with pytest.raises(ToolNotFoundError):
        list_xcrun_devices()


def test_list_hdc_targets_parses_simple_output(monkeypatch):
    sample = (
        "0123456789ABCDEF\n"
        "FEDCBA9876543210\n"
    )
    class R:
        returncode = 0
        stdout = sample
        stderr = ""
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", lambda *a, **k: R())

    devices = list_hdc_targets()
    assert len(devices) == 2
    assert devices[0].id == "0123456789ABCDEF"
    assert devices[0].name == "0123456789ABCDEF"
    assert devices[0].platform == "harmony"
    assert devices[0].state == "device"


def test_list_hdc_targets_skips_empty_and_bracket_lines(monkeypatch):
    sample = (
        "[Empty]\n"
        "0123456789ABCDEF\n"
        "\n"
    )
    class R:
        returncode = 0
        stdout = sample
        stderr = ""
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", lambda *a, **k: R())
    devices = list_hdc_targets()
    assert len(devices) == 1
    assert devices[0].id == "0123456789ABCDEF"


def test_list_hdc_targets_raises_tool_not_found_on_nonzero(monkeypatch):
    class R:
        returncode = 1
        stdout = ""
        stderr = "hdc: error"
    import bigbear_device_record.device.native as native_mod
    monkeypatch.setattr(native_mod.subprocess, "run", lambda *a, **k: R())
    with pytest.raises(ToolNotFoundError):
        list_hdc_targets()
