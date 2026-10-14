"""HarmonyConnector smoke test。"""
from bigbear_device_record.device.harmony import HarmonyConnector
from bigbear_device_record.device.base import DeviceInfo


def test_harmony_connector_pkg_and_flags():
    assert HarmonyConnector.platform == "harmony"
    assert HarmonyConnector.midscene_pkg == "@midscene/harmony@1"
    assert HarmonyConnector.device_id_arg == "--device-id"
    assert HarmonyConnector.needs_screen_capture_path is False


def test_list_devices_delegates_to_native(monkeypatch):
    fake_devices = [
        DeviceInfo(id="0123456789ABCDEF", name="Mate 60", platform="harmony", state="device"),
    ]
    from bigbear_device_record.device import harmony as harmony_mod
    monkeypatch.setattr(harmony_mod.native, "list_hdc_targets", lambda: fake_devices)

    c = HarmonyConnector(runner=lambda a, t: (0, "", ""))
    assert c.list_devices() == fake_devices


def test_connect_uses_device_id_arg():
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")
    c = HarmonyConnector(runner=fake_runner)
    c.connect("0123456789ABCDEF")
    assert calls[0] == [
        "@midscene/harmony@1", "connect", "--device-id", "0123456789ABCDEF",
    ]
