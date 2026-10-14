"""iOS connector:经由 @midscene/ios@1 调 npx 截屏,list 走 xcrun simctl。"""
from typing import List

from .base import DeviceInfo
from .midscene import MidsceneConnector
from . import native


class IOSConnector(MidsceneConnector):
    platform = "ios"
    midscene_pkg = "@midscene/ios@1"

    def list_devices(self) -> List[DeviceInfo]:
        return native.list_xcrun_devices()
