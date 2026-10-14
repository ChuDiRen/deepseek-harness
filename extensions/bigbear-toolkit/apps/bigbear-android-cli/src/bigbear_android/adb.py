# -*- coding: utf-8 -*-
"""ADB device manager - subprocess wrapper for adb commands"""
import io
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import base64
from PIL import Image
from loguru import logger

# 配置日志级别，默认只输出 WARNING 及以上
logger.remove()
logger.add(sys.stderr, level="WARNING", format="{time:HH:mm:ss} | {level} | {message}", colorize=False)


class ADBError(Exception):
    """Base exception for ADB operations"""


class ADBNotFoundError(ADBError):
    """adb executable not found in PATH"""


class DeviceNotFoundError(ADBError):
    """No available adb device"""


class ADBCommandError(ADBError):
    """ADB command returned non-zero exit code"""

    def __init__(self, message: str, returncode: int, stderr: str):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class ADBManager:
    """ADB device manager - singleton mirroring PlaywrightBrowser pattern.

    Encapsulates all adb subprocess calls. Provides:
    - Device enumeration and selection
    - shell command execution
    - exec-out binary output (for screencap)
    - screen size caching
    """

    _instance = None

    def __init__(self):
        self.device_serial: Optional[str] = None  # 当前选中的设备序列号
        self._adb_path: str = self._resolve_adb_path()  # adb 可执行路径
        self._screen_size: Optional[Tuple[int, int]] = None  # (w, h)
        self._connected: bool = False

    @staticmethod
    def _resolve_adb_path() -> str:
        """从环境变量或 PATH 查找 adb 可执行路径"""
        custom = os.getenv("ANDROID_ADB_PATH")
        if custom and Path(custom).is_file():
            return custom
        found = shutil.which("adb")
        if found:
            return found
        raise ADBNotFoundError(
            "adb 未找到。请安装 Android SDK Platform Tools 并确保 'adb' 在 PATH 中，"
            "或通过 ANDROID_ADB_PATH 环境变量指定完整路径。"
        )

    @classmethod
    def get_instance(cls) -> "ADBManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（主要用于测试）"""
        cls._instance = None

    # ---------- 设备列表与选择 ----------

    def list_devices(self) -> List[dict]:
        """执行 `adb devices -l`，返回 [{serial, state, model, usb}, ...]

        返回的设备列表仅包含 state == 'device' 的可用设备。
        """
        result = subprocess.run(
            [self._adb_path, "devices", "-l"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            raise ADBCommandError(
                f"adb devices 失败: {result.stderr.strip()}",
                result.returncode, result.stderr,
            )

        devices: List[dict] = []
        for line in result.stdout.splitlines()[1:]:  # 跳过 "List of devices attached"
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            state = parts[1]
            if state != "device":
                continue
            # 解析 -l 输出中的 model:xxx usb:xxx
            info = {"serial": serial, "state": state, "model": "", "usb": ""}
            for token in parts[2:]:
                if token.startswith("model:"):
                    info["model"] = token[len("model:"):]
                elif token.startswith("usb:"):
                    info["usb"] = token[len("usb:"):]
            devices.append(info)
        return devices

    def select_device(self, serial: Optional[str] = None) -> str:
        """选择设备：serial 指定 → 否则首个 device → 否则抛 DeviceNotFoundError。

        Returns:
            选中的设备序列号
        """
        if not serial:
            serial = os.getenv("ANDROID_DEFAULT_DEVICE")
        if serial:
            self.device_serial = serial
            self._connected = True
            return serial

        devices = self.list_devices()
        if not devices:
            raise DeviceNotFoundError(
                "未检测到任何 adb 设备。请确认：\n"
                "  1. USB 调试已开启\n"
                "  2. 设备已授权（首次连接需在手机上点击'允许 USB 调试'）\n"
                "  3. adb devices 能看到设备"
            )
        self.device_serial = devices[0]["serial"]
        self._connected = True
        return self.device_serial

    # ---------- 命令执行 ----------

    def _adb_cmd(self, *args: str, with_serial: bool = True) -> List[str]:
        """构造 adb 命令行"""
        cmd = [self._adb_path]
        if with_serial and self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        return cmd

    def shell(self, *args: str, timeout: int = 30) -> Tuple[int, str, str]:
        """执行 `adb [-s serial] shell <args>`，返回 (returncode, stdout, stderr)

        Args:
            *args: 要在 shell 中执行的命令及参数
            timeout: 超时秒数
        """
        if not self._connected or not self.device_serial:
            self.select_device()

        cmd = self._adb_cmd("shell", *args)
        logger.debug("adb shell: {}", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            raise ADBCommandError(f"adb shell 超时 ({timeout}s)", -1, str(e))

    def exec_out(self, *args: str, timeout: int = 30) -> bytes:
        """执行 `adb [-s serial] exec-out <args>`，返回原始字节流

        适用于 screencap -p 等二进制输出命令。注意 exec-out 不会自动加换行符。
        """
        if not self._connected or not self.device_serial:
            self.select_device()

        cmd = self._adb_cmd("exec-out", *args)
        logger.debug("adb exec-out: {}", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=timeout,
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
                raise ADBCommandError(
                    f"adb exec-out 失败: {stderr.strip()}",
                    result.returncode, stderr,
                )
            return result.stdout
        except subprocess.TimeoutExpired as e:
            raise ADBCommandError(f"adb exec-out 超时 ({timeout}s)", -1, str(e))

    def adb_no_shell(self, *args: str, timeout: int = 30) -> Tuple[int, str, str]:
        """执行不带 shell 子命令的 adb 命令（如 adb push/pull/install）

        Returns:
            (returncode, stdout, stderr)
        """
        if not self._connected or not self.device_serial:
            self.select_device()

        cmd = self._adb_cmd(*args)
        logger.debug("adb: {}", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            raise ADBCommandError(f"adb 命令超时 ({timeout}s)", -1, str(e))

    # ---------- 屏幕操作 ----------

    def get_screen_size(self, refresh: bool = False) -> Tuple[int, int]:
        """通过 `adb shell wm size` 获取屏幕分辨率，缓存。

        Returns:
            (width, height)
        """
        if self._screen_size is not None and not refresh:
            return self._screen_size

        rc, stdout, stderr = self.shell("wm", "size")
        if rc != 0:
            raise ADBCommandError(
                f"获取屏幕尺寸失败: {stderr.strip()}",
                rc, stderr,
            )
        # 输出示例: "Physical size: 1080x1920"
        match = re.search(r"(\d+)\s*x\s*(\d+)", stdout)
        if not match:
            raise ADBCommandError(
                f"无法解析屏幕尺寸: {stdout!r}",
                rc, stdout,
            )
        self._screen_size = (int(match.group(1)), int(match.group(2)))
        return self._screen_size

    def screencap_base64(self, use_jpeg: bool = True, quality: int = 85,
                         max_retries: int = 2) -> Tuple[str, Image.Image]:
        """截屏，返回 (base64, PIL.Image)

        Args:
            use_jpeg: 是否压缩为 JPEG（默认 True，更快）
            quality: JPEG 质量 1-100
            max_retries: 失败重试次数

        Returns:
            (base64 字符串, PIL.Image 对象)
        """
        last_err: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                png_bytes = self.exec_out("screencap", "-p", timeout=30)
                if not png_bytes:
                    raise ADBCommandError("screencap 返回空字节流", 0, "")

                img = Image.open(io.BytesIO(png_bytes))
                if use_jpeg:
                    # JPEG 不支持 RGBA，统一转 RGB
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=quality, optimize=True)
                    img_base64 = base64.b64encode(buf.getvalue()).decode("ascii")
                else:
                    img_base64 = base64.b64encode(png_bytes).decode("ascii")
                return img_base64, img
            except Exception as e:
                last_err = e
                logger.warning("screencap 第 {} 次失败: {}", attempt + 1, e)
                if attempt < max_retries:
                    time.sleep(0.5)
        raise ADBCommandError(
            f"截图失败（已重试 {max_retries} 次）: {last_err}",
            -1, str(last_err) if last_err else "",
        )

    def shell_input(self, *args: str) -> None:
        """执行 `adb shell input <args>`，封装点击/滑动/按键/文本

        例:
            shell_input("tap", "100", "200")
            shell_input("swipe", "100", "200", "300", "400", "500")
            shell_input("keyevent", "4")
            shell_input("text", "hello")
            shell_input("keyevent", "67", "67", "67")  # 一次调用发多次 DEL
        """
        rc, stdout, stderr = self.shell("input", *args)
        if rc != 0:
            raise ADBCommandError(
                f"adb input 失败: {stderr.strip() or stdout.strip()}",
                rc, stderr,
            )

    # ---------- IME / 应用管理 / 广播 ----------

    def is_installed(self, package: str) -> bool:
        """检测设备是否已安装指定包

        Args:
            package: 包名，如 ``com.android.adbkeyboard``

        Returns:
            是否已安装
        """
        rc, stdout, _ = self.shell("pm", "list", "packages", package)
        if rc != 0:
            return False
        # 输出示例: "package:com.android.adbkeyboard"
        return f"package:{package}" in stdout

    def install_apk(self, local_path: str, reinstall: bool = True, timeout: int = 120) -> None:
        """通过 adb install 安装本地 APK 到设备

        Args:
            local_path: 本地 APK 文件路径
            reinstall: 是否覆盖安装（-r），默认 True
            timeout: 超时秒数，默认 120（首次安装大 APK 或新设备初始化可能很慢）
        """
        args = ["install"]
        if reinstall:
            args.append("-r")
        args.append(local_path)
        rc, stdout, stderr = self.adb_no_shell(*args, timeout=timeout)
        if rc != 0 or "Failure" in stdout or "Failure" in stderr:
            raise ADBCommandError(
                f"安装 APK 失败: {stdout.strip()} / {stderr.strip()}",
                rc, stderr,
            )
        logger.debug("APK 安装完成: {}", local_path)

    def get_current_ime(self) -> str:
        """获取设备当前激活的输入法 ID

        Returns:
            IME ID，如 ``com.baidu.input_vivo/.ImeVivoService``，失败时返回空串
        """
        rc, stdout, _ = self.shell("settings", "get", "secure", "default_input_method")
        if rc != 0:
            return ""
        return stdout.strip()

    def enable_ime(self, ime_id: str) -> None:
        """启用一个已安装但未启用的 IME（注册为可用，但不激活）

        必须在 set_ime 之前调用，否则 set_ime 会报
        ``Unknown input method <id> cannot be selected``。
        """
        rc, stdout, stderr = self.shell("ime", "enable", ime_id)
        if rc != 0:
            raise ADBCommandError(
                f"启用 IME 失败 [{ime_id}]: {stderr.strip() or stdout.strip()}",
                rc, stderr,
            )
        logger.debug("已启用 IME: {}", ime_id)

    def set_ime(self, ime_id: str) -> None:
        """切换设备激活输入法

        Args:
            ime_id: 完整 IME ID，如 ``com.android.adbkeyboard/.AdbIME``

        Note:
            如果 IME 刚安装未启用，请先调用 :meth:`enable_ime`。
        """
        rc, stdout, stderr = self.shell("ime", "set", ime_id)
        if rc != 0:
            raise ADBCommandError(
                f"切换 IME 失败 [{ime_id}]: {stderr.strip() or stdout.strip()}",
                rc, stderr,
            )
        logger.debug("已切换 IME: {}", ime_id)

    def broadcast(self, action: str, **extras: str) -> Tuple[int, str, str]:
        """发送广播，支持字符串 extras

        Args:
            action: Intent action，如 ``ADB_INPUT_TEXT``
            **extras: 字符串型 extras，键值对

        Returns:
            (returncode, stdout, stderr)
        """
        args = ["am", "broadcast", "-a", action]
        for key, value in extras.items():
            args.extend(["--es", key, value])
        return self.shell(*args)

    # ---------- UI 层次与应用 ----------

    def dump_ui(self, output_path: str) -> str:
        """执行 `adb shell uiautomator dump`，将 XML 保存到本地路径

        Returns:
            设备端生成的 XML 文件路径（通常在 /sdcard/window_dump.xml）
        """
        device_path = "/sdcard/window_dump.xml"
        rc, stdout, stderr = self.shell("uiautomator", "dump", device_path)
        if rc != 0:
            raise ADBCommandError(
                f"uiautomator dump 失败: {stderr.strip()}",
                rc, stderr,
            )
        # 拉取到本地
        rc, _, stderr = self.adb_no_shell("pull", device_path, output_path)
        if rc != 0:
            raise ADBCommandError(
                f"adb pull 失败: {stderr.strip()}",
                rc, stderr,
            )
        return output_path

    def appinfo(self, package: str) -> str:
        """执行 `adb shell dumpsys package <pkg>`，返回完整输出"""
        rc, stdout, stderr = self.shell("dumpsys", "package", package)
        if rc != 0:
            raise ADBCommandError(
                f"dumpsys package {package} 失败: {stderr.strip()}",
                rc, stderr,
            )
        return stdout

    # 当前前台包名 / Activity（mResumedActivity / mFocusedApp）解析
    _RE_RESUMED = re.compile(
        r"mResumedActivity:\s*Activity\{[^\}]+\s+(?P<comp>[^\s/]+)/(?P<act>[^\s\}]+)"
    )
    _RE_FOCUSED = re.compile(
        r"mFocusedApp\s*=\s*ActivityRecord\{[^\}]+\s+(?P<comp>[^\s/]+)/(?P<act>[^\s\}]+)"
    )

    def get_current_app(self) -> dict:
        """返回当前前台应用的 ``{"package": str, "activity": str}``。

        优先解析 ``dumpsys activity activities`` 中的 ``mResumedActivity``；
        兜底解析 ``dumpsys window`` 中的 ``mFocusedApp``。两者任一成功即返回。
        均失败时返回空字段。
        """
        package = ""
        activity = ""

        try:
            rc, stdout, _ = self.shell("dumpsys", "activity", "activities")
            if rc == 0 and stdout:
                m = self._RE_RESUMED.search(stdout)
                if m:
                    package = m.group("comp")
                    activity = m.group("act")
        except Exception:
            pass

        if not package:
            try:
                rc, stdout, _ = self.shell("dumpsys", "window")
                if rc == 0 and stdout:
                    m = self._RE_FOCUSED.search(stdout)
                    if m:
                        package = m.group("comp")
                        activity = m.group("act")
            except Exception:
                pass

        return {"package": package, "activity": activity}

    # ---------- 生命周期 ----------

    def is_connected(self) -> bool:
        """检查当前选中的设备是否在线"""
        if not self.device_serial:
            return False
        try:
            rc, stdout, _ = self.shell("get-state")
            return rc == 0 and stdout.strip() == "device"
        except Exception:
            return False

    def close(self) -> None:
        """ADB 无需关闭连接，此处仅清空状态"""
        self._connected = False
        self.device_serial = None
        self._screen_size = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# =============================================================================
# 模块级便捷函数（无 AI 的原始 adb 操作）
# =============================================================================

def tap(serial: Optional[str], x: int, y: int) -> None:
    """在 (x, y) 坐标处点击（无 AI）

    封装 `adb shell input tap`。当 ``serial`` 为空时使用默认设备。

    Args:
        serial: 设备序列号（adb -s 参数），None 时使用默认设备
        x: 屏幕 X 坐标
        y: 屏幕 Y 坐标
    """
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += ["shell", "input", "tap", str(x), str(y)]
    result = subprocess.run(cmd, capture_output=True, timeout=10)
    if result.returncode != 0:
        raise ADBCommandError(
            f"adb input tap 失败: {result.stderr.decode(errors='replace')[:300]}",
            result.returncode, result.stderr.decode(errors='replace'),
        )
    print(f"[OK] tapped at ({x}, {y}) on {serial or 'default device'}")