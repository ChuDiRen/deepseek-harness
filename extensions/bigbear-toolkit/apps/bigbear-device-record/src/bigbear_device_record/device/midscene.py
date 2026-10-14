"""MidsceneConnector 基类:封装 npx 调用 + 截屏解析 + 维度缓存。"""
import os
import re
import shutil
import subprocess
import sys
from abc import ABC
from io import BytesIO
from pathlib import Path
from typing import Callable, ClassVar, List, Optional, Tuple

from PIL import Image

from .base import (
    DeviceCaptureError,
    DeviceConnectionError,
    DeviceConnector,
    DeviceInfo,
)


class MidsceneError(Exception):
    """npx 子命令失败(非零退出 / 解析失败)。"""


# Runner 类型别名:npx 子进程调用的注入点;测试可传入 fake 避免真跑
RunnerResult = Tuple[int, str, str]  # (rc, stdout, stderr)
Runner = Callable[[List[str], int], RunnerResult]


class NodeNotFoundError(DeviceConnectionError):
    """npx/Node.js 未安装或不在 PATH。"""
    def __init__(self):
        super().__init__(
            "Node.js/npx not found on PATH. "
            "Install Node.js >= 18 from https://nodejs.org"
        )


class MidsceneConnector(DeviceConnector):
    platform: ClassVar[str] = "abstract"
    midscene_pkg: ClassVar[str] = ""
    device_id_arg: ClassVar[str] = "--device-id"
    needs_screen_capture_path: ClassVar[bool] = False

    CONNECT_TIMEOUT = 60
    DISCONNECT_TIMEOUT = 30
    CAPTURE_TIMEOUT = 60
    LIST_DEVICES_TIMEOUT = 15

    _SCREENSHOT_PATH_RE = re.compile(r"Screenshot saved:\s*(\S+)")

    def __init__(self, runner: Optional[Runner] = None):
        self._runner: Runner = runner or self._default_runner
        self._connected_to: Optional[str] = None
        self._last_dim: Optional[Tuple[int, int]] = None

    def is_connected(self) -> bool:
        return self._connected_to is not None

    def list_devices(self) -> List[DeviceInfo]:
        raise NotImplementedError

    def get_ui_hierarchy(self) -> str:
        return ""

    def connect(self, device_id: str) -> None:
        if self._connected_to:
            raise DeviceConnectionError(
                f"already connected to {self._connected_to}"
            )
        args = [self.midscene_pkg, "connect", self.device_id_arg, device_id]
        try:
            self._runner(args, self.CONNECT_TIMEOUT)
        except MidsceneError as e:
            raise DeviceConnectionError(str(e)) from e
        self._connected_to = device_id

    def disconnect(self) -> None:
        if not self._connected_to:
            return
        try:
            self._runner([self.midscene_pkg, "disconnect"],
                         self.DISCONNECT_TIMEOUT)
        except Exception:
            pass  # 静默,清状态
        self._connected_to = None
        self._last_dim = None

    def capture_screenshot(self) -> bytes:
        if not self._connected_to:
            raise DeviceCaptureError("not connected")
        _, stdout, _ = self._runner(
            [self.midscene_pkg, "take_screenshot"], self.CAPTURE_TIMEOUT
        )
        m = self._SCREENSHOT_PATH_RE.search(stdout)
        if not m:
            raise DeviceCaptureError(
                f"could not find screenshot path in midscene output: "
                f"{stdout[:200]}"
            )
        path = m.group(1)
        try:
            with open(path, "rb") as f:
                png = f.read()
            try:
                self._last_dim = Image.open(BytesIO(png)).size
            except Exception:
                pass
            return png
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def get_dimensions(self) -> Tuple[int, int]:
        if self._last_dim:
            return self._last_dim
        # 缓存未命中(刚 connect 还没截图):拍一张空帧
        self.capture_screenshot()
        return self._last_dim or (0, 0)

    def _default_runner(self, args: List[str], timeout: int) -> RunnerResult:
        """默认 runner:用 npx 调包(不是把包名当命令),Windows 走 cmd /c 处理 .cmd/.bat 后缀。

        形参约定:args[0] = midscene 包名(如 "@midscene/computer@1"),
        args[1:] = 子命令及参数。runner 内部组装为:
            npx -y <args[0]> <args[1:]>
        """
        npx = shutil.which("npx")
        if not npx:
            raise NodeNotFoundError()
        npx_path = Path(npx)
        full_args = ["-y", *args]
        if npx_path.suffix.lower() in {".cmd", ".bat"}:
            # Windows: npx 是 .cmd/.bat,需经 cmd /c 走 PATHEXT
            cmd, cmd_args = "cmd", ["/c", npx, *full_args]
        else:
            # Unix 或 npx 是 .exe 链接(WSL 等)
            cmd, cmd_args = npx, full_args
        env = os.environ.copy()
        if self.needs_screen_capture_path:
            capture_dir = Path(os.environ["TEMP"]) / "screenCapture"
            if capture_dir.is_dir():
                env["PATH"] = str(capture_dir) + os.pathsep + env.get("PATH", "")
        try:
            proc = subprocess.run(
                [cmd, *cmd_args], capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout, env=env,
            )
        except FileNotFoundError as e:
            raise NodeNotFoundError() from e
        except subprocess.TimeoutExpired as e:
            raise MidsceneError(f"{args} timed out after {timeout}s") from e
        if proc.returncode != 0:
            raise MidsceneError(
                f"{args} failed (rc={proc.returncode}): {proc.stderr[:500]}"
            )
        return proc.returncode, proc.stdout, proc.stderr


def _normalize_command(command: str, *args: str) -> Tuple[str, List[str]]:
    """非 Windows 直接返回原命令;Windows 下若是绝对路径的 .exe/.bat 直接返回,
    否则解析成 cmd /c <command> [args...] 以借助 PATHEXT 解析 .cmd/.bat。
    """
    if sys.platform != "win32":
        return command, list(args)

    path = Path(command)
    if path.is_absolute():
        if path.suffix.lower() in {".exe", ".bat"}:
            return command, list(args)
        return "cmd", ["/c", command, *args]

    resolved = shutil.which(command)
    if not resolved:
        return "cmd", ["/c", command, *args]
    resolved_path = Path(resolved)
    if resolved_path.suffix.lower() in {".exe", ".bat"}:
        return resolved, list(args)
    return "cmd", ["/c", command, *args]
