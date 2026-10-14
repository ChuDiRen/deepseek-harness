import pytest
from bigbear_device_record.device.base import (
    DeviceInfo,
    DeviceConnector,
    DeviceConnectionError,
    DeviceCaptureError,
)


def test_device_info_construction():
    info = DeviceInfo(id="dev1", name="My Phone", platform="android", state="device")
    assert info.id == "dev1"
    assert info.name == "My Phone"
    assert info.platform == "android"
    assert info.state == "device"


def test_abstract_cannot_be_instantiated():
    with pytest.raises(TypeError):
        DeviceConnector()


def test_abstract_methods_raise_not_implemented():
    class Stub(DeviceConnector):
        platform = "stub"
    Stub.__abstractmethods__ = frozenset()  # bypass ABC check (Py3.13+ enforces in __new__)
    stub = object.__new__(Stub)
    with pytest.raises(NotImplementedError):
        stub.list_devices()
    with pytest.raises(NotImplementedError):
        stub.connect("dev1")
    with pytest.raises(NotImplementedError):
        stub.capture_screenshot()
    with pytest.raises(NotImplementedError):
        stub.get_ui_hierarchy()
    with pytest.raises(NotImplementedError):
        stub.get_dimensions()


def test_exceptions_are_exceptions():
    assert issubclass(DeviceConnectionError, Exception)
    assert issubclass(DeviceCaptureError, Exception)
