# -*- coding: utf-8 -*-
"""Android device actions via adb shell input"""
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

from .adb import ADBManager


class ClipboardNotSupported(Exception):
    """设备 ``cmd clipboard`` 不可用（vivo/ColorOS/HyperOS 等定制 ROM 常见）。

    调用方应捕获此异常并回退到 ADBKeyboard 等方案。
    """


# Android 按键码常用别名（参考 https://developer.android.com/reference/android/view/KeyEvent）
KEYCODES = {
    # 导航
    "back": 4,
    "home": 3,
    "menu": 82,
    "recents": 187,        # 最近任务 / 应用切换
    "app_switch": 187,    # 同上（标准名）
    "recent": 187,
    "overview": 187,
    "notifications": 83,  # 下拉通知栏
    "quick_settings": 224,
    # 文本编辑
    "enter": 66,
    "delete": 67,
    "backspace": 67,
    "tab": 61,
    "space": 62,
    "esc": 111,
    # 系统
    "power": 26,
    "volume_up": 24,
    "volume_down": 25,
    "wakeup": 224,
    "wake": 224,
    "sleep": 223,
    "camera": 27,
    # 剪贴板
    "paste": 279,
    "copy": 278,
    "cut": 277,
    "select_all": 277,  # Ctrl+A 等价
    # 方向
    "up": 19,
    "down": 20,
    "left": 21,
    "right": 22,
    # 浏览器/媒体
    "refresh": 231,
    "forward": 125,
    "search": 84,
}


class AndroidActions:
    """Android device actions via adb shell input.

    所有操作通过 adb shell input 实现，封装为原子操作供 CLI/AI 调用。
    """

    def __init__(self, adb: ADBManager):
        """
        Args:
            adb: ADBManager 实例
        """
        self.adb = adb

    # ---------- 点击 ----------

    def tap(self, x: float, y: float):
        """点击指定坐标

        Args:
            x: X 坐标
            y: Y 坐标
        """
        self.adb.shell_input("tap", str(int(x)), str(int(y)))

    def click_at(self, x: float, y: float):
        """点击指定坐标（click_at 别名，与 bigbear-web-cli 接口对齐）"""
        self.tap(x, y)

    def double_tap(self, x: float, y: float):
        """双击坐标"""
        self.tap(x, y)
        time.sleep(0.1)
        self.tap(x, y)

    def long_press(self, x: float, y: float, duration_ms: int = 1000):
        """长按坐标（通过 swipe 同坐标实现）

        Args:
            x, y: 坐标
            duration_ms: 按住时长（毫秒），默认 1000
        """
        self.adb.shell_input(
            "swipe", str(int(x)), str(int(y)), str(int(x)), str(int(y)), str(duration_ms),
        )

    # ---------- 滑动 ----------

    def swipe(self, start_x: float, start_y: float, end_x: float, end_y: float,
              duration_ms: int = 500):
        """从起点滑动到终点

        Args:
            start_x, start_y: 起点坐标
            end_x, end_y: 终点坐标
            duration_ms: 滑动时长（毫秒）
        """
        self.adb.shell_input(
            "swipe",
            str(int(start_x)), str(int(start_y)),
            str(int(end_x)), str(int(end_y)),
            str(duration_ms),
        )

    def swipe_up(self, count: int = 1, distance: float = 0.6, duration_ms: int = 500):
        """整屏向上滑动（手指从下往上划），content 向下滚动

        Args:
            count: 滑动次数
            distance: 滑动距离比例 0.1~1.0
            duration_ms: 单次滑动时长
        """
        w, h = self.adb.get_screen_size()
        start_x = w // 2
        start_y = int(h * (1 - distance) / 2 + h * distance)
        end_x = w // 2
        end_y = int(h * (1 - distance) / 2)
        for _ in range(count):
            self.swipe(start_x, start_y, end_x, end_y, duration_ms)
            time.sleep(0.2)

    def swipe_down(self, count: int = 1, distance: float = 0.6, duration_ms: int = 500):
        """整屏向下滑动（手指从上往下划），content 向上滚动"""
        w, h = self.adb.get_screen_size()
        start_x = w // 2
        start_y = int(h * (1 - distance) / 2)
        end_x = w // 2
        end_y = int(h * (1 - distance) / 2 + h * distance)
        for _ in range(count):
            self.swipe(start_x, start_y, end_x, end_y, duration_ms)
            time.sleep(0.2)

    def swipe_left(self, count: int = 1, distance: float = 0.6, duration_ms: int = 500):
        """整屏向左滑动（手指从右往左划）"""
        w, h = self.adb.get_screen_size()
        start_x = int(w * (1 - distance) / 2 + w * distance)
        start_y = h // 2
        end_x = int(w * (1 - distance) / 2)
        end_y = h // 2
        for _ in range(count):
            self.swipe(start_x, start_y, end_x, end_y, duration_ms)
            time.sleep(0.2)

    def swipe_right(self, count: int = 1, distance: float = 0.6, duration_ms: int = 500):
        """整屏向右滑动（手指从左往右划）"""
        w, h = self.adb.get_screen_size()
        start_x = int(w * (1 - distance) / 2)
        start_y = h // 2
        end_x = int(w * (1 - distance) / 2 + w * distance)
        end_y = h // 2
        for _ in range(count):
            self.swipe(start_x, start_y, end_x, end_y, duration_ms)
            time.sleep(0.2)

    def swipe_in_region(self, region: Tuple[int, int, int, int],
                        direction: str, distance: float = 0.6, duration_ms: int = 500):
        """在指定区域内按方向和距离比例滑动

        Args:
            region: (x1, y1, x2, y2) 区域坐标
            direction: up/down/left/right
            distance: 滑动距离比例 0.1~1.0
            duration_ms: 滑动时长
        """
        x1, y1, x2, y2 = region
        width = x2 - x1
        height = y2 - y1

        if direction == "down":
            start_x = x1 + width // 2
            start_y = y1 + int(height * (1 - distance) / 2)
            end_x = start_x
            end_y = y1 + int(height * (1 - distance) / 2 + height * distance)
        elif direction == "up":
            start_x = x1 + width // 2
            start_y = y1 + int(height * (1 - distance) / 2 + height * distance)
            end_x = start_x
            end_y = y1 + int(height * (1 - distance) / 2)
        elif direction == "left":
            start_x = x1 + int(width * (1 - distance) / 2 + width * distance)
            start_y = y1 + height // 2
            end_x = x1 + int(width * (1 - distance) / 2)
            end_y = start_y
        elif direction == "right":
            start_x = x1 + int(width * (1 - distance) / 2)
            start_y = y1 + height // 2
            end_x = x1 + int(width * (1 - distance) / 2 + width * distance)
            end_y = start_y
        else:
            raise ValueError(f"无效方向: {direction}（应为 up/down/left/right）")

        self.swipe(start_x, start_y, end_x, end_y, duration_ms)

    # ---------- 双指缩放（pinch / zoom）----------

    # 屏幕短边的 15% 作为偏移基准
    _PINCH_OFFSET_RATIO = 0.15

    def pinch(self, x: float, y: float, scale: float = 0.5, duration_ms: int = 500):
        """双指向内捏合（缩小）

        通过并行执行两个 `adb shell input swipe` 实现：
        手指 1 从 (x - offset_start, y) 滑向 (x - offset_end, y)
        手指 2 从 (x + offset_start, y) 滑向 (x + offset_end, y)
        offset_start > offset_end，两指从外往内靠拢。

        Args:
            x: 中心点 X
            y: 中心点 Y
            scale: 缩放比例 0.1~1.0，0.5 表示缩小到一半（默认 0.5）
            duration_ms: 单指滑动时长（毫秒）
        """
        w, h = self.adb.get_screen_size()
        base = int(min(w, h) * self._PINCH_OFFSET_RATIO)

        # 起点距中心远（base），终点距中心近（base * scale）
        offset_start = base
        offset_end = max(int(base * scale), 10)  # 最小 10 像素

        # 两指从外往内
        finger1_start = (int(x - offset_start), int(y))
        finger1_end = (int(x - offset_end), int(y))
        finger2_start = (int(x + offset_start), int(y))
        finger2_end = (int(x + offset_end), int(y))

        self._parallel_swipe(finger1_start, finger1_end, finger2_start, finger2_end, duration_ms)

    def zoom(self, x: float, y: float, scale: float = 2.0, duration_ms: int = 500):
        """双指向外张开（放大）

        通过并行执行两个 `adb shell input swipe` 实现：
        手指 1 从 (x - offset_end, y) 滑向 (x - offset_start, y)
        手指 2 从 (x + offset_end, y) 滑向 (x + offset_start, y)
        offset_start > offset_end，两指从内往外张开。

        Args:
            x: 中心点 X
            y: 中心点 Y
            scale: 缩放比例 1.0~5.0，2.0 表示放大到 2 倍（默认 2.0）
            duration_ms: 单指滑动时长（毫秒）
        """
        w, h = self.adb.get_screen_size()
        base = int(min(w, h) * self._PINCH_OFFSET_RATIO)

        # 起点距中心近（base），终点距中心远（base * scale）
        offset_end = base
        offset_start = int(base * scale)

        # 两指从内往外
        finger1_start = (int(x - offset_end), int(y))
        finger1_end = (int(x - offset_start), int(y))
        finger2_start = (int(x + offset_end), int(y))
        finger2_end = (int(x + offset_start), int(y))

        self._parallel_swipe(finger1_start, finger1_end, finger2_start, finger2_end, duration_ms)

    def _parallel_swipe(self, f1_start, f1_end, f2_start, f2_end, duration_ms: int):
        """并行执行两个 adb shell input swipe（模拟双指）

        使用 threading 同时启动两个 subprocess，使两个 swipe 在时间上重叠。
        Android 系统会将其识别为双指手势。
        """
        def run_swipe(start, end):
            try:
                self.adb.shell_input(
                    "swipe",
                    str(start[0]), str(start[1]),
                    str(end[0]), str(end[1]),
                    str(duration_ms),
                )
            except Exception as e:
                logger.warning("并行 swipe 失败: {}", e)

        t1 = threading.Thread(target=run_swipe, args=(f1_start, f1_end))
        t2 = threading.Thread(target=run_swipe, args=(f2_start, f2_end))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    # ---------- 输入 ----------

    def input_text(self, x: float, y: float, text: str):
        """点击坐标后输入文本

        - 英文/数字/常见符号：使用 ``adb shell input text``
        - 中文/特殊字符：先尝试剪贴板 + PASTE（Android 10+），失败时自动回退
          到 ADBKeyboard（需联网首次下载 APK，缓存在 ``~/.cache/bigbear-android-cli``）

        Args:
            x, y: 点击坐标
            text: 要输入的文本
        """
        # 先点击获取焦点
        self.tap(x, y)
        time.sleep(0.3)

        if self._has_non_ascii(text):
            # 中文路径：先尝试剪贴板，失败回退到 ADBKeyboard
            try:
                self._input_via_clipboard(text)
            except ClipboardNotSupported as e:
                logger.info("剪贴板方案不可用，回退到 ADBKeyboard: {}", e)
                self._input_via_adbkeyboard(text)
        else:
            # 直接 input text（转义 shell 特殊字符，%s 表示空格）
            escaped = text.replace(" ", "%s")
            self.adb.shell_input("text", escaped)
            time.sleep(0.2)

    def _has_non_ascii(self, text: str) -> bool:
        """检测是否包含中文/emoji 等非 ASCII 字符"""
        return bool(re.search(r"[^\x00-\x7F]", text))

    # ---------- 中文输入：剪贴板方案 ----------

    # 清空输入框时一次批量发的 DEL 次数。50 是为兼容"残留多字符"场景；
    # 一次 adb 调用比 50 次循环快 ~50 倍（实测 0.1s vs 5s+）。
    _BATCH_DEL_COUNT = 50

    def _input_via_clipboard(self, text: str):
        """通过剪贴板 + PASTE 输入文本

        流程：
        1. MOVE_END + 批量 DEL 清空输入框（一次 shell 调用发 50 次 DEL）
        2. ``cmd clipboard set-primary-clip`` 设置剪贴板
        3. ``cmd clipboard get-primary-clip`` 读回校验（防止 rc=0 但设备端失败）
        4. KEYCODE_PASTE 触发粘贴

        Raises:
            ClipboardNotSupported: 设备不支持 ``cmd clipboard``（vivo/ColorOS/HyperOS
                等定制 ROM 常见），调用方应回退到 ADBKeyboard。
        """
        # 1) 清空：一次 shell 调用发 50 次 DEL（API 30+ 支持 keyevent 多参数）
        self.adb.shell_input("keyevent", "123")  # MOVE_END
        time.sleep(0.05)
        del_codes = " ".join(["67"] * self._BATCH_DEL_COUNT)
        self.adb.shell_input("keyevent", *del_codes.split())
        time.sleep(0.1)

        # 2) 设置剪贴板
        rc, _, stderr = self.adb.shell(
            "cmd", "clipboard", "set-primary-clip", "--user", "0", text,
        )
        # adb shell 的 rc 不可靠，必须检查 stderr 实际内容
        stderr_text = stderr.strip()
        if rc != 0 or "No shell command" in stderr_text or "Exception" in stderr_text:
            raise ClipboardNotSupported(
                f"[{self.adb.device_serial}] cmd clipboard 不可用 "
                f"(rc={rc}, stderr='{stderr_text}')。"
                f"常见于 vivo/ColorOS/HyperOS 等定制 ROM。"
            )

        # 3) 读回校验 —— 这是关键：vivo 上 set 返回 rc=0 但实际失败
        rc2, stdout, stderr2 = self.adb.shell(
            "cmd", "clipboard", "get-primary-clip", "--user", "0",
        )
        if rc2 != 0 or stdout.strip() != text:
            raise ClipboardNotSupported(
                f"[{self.adb.device_serial}] 剪贴板读回校验失败："
                f"rc={rc2}, expected='{text}', got='{stdout.strip()}'"
            )

        # 4) 触发粘贴
        time.sleep(0.1)
        self.adb.shell_input("keyevent", "279")  # KEYCODE_PASTE
        time.sleep(0.3)

    # ---------- 中文输入：ADBKeyboard 回退方案 ----------

    _ADBKEYBOARD_PKG = "com.android.adbkeyboard"
    _ADBKEYBOARD_IME = "com.android.adbkeyboard/.AdbIME"
    _ADBKEYBOARD_URL = "https://github.com/senzhk/ADBKeyBoard/raw/master/ADBKeyboard.apk"
    _ADBKEYBOARD_BROADCAST = "ADB_INPUT_TEXT"

    def _input_via_adbkeyboard(self, text: str):
        """通过 ADBKeyboard 广播接口输入文本

        流程：
        1. 检查设备是否已安装 ADBKeyboard；未安装则下载并安装
        2. 保存当前 IME
        3. 切换到 ADBKeyboard
        4. 发送广播 ``am broadcast -a ADB_INPUT_TEXT --es msg <text>``
        5. 恢复原 IME（无论成败）

        ADBKeyboard 来源：senzhk/ADBKeyBoard（GPL-2.0），首次使用时联网下载，
        缓存到 ``~/.cache/bigbear-android-cli/ADBKeyboard.apk``。
        """
        # 1) 检测/安装
        if not self.adb.is_installed(self._ADBKEYBOARD_PKG):
            apk_path = self._download_adbkeyboard_apk()
            self.adb.install_apk(apk_path)
            # 等待系统注册新 IME
            time.sleep(1)

        # 2) 保存原 IME
        prev_ime = self.adb.get_current_ime()

        # 3) 启用 ADBKeyboard（安装后必须先 enable 才能 set）
        try:
            self.adb.enable_ime(self._ADBKEYBOARD_IME)
        except Exception as e:
            logger.debug("enable_ime 失败（可能已启用）: {}", e)

        # 4) 切换到 ADBKeyboard 并发送文本
        try:
            self.adb.set_ime(self._ADBKEYBOARD_IME)
            time.sleep(0.3)
            rc, stdout, stderr = self.adb.broadcast(
                self._ADBKEYBOARD_BROADCAST, msg=text,
            )
            # am broadcast 总是 rc=0，需检查 stdout 的 result=
            if rc != 0 or "result=0" not in stdout:
                raise RuntimeError(
                    f"ADBKeyboard 广播失败: stdout='{stdout.strip()}', "
                    f"stderr='{stderr.strip()}'"
                )
            time.sleep(0.3)
        finally:
            # 5) 恢复原 IME（无论成败）
            if prev_ime and prev_ime != self._ADBKEYBOARD_IME:
                try:
                    self.adb.set_ime(prev_ime)
                except Exception as e:
                    logger.warning("恢复原 IME 失败 [{}]: {}", prev_ime, e)

    def _download_adbkeyboard_apk(self) -> str:
        """下载 ADBKeyboard.apk 到本地缓存，返回本地路径

        缓存目录：``~/.cache/bigbear-android-cli/ADBKeyboard.apk``
        """
        cache_dir = Path.home() / ".cache" / "bigbear-android-cli"
        cache_dir.mkdir(parents=True, exist_ok=True)
        apk_path = cache_dir / "ADBKeyboard.apk"

        if apk_path.exists() and apk_path.stat().st_size > 1000:
            return str(apk_path)

        logger.info("正在下载 ADBKeyboard: {}", self._ADBKEYBOARD_URL)
        try:
            urllib.request.urlretrieve(self._ADBKEYBOARD_URL, apk_path)
        except Exception as e:
            raise RuntimeError(
                f"下载 ADBKeyboard 失败: {e}。"
                f"如网络受限，可手动从 {self._ADBKEYBOARD_URL} 下载并放到 {apk_path}。"
            )

        size = apk_path.stat().st_size
        if size < 1000:
            raise RuntimeError(f"下载的 ADBKeyboard 文件异常（仅 {size} 字节）: {apk_path}")
        logger.info("ADBKeyboard 已下载: {} ({} bytes)", apk_path, size)
        return str(apk_path)

    # ---------- 按键 ----------

    def keyevent(self, code: int):
        """发送按键事件

        Args:
            code: 按键码（数字或 KEYCODES 字典中的别名）
        """
        if isinstance(code, str):
            resolved = KEYCODES.get(code.lower())
            if resolved is None:
                raise ValueError(f"未知按键名: {code}（可用: {', '.join(sorted(KEYCODES.keys()))}）")
            code = resolved
        self.adb.shell_input("keyevent", str(code))

    def press_back(self):
        """按返回键"""
        self.keyevent(4)

    def press_home(self):
        """按 Home 键"""
        self.keyevent(3)

    def press_enter(self):
        """按回车键"""
        self.keyevent(66)

    def wake_screen(self):
        """唤醒屏幕"""
        self.keyevent(224)

    def sleep_screen(self):
        """休眠屏幕"""
        self.keyevent(223)

    def open_recents(self):
        """打开最近任务列表（应用快速切换）

        等同于按多任务键/方形键/keyevent 187
        """
        self.keyevent(187)

    def open_notifications(self):
        """下拉通知栏"""
        self.keyevent(83)

    # ---------- 应用 ----------

    def launch_app(self, package: str, activity: Optional[str] = None):
        """启动应用

        Args:
            package: 应用包名
            activity: Activity 名（可选）。如 `com.example/.MainActivity`，省略则启动默认入口
        """
        if activity:
            component = f"{package}/{activity}" if not activity.startswith(".") else f"{package}{activity}"
            cmd = ["am", "start", "-n", component]
        else:
            cmd = ["monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]

        rc, stdout, stderr = self.adb.shell(*cmd)
        if rc != 0:
            raise RuntimeError(f"启动应用失败 [{package}]: {stderr.strip() or stdout.strip()}")
        logger.debug("启动应用: {} stdout={}", package, stdout.strip())

    def stop_app(self, package: str):
        """强制停止应用"""
        rc, stdout, stderr = self.adb.shell("am", "force-stop", package)
        if rc != 0:
            raise RuntimeError(f"停止应用失败 [{package}]: {stderr.strip()}")

    def go_home(self):
        """回到桌面（等同 press_home）"""
        self.press_home()