"""IOSConnector smoke test。"""
from bigbear_device_record.device.ios import IOSConnector
from bigbear_device_record.device.base import DeviceInfo


def test_ios_connector_pkg_and_flags():
    assert IOSConnector.platform == "ios"
    assert IOSConnector.midscene_pkg == "@midscene/ios@1"
    assert IOSConnector.device_id_arg == "--device-id"
    assert IOSConnector.needs_screen_capture_path is False


def test_list_devices_delegates_to_native(monkeypatch):
    fake_devices = [
        DeviceInfo(id="AAAA-1111", name="iPhone 15", platform="ios", state="device"),
    ]
    from bigbear_device_record.device import ios as ios_mod
    monkeypatch.setattr(ios_mod.native, "list_xcrun_devices", lambda: fake_devices)

    c = IOSConnector(runner=lambda a, t: (0, "", ""))
    assert c.list_devices() == fake_devices


def test_connect_uses_device_id_arg():
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")
    c = IOSConnector(runner=fake_runner)
    c.connect("AAAA-1111")
    assert calls[0] == [
        "@midscene/ios@1", "connect", "--device-id", "AAAA-1111",
    ]
