import pytest
from bigbear_device_record.device.manager import DeviceManager, PLATFORM_MAP
from bigbear_device_record.device.pc import ComputerConnector
from bigbear_device_record.device.android import AndroidConnector
from bigbear_device_record.device.base import (
    DeviceConnectionError,
    DeviceInfo,
)


def test_pc_platform_returns_pc_connector():
    mgr = DeviceManager(platform="pc")
    assert isinstance(mgr.connector, ComputerConnector)
    assert mgr.platform == "pc"


def test_android_platform_returns_android_connector():
    mgr = DeviceManager(platform="android")
    assert isinstance(mgr.connector, AndroidConnector)


def test_unknown_platform_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported platform"):
        DeviceManager(platform="blackberry")


def _make_fake_pc_connector():
    """Build a ComputerConnector that doesn't actually run npx."""

    class FakePCConnector(ComputerConnector):
        def __init__(self):
            super().__init__(runner=lambda a, t: (0, "", ""))

        def list_devices(self):
            return [
                DeviceInfo(id="local-pc", name="Local", platform="pc", state="device"),
                DeviceInfo(id="dev-1", name="Test", platform="pc", state="device"),
            ]

    return FakePCConnector


def test_list_devices_passthrough(monkeypatch):
    monkeypatch.setitem(PLATFORM_MAP, "pc", _make_fake_pc_connector())
    mgr = DeviceManager(platform="pc")
    devices = mgr.list_devices()
    assert len(devices) >= 1
    assert devices[0].platform == "pc"


def test_connect_default_device(monkeypatch):
    monkeypatch.setitem(PLATFORM_MAP, "pc", _make_fake_pc_connector())
    mgr = DeviceManager(platform="pc")
    info = mgr.connect()  # 无 device_id 时选第一个
    assert info.platform == "pc"
    assert mgr.connector.is_connected()


def test_connect_explicit_device_id(monkeypatch):
    monkeypatch.setitem(PLATFORM_MAP, "pc", _make_fake_pc_connector())
    mgr = DeviceManager(platform="pc", device_id="local-pc")
    info = mgr.connect()
    assert info.id == "local-pc"


def test_disconnect(monkeypatch):
    monkeypatch.setitem(PLATFORM_MAP, "pc", _make_fake_pc_connector())
    mgr = DeviceManager(platform="pc")
    mgr.connect()
    assert mgr.connector.is_connected()
    mgr.disconnect()
    assert not mgr.connector.is_connected()
