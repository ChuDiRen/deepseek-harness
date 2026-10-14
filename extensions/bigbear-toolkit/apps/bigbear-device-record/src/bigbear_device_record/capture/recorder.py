"""DeviceRecorder 与 SnapshotHandler。
- SnapshotHandler: 接收一次截图请求 → 截图 + UI dump + 存盘 + 可选 vision
- DeviceRecorder:  把 DeviceManager + StreamWorker + SnapshotHandler 组合起来
"""
import asyncio
import base64
import logging
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional

from ..device.base import DeviceConnector
from ..debug import debug, step
from .storage import Storage
from .stream import StreamWorker
from .vision import analyze_screenshot_with_vision

logger = logging.getLogger(__name__)


class SnapshotHandler:
    def __init__(
        self,
        *,
        connector: DeviceConnector,
        storage: Storage,
        platform: str,
        vision_config: Optional[dict] = None,
    ):
        self.connector = connector
        self.storage = storage
        self.platform = platform
        self.vision_config = vision_config

    def capture(self, *, module: str, func: str, desc: str) -> Path:
        # 1. 截图
        png_bytes = self.connector.capture_screenshot()
        step(f"{self.platform} 截图已获取")
        # 2. UI 层次
        try:
            ui_dump = self.connector.get_ui_hierarchy() or ""
        except Exception as e:
            logger.warning("get_ui_hierarchy failed: %s", e)
            ui_dump = ""
        # 3. 维度
        try:
            dims = self.connector.get_dimensions()
        except Exception:
            dims = (0, 0)
        # 4. 存盘
        json_path = self.storage.save_snapshot(
            png_bytes=png_bytes,
            platform=self.platform,
            module=module,
            func=func,
            desc=desc,
            device_dump=ui_dump,
            device_id="",
            device_name="",
            dimensions=dims,
        )
        step(f"{self.platform} UI信息已获取")
        # 5. 可选 vision
        if self.vision_config and self.vision_config.get("api_key"):
            step(f"{self.platform} 视觉AI识别中...")
            try:
                screenshot_name = f"screenshot_{json_path.stem.split('_')[-1]}.png"
                vision_result = analyze_screenshot_with_vision(
                    str(json_path.parent.parent / "img" / screenshot_name),
                    **self.vision_config,
                )
            except Exception as e:
                logger.warning("vision analysis raised: %s", e)
                vision_result = None
            if vision_result:
                debug("vision result keys: %s", list(vision_result.keys()))
                self.storage.update_with_vision(json_path, vision_result)
                step(f"{self.platform} 视觉AI分析完毕")
        return json_path


class DeviceRecorder:
    """组合 DeviceManager + StreamWorker + SnapshotHandler，提供 CLI 一站式调用。"""

    def __init__(
        self,
        *,
        connector: DeviceConnector,
        storage: Storage,
        platform: str,
        fps: int = 2,
        vision_config: Optional[dict] = None,
        on_event: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self.connector = connector
        self.storage = storage
        self.platform = platform
        self.handler = SnapshotHandler(
            connector=connector,
            storage=storage,
            platform=platform,
            vision_config=vision_config,
        )
        self.on_event = on_event or (lambda msg: asyncio.sleep(0))
        self.worker: Optional[StreamWorker] = None
        self.snapshot_count = 0
        self._vision_config = vision_config
        self._fps = fps

    async def start_streaming(self) -> None:
        self.worker = StreamWorker(
            connector=self.connector,
            fps=self._fps,
            on_frame=self._on_frame,
            on_error=self._on_error,
        )
        await self.worker.start()

    async def stop_streaming(self) -> None:
        if self.worker:
            await self.worker.stop()
            self.worker = None

    async def set_mode(self, mode: str) -> None:
        if self.worker:
            await self.worker.set_mode(mode)

    async def set_fps(self, fps: int) -> None:
        self._fps = fps
        if self.worker:
            await self.worker.set_fps(fps)

    async def take_snapshot(self, *, module: str, func: str, desc: str, enable_vision: bool) -> dict:
        # 模块为空时使用默认模块，避免落到批次根目录或空目录
        module = (module or "").strip() or "默认模块"
        # 同步部分跑在线程池
        def _do():
            handler_vision = self._vision_config if enable_vision else None
            handler = SnapshotHandler(
                connector=self.connector,
                storage=self.storage,
                platform=self.platform,
                vision_config=handler_vision,
            )
            json_path = handler.capture(module=module, func=func, desc=desc)
            return json_path
        json_path = await asyncio.to_thread(_do)
        self.snapshot_count += 1
        return {
            "type": "snapshot_done",
            "filename": json_path.name,
            "count": self.snapshot_count,
            "path": str(json_path),
        }

    async def get_state(self) -> dict:
        mode = self.worker.mode if self.worker else "live"
        return {
            "type": "state",
            "mode": mode,
            "fps": self._fps,
            "snapshot_count": self.snapshot_count,
        }

    async def _on_frame(self, payload: dict) -> None:
        await self.on_event(payload)

    async def _on_error(self, payload: dict) -> None:
        await self.on_event(payload)
