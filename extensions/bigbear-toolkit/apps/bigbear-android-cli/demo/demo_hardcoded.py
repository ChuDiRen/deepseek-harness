# -*- coding: utf-8 -*-
"""
Demo 1: 固定坐标版（0 基础入门）

目标：熟悉「adb 连设备 → 截图 → tap → input text」基础链路
特点：坐标写死，不调 AI

跑这个命令： python demo_hardcoded.py

前置条件：
  1. adb 在 PATH 里（adb version 能输出）
  2. 至少一台设备已连接（adb devices 能看到）
  3. 设备 USB 调试已开启
"""

import os
import re
import time
import subprocess
import base64
import io
from pathlib import Path

from PIL import Image


# ─────────────────────────────────────────────────────────────
# 配置：点击坐标（写死的）+ 屏幕尺寸自适应
# ─────────────────────────────────────────────────────────────
# 屏幕中心点的相对坐标（0~1 范围）
# 例如 (0.5, 0.5) 是屏幕正中心
TAP_RELATIVE_X = 0.5
TAP_RELATIVE_Y = 0.5

# 要输入的文本
INPUT_TEXT = "hello adb"

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────
# 工具函数：封装 adb 命令
# ─────────────────────────────────────────────────────────────
def run_adb(*args, timeout=30):
    """执行 adb 命令，返回 (returncode, stdout, stderr)"""
    cmd = ["adb", *args]
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def check_adb_available():
    """检查 adb 是否可用"""
    try:
        rc, stdout, _ = run_adb("version")
        return rc == 0, stdout.strip().split('\n')[0] if stdout else "unknown"
    except FileNotFoundError:
        return False, "adb 命令未找到（请安装 Android Platform Tools 并加 PATH）"


def get_devices():
    """列出所有 adb 设备"""
    rc, stdout, _ = run_adb("devices", "-l")
    devices = []
    for line in stdout.splitlines()[1:]:
        line = line.strip()
        if not line or "\t" not in line:
            continue
        parts = line.split()
        if len(parts) < 2 or parts[1] != "device":
            continue
        serial = parts[0]
        # 提取 model 字段
        model = ""
        for token in parts[2:]:
            if token.startswith("model:"):
                model = token[len("model:"):]
                break
        devices.append({"serial": serial, "model": model})
    return devices


def get_screen_size():
    """获取屏幕分辨率 (w, h)"""
    rc, stdout, _ = run_adb("shell", "wm", "size")
    if rc != 0:
        raise RuntimeError(f"获取屏幕尺寸失败: {stdout}")
    # 输出示例: "Physical size: 1080x2400"
    match = re.search(r"(\d+)\s*x\s*(\d+)", stdout)
    if not match:
        raise RuntimeError(f"无法解析屏幕尺寸: {stdout!r}")
    return int(match.group(1)), int(match.group(2))


def screencap_png():
    """截屏，返回 PNG bytes"""
    # exec-out 是 adb 的二进制输出模式（不会自动加换行符）
    result = subprocess.run(
        ["adb", "exec-out", "screencap", "-p"],
        capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"screencap 失败: {result.stderr.decode(errors='replace')}")
    return result.stdout


def tap(x, y):
    """点击坐标 (x, y)"""
    run_adb("shell", "input", "tap", str(int(x)), str(int(y)))


def input_ascii_text(text):
    """输入 ASCII 文本（不能输中文）"""
    # adb shell input text 的特殊字符处理：
    # - 空格要用 %s
    # - & | 等 shell 特殊字符要转义
    escaped = text.replace(" ", "%s")
    run_adb("shell", "input", "text", escaped)


# ─────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Demo 1: 固定坐标版（Android）")
    print("=" * 60)

    # 第 1 步：检查 adb
    print("[DEMO1] 第 1 步：检测 adb ...")
    available, version = check_adb_available()
    if not available:
        print(f"[FAIL] {version}")
        print("       请安装 https://developer.android.com/tools/releases/platform-tools")
        return
    print(f"[DEMO1]   ✓ adb 可用: {version}")

    # 第 2 步：检查设备
    print("[DEMO1] 第 2 步：检测设备 ...")
    devices = get_devices()
    if not devices:
        print("[FAIL] 没有可用设备")
        print("       1. USB 调试开了吗？")
        print("       2. 数据线连好了吗？")
        print("       3. 手机点过'允许 USB 调试'吗？")
        return
    print(f"[DEMO1]   ✓ 找到 {len(devices)} 台设备:")
    for d in devices:
        print(f"[DEMO1]     - {d['serial']}  ({d['model']})")

    # 第 3 步：拿屏幕尺寸
    print("[DEMO1] 第 3 步：获取屏幕尺寸 ...")
    w, h = get_screen_size()
    print(f"[DEMO1]   ✓ 屏幕尺寸: {w} x {h}")

    # 把相对坐标转成绝对坐标
    tap_x = int(w * TAP_RELATIVE_X)
    tap_y = int(h * TAP_RELATIVE_Y)
    print(f"[DEMO1]   → 将点击 ({TAP_RELATIVE_X}, {TAP_RELATIVE_Y}) → ({tap_x}, {tap_y})")

    # 第 4 步：截图（操作前）
    print("[DEMO1] 第 4 步：截图（操作前）...")
    png_bytes = screencap_png()
    img = Image.open(io.BytesIO(png_bytes))
    before_path = OUTPUT_DIR / "01_before.png"
    img.save(before_path)
    print(f"[DEMO1]   ✓ 保存: {before_path} ({w}x{h})")

    # 第 5 步：点击
    print(f"[DEMO1] 第 5 步：在坐标 ({tap_x}, {tap_y}) tap ...")
    tap(tap_x, tap_y)
    time.sleep(0.5)

    # 第 6 步：输入文本
    print(f"[DEMO1] 第 6 步：输入文本 '{INPUT_TEXT}' ...")
    if re.search(r'[^\x00-\x7F]', INPUT_TEXT):
        print("[DEMO1]   ⚠ 含中文，走剪贴板方案（Demo 1 简化版只支持 ASCII）")
        print("[DEMO1]   请改成英文测试，或跑 Demo 2/3 看完整中文输入")
    else:
        input_ascii_text(INPUT_TEXT)
        print(f"[DEMO1]   ✓ 输入完成")

    time.sleep(0.5)

    # 第 7 步：截图（操作后）
    print("[DEMO1] 第 7 步：截图（操作后）...")
    png_bytes = screencap_png()
    img = Image.open(io.BytesIO(png_bytes))
    after_path = OUTPUT_DIR / "02_after.png"
    img.save(after_path)
    print(f"[DEMO1]   ✓ 保存: {after_path}")

    print()
    print("=" * 60)
    print("[DEMO1] 完成！请打开 output/02_after.png 查看效果")
    print()
    print("  排查指引：")
    print(f"    - 屏幕中心点 ({tap_x}, {tap_y}) 是什么？是输入框就赢了")
    print(f"    - 是桌面就说明坐标没点中想点的元素，改 TAP_RELATIVE_X/Y")
    print("    - 你的设备分辨率是 1080x2400，屏幕中点就是 (540, 1200)")
    print("=" * 60)


if __name__ == "__main__":
    main()