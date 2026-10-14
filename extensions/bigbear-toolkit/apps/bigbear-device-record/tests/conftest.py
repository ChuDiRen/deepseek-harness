"""Shared test fixtures and helpers."""
import base64
from pathlib import Path
from typing import List, Tuple
import pytest
from PIL import Image
import io

from bigbear_device_record.device.base import (
    DeviceInfo,
    DeviceConnector,
    DeviceConnectionError,
    DeviceCaptureError,
)


class MockDeviceConnector(DeviceConnector):
    """可注入截图返回值的测试替身。"""

    platform = "mock"

    def __init__(self, fake_png: bytes | None = None):
        self._fake_png = fake_png or self._make_png(640, 480, (200, 100, 50))
        self._connected_to: str | None = None
        self._dimensions: Tuple[int, int] = (640, 480)
        self._ui_hierarchy: str = "<hierarchy/>"
        self.capture_count = 0
        self.fail_next_capture = False

    @staticmethod
    def _make_png(w: int, h: int, color) -> bytes:
        img = Image.new("RGB", (w, h), color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def list_devices(self) -> List[DeviceInfo]:
        return [DeviceInfo(id="mock-1", name="Mock Device", platform="mock", state="device")]

    def connect(self, device_id: str) -> None:
        if device_id not in ("mock-1", "auto"):
            raise DeviceConnectionError(f"unknown device: {device_id}")
        self._connected_to = device_id

    def disconnect(self) -> None:
        self._connected_to = None

    def is_connected(self) -> bool:
        return self._connected_to is not None

    def capture_screenshot(self) -> bytes:
        self.capture_count += 1
        if self.fail_next_capture:
            self.fail_next_capture = False
            raise DeviceCaptureError("simulated capture failure")
        return self._fake_png

    def get_ui_hierarchy(self) -> str:
        return self._ui_hierarchy

    def get_dimensions(self) -> Tuple[int, int]:
        return self._dimensions


@pytest.fixture
def mock_connector() -> MockDeviceConnector:
    return MockDeviceConnector()


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """每个测试一个独立输出目录。"""
    out = tmp_path / "output"
    out.mkdir()
    return out
