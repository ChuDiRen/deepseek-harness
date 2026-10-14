"""AndroidConnector smoke test。"""
from bigbear_device_record.device.android import AndroidConnector
from bigbear_device_record.device.base import DeviceInfo


def test_android_connector_pkg_and_flags():
    assert AndroidConnector.platform == "android"
    assert AndroidConnector.midscene_pkg == "@midscene/android@1"
    # midscene-android 用 camelCase
    assert AndroidConnector.device_id_arg == "--deviceId"
    assert AndroidConnector.needs_screen_capture_path is False


def test_list_devices_delegates_to_native(monkeypatch):
    fake_devices = [
        DeviceInfo(id="emulator-5554", name="Pixel 7", platform="android", state="device"),
    ]
    from bigbear_device_record.device import android as android_mod
    monkeypatch.setattr(android_mod.native, "list_adb_devices", lambda: fake_devices)

    c = AndroidConnector(runner=lambda a, t: (0, "", ""))
    assert c.list_devices() == fake_devices


def test_connect_uses_deviceId_arg():
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")
    c = AndroidConnector(runner=fake_runner)
    c.connect("emulator-5554")
    assert calls[0] == [
        "@midscene/android@1", "connect", "--deviceId", "emulator-5554",
    ]
