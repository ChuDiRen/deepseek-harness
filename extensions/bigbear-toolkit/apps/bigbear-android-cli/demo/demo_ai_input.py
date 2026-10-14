# -*- coding: utf-8 -*-
"""
Demo 2: AI 找元素版（Android 完整流程，使用 0-1000 归一化坐标）

目标：演示「AI 视觉识别 + adb 自动化」的完整链路
特点：元素坐标由 AI 自动识别
重点：坐标用 0-1000 归一化方案（和官方源码一致）

跑这个命令： python demo_ai_input.py

前置条件：
  1. adb 在 PATH 里 + 设备已连
  2. 已经 pip install -r requirements.txt
  3. 已经在 .env 里填好 ANDROID_AI_* 配置（用视觉模型）
"""

import os
import re
import io
import time
import json
import base64
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw


# ─────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────
DEBUG = True  # True = 额外保存一张红框标注图

ELEMENT_DESC = "搜索框"   # 改成你想找的任何元素
INPUT_TEXT = "Playwright 真好用"  # 含中文，会走剪贴板

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────
# 加载配置
# ─────────────────────────────────────────────────────────────
def load_config():
    """从 .env 读 AI 接口配置（注意 Android 用的是 ANDROID_AI_* 前缀）"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        raise FileNotFoundError(
            f"找不到 .env：{env_path}\n"
            "请先 cp .env.example .env 并填好配置"
        )
    load_dotenv(env_path)

    config = {
        "api_key": os.getenv("ANDROID_AI_API_KEY"),
        "base_url": os.getenv("ANDROID_AI_BASE_URL"),
        "model": os.getenv("ANDROID_AI_MODEL"),
    }
    for k, v in config.items():
        if not v:
            raise ValueError(f".env 里的 {k.upper()} 是空的，请填上")
    return config


# ─────────────────────────────────────────────────────────────
# adb 封装（精简版）
# ─────────────────────────────────────────────────────────────
def run_adb(*args, timeout=30):
    cmd = ["adb", *args]
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def check_devices():
    """检查 adb 设备"""
    rc, _, _ = run_adb("version")
    if rc != 0:
        raise RuntimeError("adb 不可用，请安装 Platform Tools 并加 PATH")

    rc, stdout, _ = run_adb("devices", "-l")
    devices = []
    for line in stdout.splitlines()[1:]:
        line = line.strip()
        if "\t" not in line:
            continue
        parts = line.split()
        if len(parts) < 2 or parts[1] != "device":
            continue
        devices.append({"serial": parts[0]})
    if not devices:
        raise RuntimeError("没有可用设备，请检查 USB 调试")
    return devices


def get_screen_size():
    rc, stdout, _ = run_adb("shell", "wm", "size")
    if rc != 0:
        raise RuntimeError(f"获取屏幕尺寸失败: {stdout}")
    m = re.search(r"(\d+)\s*x\s*(\d+)", stdout)
    if not m:
        raise RuntimeError(f"无法解析屏幕尺寸: {stdout!r}")
    return int(m.group(1)), int(m.group(2))


def screencap():
    """截屏，返回 (png_bytes, PIL.Image)"""
    result = subprocess.run(
        ["adb", "exec-out", "screencap", "-p"],
        capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"screencap 失败: {result.stderr.decode(errors='replace')}")
    png_bytes = result.stdout
    img = Image.open(io.BytesIO(png_bytes))
    return png_bytes, img


def screencap_jpeg_base64():
    """截屏转 JPEG base64（更省 token）"""
    png_bytes, img = screencap()
    # 转 RGB 模式（PNG 可能是 RGBA）
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    img_base64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return img_base64, img


def tap(x, y):
    run_adb("shell", "input", "tap", str(int(x)), str(int(y)))


def input_text(x, y, text):
    """点击 + 输入文本（自动处理中文）"""
    tap(x, y)
    time.sleep(0.3)

    if re.search(r'[^\x00-\x7F]', text):
        # 含中文：走剪贴板方案
        _input_via_clipboard(text)
    else:
        # ASCII：直接 input text（空格用 %s）
        escaped = text.replace(" ", "%s")
        run_adb("shell", "input", "text", escaped)


def _input_via_clipboard(text):
    """剪贴板方案输入中文（标准 Android 10+）"""
    # 清空：一次发 50 次 DEL
    run_adb("shell", "input", "keyevent", "123")  # MOVE_END
    time.sleep(0.05)
    run_adb("shell", "input", "keyevent", *(["67"] * 50))
    time.sleep(0.1)

    # 设置剪贴板
    rc, _, stderr = run_adb(
        "shell", "cmd", "clipboard", "set-primary-clip",
        "--user", "0", text,
    )
    stderr_text = stderr.strip() if stderr else ""
    if rc != 0 or "No shell command" in stderr_text or "Exception" in stderr_text:
        raise RuntimeError(
            f"剪贴板方案不可用（rc={rc}, stderr={stderr_text}）。"
            "常见于 vivo/ColorOS/HyperOS。"
            "请改用 ADBKeyboard 方案（见官方 actions.py）"
        )

    # 读回校验
    rc2, stdout, _ = run_adb("shell", "cmd", "clipboard", "get-primary-clip", "--user", "0")
    if rc2 != 0 or stdout.strip() != text:
        raise RuntimeError(
            f"剪贴板读回校验失败（rc={rc2}, got={stdout.strip()!r}）"
        )

    # 触发粘贴
    time.sleep(0.1)
    run_adb("shell", "input", "keyevent", "279")  # KEYCODE_PASTE
    time.sleep(0.3)


# ─────────────────────────────────────────────────────────────
# 核心：0-1000 归一化坐标 → 真实像素
# ─────────────────────────────────────────────────────────────
def convert_bbox_to_pixel(bbox_1000, w, h):
    """0-1000 归一化坐标 → 真实像素（Android 专用，不用 DPR）

    公式：value × (屏幕尺寸 / 1000)
    示例（屏幕 1080×2400，AI 返回 [240, 178, 960, 253]）:
      scale_x = 1080/1000 = 1.08
      scale_y = 2400/1000 = 2.40
      x1 = 240 × 1.08 = 259
      y1 = 178 × 2.40 = 427
    """
    return [
        int(bbox_1000[0] * w / 1000),
        int(bbox_1000[1] * h / 1000),
        int(bbox_1000[2] * w / 1000),
        int(bbox_1000[3] * h / 1000),
    ]


def get_center(bbox):
    return (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2


# ─────────────────────────────────────────────────────────────
# AI 视觉识别
# ─────────────────────────────────────────────────────────────
def call_ai_find_element(client, model, img_b64, w, h, element_desc):
    """调 AI 找元素坐标（0-1000 归一化）"""
    print(f"[DEMO2]   调 AI 找 '{element_desc}' ...")

    prompt = f"""## Role
You are an AI assistant specialized in UI element localization on Android devices.

## Objective
- ONLY identify if the target element exists in the screenshot.
- If found, provide the precise bounding box coordinates.
- Do NOT analyze page state or suggest actions.

## Output Format (strict JSON only)
{{
  "found": true | false,
  "bbox": [xmin, ymin, xmax, ymax] (only if found is true)
}}

## CRITICAL: Coordinate System
- Use NORMALIZED coordinates in the range 0 to 1000.
- (0, 0) = top-left, (1000, 1000) = bottom-right.
- bbox values must be integers between 0 and 1000.

## User Description
Find: {element_desc}

## Screenshot Analysis
- Image size: {w}x{h} pixels (Android screen)
- Output bbox in 0-1000 normalized space.
"""

    completion = client.chat.completions.create(
        model=model,
        temperature=0.1,
        max_tokens=512,
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }]
    )

    message = completion.choices[0].message
    finish_reason = completion.choices[0].finish_reason
    ai_text = message.content

    print(f"[DEMO2]   finish_reason = {finish_reason}")
    print(f"[DEMO2]   content 类型  = {type(ai_text).__name__}")

    # 防御式：AI 返回空
    if not ai_text:
        print()
        print(f"[DEMO2] ✗ AI 返回空内容（model={model}, finish_reason={finish_reason}）")
        print("    最常见原因：模型不是视觉模型")
        print("    请确认 .env 里 ANDROID_AI_MODEL 是 qwen-vl-plus / qwen-vl-max / gpt-4o 这种")
        raise Exception(f"AI 返回空内容（model={model}）")

    print(f"[DEMO2]   AI 响应：{ai_text[:200]}")

    try:
        result = json.loads(ai_text)
    except json.JSONDecodeError as e:
        raise Exception(f"AI 返回非 JSON：{ai_text[:200]}")

    if not result.get("found"):
        raise Exception(f"AI 没找到 '{element_desc}'")

    bbox_1000 = result["bbox"]
    if len(bbox_1000) != 4:
        raise Exception(f"bbox 格式错：{bbox_1000}")

    bbox_pixel = convert_bbox_to_pixel(bbox_1000, w, h)
    cx, cy = get_center(bbox_pixel)
    return (cx, cy), bbox_pixel, bbox_1000


# ─────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Demo 2: AI 找元素版（Android, 0-1000 归一化坐标）")
    print("=" * 60)

    # 读配置
    print("[DEMO2] 读配置 ...")
    config = load_config()
    print(f"[DEMO2]   Model: {config['model']}")

    # 检测设备
    print("[DEMO2] 第 1 步：检测设备 ...")
    devices = check_devices()
    serial = devices[0]["serial"]
    print(f"[DEMO2]   ✓ 设备: {serial}")

    # 屏幕尺寸
    w, h = get_screen_size()
    print(f"[DEMO2]   ✓ 屏幕尺寸: {w} x {h}")

    # AI 客户端
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])

    try:
        # 截图
        print("[DEMO2] 第 2 步：截图 ...")
        img_b64, img_pil = screencap_jpeg_base64()
        print(f"[DEMO2]   截图: {img_pil.size[0]}x{img_pil.size[1]}, base64={len(img_b64)} 字符")

        # 调 AI
        print(f"[DEMO2] 第 3 步：调 AI 找 '{ELEMENT_DESC}' ...")
        (cx, cy), bbox_pixel, bbox_1000 = call_ai_find_element(
            client, config["model"], img_b64, w, h, ELEMENT_DESC
        )

        # 详细打印坐标换算
        print()
        print(f"[DEMO2]   ── 坐标换算过程 ──")
        print(f"[DEMO2]   AI 返回（0-1000）: {bbox_1000}")
        print(f"[DEMO2]   缩放因子:           x={w/1000:.3f}, y={h/1000:.3f}")
        print(f"[DEMO2]   还原成像素:         {bbox_pixel}")
        print(f"[DEMO2]   中心点:             ({cx:.0f}, {cy:.0f})")

        # debug 模式：保存红框图
        if DEBUG:
            marked_path = OUTPUT_DIR / "ai_marked.png"
            debug_img = img_pil.copy()
            draw = ImageDraw.Draw(debug_img)
            draw.rectangle(bbox_pixel, outline="red", width=4)
            draw.text((bbox_pixel[0], max(bbox_pixel[1] - 25, 5)),
                      f"AI 框 ({ELEMENT_DESC})", fill="red")
            debug_img.save(marked_path)
            print(f"[DEMO2]   ✓ 标注图: {marked_path}")

        # 点击 + 输入
        print()
        print(f"[DEMO2] 第 4 步：在 ({cx:.0f}, {cy:.0f}) tap + 输入 '{INPUT_TEXT}' ...")
        input_text(cx, cy, INPUT_TEXT)

        time.sleep(1)

        # 截图（操作后）
        after_path = OUTPUT_DIR / "ai_after.png"
        png_bytes, _ = screencap()
        with open(after_path, "wb") as f:
            f.write(png_bytes)
        print(f"[DEMO2] 第 5 步：截图（操作后）→ {after_path}")

        print()
        print("=" * 60)
        print("[DEMO2] 完成！")
        print(f"  - 看效果:    {after_path}")
        if DEBUG:
            print(f"  - 看 AI 框:  {OUTPUT_DIR / 'ai_marked.png'}")
        print("=" * 60)

    finally:
        print()
        print("[DEMO2] 3 秒后退出 ...")
        time.sleep(3)


if __name__ == "__main__":
    main()