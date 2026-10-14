"""HarmonyOS connector:经由 @midscene/harmony@1 调 npx 截屏,list 走 hdc。"""
from typing import List

from .base import DeviceInfo
from .midscene import MidsceneConnector
from . import native


class HarmonyConnector(MidsceneConnector):
    platform = "harmony"
    midscene_pkg = "@midscene/harmony@1"

    def list_devices(self) -> List[DeviceInfo]:
        return native.list_hdc_targets()
