"""Device abstraction: base class + dataclasses + exceptions"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple


class DeviceConnectionError(Exception):
    """设备连接失败或掉线"""


class DeviceCaptureError(Exception):
    """截图命令失败"""


@dataclass
class DeviceInfo:
    id: str              # e.g. "emulator-5554" / "iPhone15,2" / Windows 机器名
    name: str            # 人类可读名
    platform: str        # "android" | "ios" | "harmony" | "pc"
    state: str           # "device" | "offline" | "unauthorized"


class DeviceConnector(ABC):
    """所有平台设备的统一抽象。
    PC 端可直接使用 ComputerConnector；
    安卓/iOS/鸿蒙需继承本类并实现真实工具调用。"""

    platform: str = "abstract"

    @abstractmethod
    def list_devices(self) -> List[DeviceInfo]:
        raise NotImplementedError

    @abstractmethod
    def connect(self, device_id: str) -> None:
        """失败抛 DeviceConnectionError"""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def capture_screenshot(self) -> bytes:
        """返回 PNG 字节；失败抛 DeviceCaptureError"""
        raise NotImplementedError

    @abstractmethod
    def get_ui_hierarchy(self) -> str:
        """返回设备 UI 层次文本（占位阶段返回空字符串）。
        返回值直接写入 JSON 的 content 字段。"""
        raise NotImplementedError

    @abstractmethod
    def get_dimensions(self) -> Tuple[int, int]:
        """(width, height)"""
        raise NotImplementedError
