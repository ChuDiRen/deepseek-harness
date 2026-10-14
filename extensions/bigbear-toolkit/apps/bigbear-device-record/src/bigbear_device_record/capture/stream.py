"""StreamWorker: 在独立 asyncio 任务中持续 capture_screenshot() → base64 → 推帧。
mode="live" 时按 FPS 推帧；mode="snapshot" 时停推。
当上一帧 capture 未完成时,本帧直接丢弃(自然降频),不排队。
"""
import asyncio
import base64
import time
from typing import Awaitable, Callable, Optional

from ..device.base import DeviceConnector


FrameCallback = Callable[[dict], Awaitable[None]]


class StreamWorker:
    def __init__(
        self,
        *,
        connector: DeviceConnector,
        fps: int = 2,
        on_frame: FrameCallback,
        on_error: Optional[FrameCallback] = None,
    ):
        self.connector = connector
        self.fps = max(1, min(60, fps))
        self.on_frame = on_frame
        self.on_error = on_error
        self.mode = "live"
        self._task: Optional[asyncio.Task] = None
        self._stop = False
        self._seq = 0
        self._consecutive_errors = 0
        self._MAX_CONSECUTIVE_ERRORS = 3
        self._in_flight = False  # 防止 capture 慢时排队

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop = False
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None

    async def set_mode(self, mode: str) -> None:
        if mode not in ("live", "snapshot"):
            raise ValueError(f"invalid mode: {mode}")
        self.mode = mode
        self._consecutive_errors = 0  # reset on mode change

    async def set_fps(self, fps: int) -> None:
        self.fps = max(1, min(60, fps))

    async def _loop(self) -> None:
        interval = 1.0 / self.fps
        while not self._stop:
            if self.mode == "live":
                if self._in_flight:
                    # 上一帧还在跑,本帧直接丢弃,等下一拍
                    await asyncio.sleep(interval)
                    continue
                self._in_flight = True
                try:
                    await self._emit_frame()
                finally:
                    self._in_flight = False
            await asyncio.sleep(interval)

    async def _emit_frame(self) -> None:
        try:
            png_bytes = await asyncio.to_thread(self.connector.capture_screenshot)
            self._consecutive_errors = 0
            self._seq += 1
            frame_b64 = base64.b64encode(png_bytes).decode("ascii")
            await self.on_frame({
                "type": "frame",
                "data": frame_b64,
                "seq": self._seq,
                "timestamp": time.time(),
            })
        except Exception as e:
            self._consecutive_errors += 1
            if self.on_error:
                await self.on_error({
                    "type": "error",
                    "message": f"capture failed: {e}",
                })
            if self._consecutive_errors >= self._MAX_CONSECUTIVE_ERRORS:
                # 切到按需模式避免刷屏
                self.mode = "snapshot"
                if self.on_error:
                    await self.on_error({
                        "type": "error",
                        "message": f"连续 {self._consecutive_errors} 次截图失败，已切换到按需模式",
                    })
                self._consecutive_errors = 0
