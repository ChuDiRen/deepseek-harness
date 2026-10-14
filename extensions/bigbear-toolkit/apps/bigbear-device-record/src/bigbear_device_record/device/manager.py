"""DeviceManager: 根据 --platform 选择并实例化对应 connector。"""
from typing import Optional

from .base import DeviceInfo, DeviceConnector
from .pc import ComputerConnector
from .android import AndroidConnector
from .ios import IOSConnector
from .harmony import HarmonyConnector


PLATFORM_MAP = {
    "pc": ComputerConnector,
    "android": AndroidConnector,
    "ios": IOSConnector,
    "harmony": HarmonyConnector,
}


class DeviceManager:
    def __init__(self, platform: str, device_id: Optional[str] = None):
        if platform not in PLATFORM_MAP:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported: {sorted(PLATFORM_MAP.keys())}"
            )
        self.platform = platform
        self.device_id = device_id
        self.connector: DeviceConnector = PLATFORM_MAP[platform]()

    def list_devices(self) -> list[DeviceInfo]:
        return self.connector.list_devices()

    def connect(self) -> DeviceInfo:
        """连接设备：device_id 为 None 时取 list_devices() 第一个。"""
        devices = self.connector.list_devices()
        if not devices:
            from .base import DeviceConnectionError
            raise DeviceConnectionError(f"No {self.platform} devices found")
        target_id = self.device_id or devices[0].id
        self.connector.connect(target_id)
        self.device_id = target_id
        # 返回已连接的 DeviceInfo
        return next(d for d in devices if d.id == target_id)

    def disconnect(self) -> None:
        self.connector.disconnect()
