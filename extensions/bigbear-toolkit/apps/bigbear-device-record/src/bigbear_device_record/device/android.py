"""Android connector:经由 @midscene/android@1 调 npx 截屏,list 走 adb。"""
from typing import List

from .base import DeviceInfo
from .midscene import MidsceneConnector
from . import native


class AndroidConnector(MidsceneConnector):
    platform = "android"
    midscene_pkg = "@midscene/android@1"
    device_id_arg = "--deviceId"  # midscene-android 是 camelCase

    def list_devices(self) -> List[DeviceInfo]:
        return native.list_adb_devices()
