# -*- coding: utf-8 -*-
"""
Demo 3: 逐步拆解版（Android，理解每一层）

目标：把「截图 → AI → 坐标 → adb」拆成 7 个独立可运行的步骤
特点：每步可单独跑，每步都有详细打印

跑这个命令： python demo_step_by_step.py

⚠️ 用法：在文件最末尾的 if __name__ 里选择要跑哪个 step
"""

import os
import io
import re
import time
import json
import base64
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

# ─────────────────────────────────────────────────────────────
# 全局配置
# ─────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

ELEMENT_DESC = "搜索框"
INPUT_TEXT = "一步一步学自动化"


# ─────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────
def load_config():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f"找不到 .env：{env_path}")
    load_dotenv(env_path)
    return {
        "api_key": (os.getenv("ANDROID_AI_API_KEY") or os.getenv("DSH_BIGBEAR_ANDROID_AI_API_KEY")),
        "base_url": (os.getenv("ANDROID_AI_BASE_URL") or os.getenv("DSH_BIGBEAR_ANDROID_AI_BASE_URL")),
        "model": (os.getenv("ANDROID_AI_MODEL") or os.getenv("DSH_BIGBEAR_ANDROID_AI_MODEL")),
    }


def run_adb(*args, timeout=30):
    return subprocess.run(
        ["adb", *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    ).returncode, subprocess.run(["adb", *args], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace",
                                  timeout=timeout).stdout, ""


def run_adb_bytes(*args, timeout=30):
    return subprocess.run(
        ["adb", *args], capture_output=True, timeout=timeout,
    )


def hr(title):
    print()
    print("─" * 60)
    print(f"  {title}")
    print("─" * 60)


def bbox_1000_to_pixel(bbox_1000, w, h):
    """0-1000 归一化坐标 → 真实像素"""
    return [
        int(bbox_1000[0] * w / 1000),
        int(bbox_1000[1] * h / 1000),
        int(bbox_1000[2] * w / 1000),
        int(bbox_1000[3] * h / 1000),
    ]


# ─────────────────────────────────────────────────────────────
# STEP 1: 检查 adb 设备
# ─────────────────────────────────────────────────────────────
def step_1_check_adb():
    hr("STEP 1: 检查 adb 设备")

    # 检查 adb 是否安装
    r = subprocess.run(["adb", "version"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=10)
    if r.returncode != 0:
        print(f"  ✗ adb 不可用: {r.stderr}")
        return
    print(f"  ✓ adb 版本: {r.stdout.strip().split(chr(10))[0]}")

    # 列设备
    r = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=10)
    print(f"\n  设备列表：")
    print(f"    {r.stdout}")
    print(f"  【你应该看到】至少一台设备，state=device（不是 offline/unauthorized）")
    print(f"  如果没设备：检查 USB 调试 / 数据线 / 手机授权弹窗")


# ─────────────────────────────────────────────────────────────
# STEP 2: 获取屏幕尺寸
# ─────────────────────────────────────────────────────────────
def step_2_screen_size():
    hr("STEP 2: 获取屏幕尺寸")

    print("  → 执行 adb shell wm size")
    r = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=10)
    print(f"  原始输出: {r.stdout.strip()}")

    m = re.search(r"(\d+)\s*x\s*(\d+)", r.stdout)
    if not m:
        print("  ✗ 无法解析")
        return
    w, h = int(m.group(1)), int(m.group(2))
    print(f"  ✓ 屏幕: {w} x {h}")
    print()
    print("  📐 重要：这个尺寸决定坐标换算的缩放因子")
    print(f"     scale_x = {w} / 1000 = {w/1000:.3f}")
    print(f"     scale_y = {h} / 1000 = {h/1000:.3f}")
    print()
    print(f"  屏幕中点: ({w//2}, {h//2})")


# ─────────────────────────────────────────────────────────────
# STEP 3: 截图保存
# ─────────────────────────────────────────────────────────────
def step_3_screenshot():
    hr("STEP 3: 截图")

    print("  → 执行 adb exec-out screencap -p ...")
    r = subprocess.run(["adb", "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=30)
    png_bytes = r.stdout
    print(f"  ✓ 拿到 {len(png_bytes)} 字节 PNG")

    output_path = OUTPUT_DIR / "step3_screenshot.png"
    with open(output_path, "wb") as f:
        f.write(png_bytes)
    print(f"  ✓ 保存: {output_path}")

    img = Image.open(io.BytesIO(png_bytes))
    print(f"  ✓ PIL 尺寸: {img.size[0]} x {img.size[1]}")

    print()
    print("  【你应该看到】")
    print(f"    - {output_path} 文件存在")
    print(f"    - 打开它能看到当前设备屏幕")
    print()
    print("  💡 注意：exec-out 和 shell 不一样")
    print("     - adb shell screencap 会自动加换行符，导致 PNG 损坏")
    print("     - adb exec-out screencap -p 才是二进制原样输出（标准做法）")


# ─────────────────────────────────────────────────────────────
# STEP 4: 调 AI（重点：0-1000 归一化）
# ─────────────────────────────────────────────────────────────
def step_4_call_ai():
    hr("STEP 4: 调 AI 找元素（0-1000 归一化坐标）")

    config = load_config()
    print(f"  → 模型: {config['model']}")

    # 拿屏幕尺寸
    r = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
    w, h = map(int, re.search(r"(\d+)\s*x\s*(\d+)", r.stdout).groups())

    # 截图
    print(f"  → 截图...")
    r = subprocess.run(["adb", "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=30)
    img = Image.open(io.BytesIO(r.stdout))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    print(f"    base64 长度: {len(img_b64)} 字符")

    # 调 AI
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    prompt = f"""你是 Android UI 元素定位专家。

找截图里的「{ELEMENT_DESC}」。

## 坐标系统（重要！）
- 使用 0-1000 归一化坐标
- (0, 0) = 左上角，(1000, 1000) = 右下角

## 输出 JSON（严格）
{{"found": true, "bbox": [xmin, ymin, xmax, ymax]}}

屏幕实际尺寸: {w}x{h} 像素，但请按 0-1000 系统输出。
"""

    print("  → 调 AI 接口 ...")
    completion = client.chat.completions.create(
        model=config["model"],
        temperature=0.1,
        max_tokens=256,
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

    print(f"\n  finish_reason = {finish_reason}")
    print(f"  content 类型  = {type(ai_text).__name__}")

    if not ai_text:
        print(f"\n  ✗ AI 返回空！model={config['model']}")
        print(f"    最可能：模型不是视觉模型")
        return

    print(f"  AI 响应: {ai_text[:200]}")
    result = json.loads(ai_text)
    bbox_1000 = result["bbox"]

    print()
    print(f"  ── 坐标换算（核心）──")
    print(f"  AI 返回（0-1000）: {bbox_1000}")
    print(f"  缩放因子:           x={w/1000:.3f}, y={h/1000:.3f}")
    bbox_pixel = bbox_1000_to_pixel(bbox_1000, w, h)
    cx = (bbox_pixel[0] + bbox_pixel[2]) / 2
    cy = (bbox_pixel[1] + bbox_pixel[3]) / 2
    print(f"  还原成像素:         {bbox_pixel}")
    print(f"  中心点:             ({cx:.0f}, {cy:.0f})")
    print()
    print("  【你应该理解】")
    print("    - AI 输出的是 0-1000 数字，不管屏幕多大都一样")
    print("    - 真实坐标 = value × (屏幕尺寸 / 1000)")
    print("    - Android 不用考虑 DPR，直接用屏幕像素")


# ─────────────────────────────────────────────────────────────
# STEP 5: tap 一个坐标
# ─────────────────────────────────────────────────────────────
def step_5_tap():
    hr("STEP 5: tap 坐标")

    # 拿屏幕尺寸，tap 屏幕中心
    r = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
    w, h = map(int, re.search(r"(\d+)\s*x\s*(\d+)", r.stdout).groups())
    x, y = w // 2, h // 2

    print(f"  → 屏幕尺寸: {w} x {h}")
    print(f"  → 在中心点 ({x}, {y}) tap")

    r = subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)],
                       capture_output=True, timeout=10)
    print(f"  ✓ tap 完成（rc={r.returncode}）")

    print()
    print("  【你应该看到】")
    print(f"    - 设备屏幕中心被点击了")
    print(f"    - 如果中点是个图标，可能会打开应用/弹窗")
    print(f"    - 如果中点是个输入框，会出现闪烁光标")

    time.sleep(2)


# ─────────────────────────────────────────────────────────────
# STEP 6: 输入文本（含中文）
# ─────────────────────────────────────────────────────────────
def step_6_input():
    hr("STEP 6: 输入文本")

    # 拿屏幕尺寸
    r = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
    w, h = map(int, re.search(r"(\d+)\s*x\s*(\d+)", r.stdout).groups())
    x, y = w // 2, h // 2

    # 先点击
    print(f"  → 点击 ({x}, {y})")
    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], timeout=10)
    time.sleep(0.5)

    print(f"  → 输入: {INPUT_TEXT!r}")
    if re.search(r'[^\x00-\x7F]', INPUT_TEXT):
        # 中文走剪贴板
        print(f"    含中文，走剪贴板方案")
        subprocess.run(["adb", "shell", "input", "keyevent", "123"], timeout=10)  # MOVE_END
        time.sleep(0.05)
        subprocess.run(["adb", "shell", "input", "keyevent", *(["67"] * 30)], timeout=10)
        time.sleep(0.1)
        r = subprocess.run(
            ["adb", "shell", "cmd", "clipboard", "set-primary-clip", "--user", "0", INPUT_TEXT],
            capture_output=True, timeout=10
        )
        if r.returncode != 0:
            print(f"    ✗ 剪贴板失败: {r.stderr.decode()}")
            print(f"    试试跑 Demo 2，看完整剪贴板方案 + ADBKeyboard 回退")
            return
        time.sleep(0.1)
        subprocess.run(["adb", "shell", "input", "keyevent", "279"], timeout=10)  # PASTE
    else:
        # ASCII
        escaped = INPUT_TEXT.replace(" ", "%s")
        subprocess.run(["adb", "shell", "input", "text", escaped], timeout=10)

    print(f"  ✓ 输入完成")
    time.sleep(1)

    # 截图保存
    out = OUTPUT_DIR / "step6_after_input.png"
    r = subprocess.run(["adb", "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=30)
    with open(out, "wb") as f:
        f.write(r.stdout)
    print(f"  ✓ 截图: {out}")


# ─────────────────────────────────────────────────────────────
# STEP 8: 完整流程
# ─────────────────────────────────────────────────────────────
def step_8_full_pipeline():
    hr("STEP 8: 完整流程（截图 → AI → tap → 输入）")

    config = load_config()
    print(f"  模型: {config['model']}")

    # 拿屏幕尺寸
    r = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
    w, h = map(int, re.search(r"(\d+)\s*x\s*(\d+)", r.stdout).groups())
    print(f"  屏幕: {w}x{h}")

    # 截图
    print("  → 截图 ...")
    r = subprocess.run(["adb", "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=30)
    img = Image.open(io.BytesIO(r.stdout))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    print(f"    base64: {len(img_b64)} 字符")

    # 调 AI
    print(f"  → 调 AI 找 '{ELEMENT_DESC}' ...")
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    prompt = f"""找 Android 截图里的「{ELEMENT_DESC}」。

使用 0-1000 归一化坐标（0=左上, 1000=右下）。

输出 JSON:
{{"found": true, "bbox": [xmin, ymin, xmax, ymax]}}

屏幕实际尺寸 {w}x{h} 像素，但请按 0-1000 输出。"""
    completion = client.chat.completions.create(
        model=config["model"], temperature=0.1, max_tokens=256,
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }]
    )
    ai_text = completion.choices[0].message.content
    if not ai_text:
        print(f"  ✗ AI 返回空！model={config['model']}, 请换成视觉模型")
        return
    result = json.loads(ai_text)
    bbox_1000 = result["bbox"]
    bbox_pixel = bbox_1000_to_pixel(bbox_1000, w, h)
    cx = (bbox_pixel[0] + bbox_pixel[2]) / 2
    cy = (bbox_pixel[1] + bbox_pixel[3]) / 2
    print(f"    bbox（0-1000）: {bbox_1000}")
    print(f"    bbox（像素）:   {bbox_pixel}")
    print(f"    中心点:         ({cx:.0f}, {cy:.0f})")

    # tap
    print(f"  → tap ({cx:.0f}, {cy:.0f})")
    subprocess.run(["adb", "shell", "input", "tap", str(int(cx)), str(int(cy))], timeout=10)
    time.sleep(0.5)

    # 输入
    print(f"  → 输入 '{INPUT_TEXT}'")
    if re.search(r'[^\x00-\x7F]', INPUT_TEXT):
        subprocess.run(["adb", "shell", "input", "keyevent", "123"], timeout=10)
        subprocess.run(["adb", "shell", "input", "keyevent", *(["67"] * 30)], timeout=10)
        subprocess.run(
            ["adb", "shell", "cmd", "clipboard", "set-primary-clip", "--user", "0", INPUT_TEXT],
            timeout=10
        )
        time.sleep(0.1)
        subprocess.run(["adb", "shell", "input", "keyevent", "279"], timeout=10)
    else:
        subprocess.run(["adb", "shell", "input", "text", INPUT_TEXT.replace(" ", "%s")], timeout=10)

    time.sleep(1)

    # 截图
    out = OUTPUT_DIR / "step8_final.png"
    r = subprocess.run(["adb", "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=30)
    with open(out, "wb") as f:
        f.write(r.stdout)
    print(f"  ✓ 截图: {out}")
    print(f"\n  ✅ 完整流程跑完！查看 {out}")


# ─────────────────────────────────────────────────────────────
# 入口：选择 step
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Demo 3: 逐步拆解版（Android）")
    print("=" * 60)
    print()
    print("可用 step:")
    print("  step_1_check_adb()    - 检查 adb + 设备")
    print("  step_2_screen_size()  - 获取屏幕尺寸")
    print("  step_3_screenshot()   - 截图")
    print("  step_4_call_ai()      - 调 AI（需 API Key）")
    print("  step_5_tap()          - tap 坐标")
    print("  step_6_input()        - 输入文本")
    print("  step_8_full_pipeline()- 完整流程")
    print()
    print("默认跑：step_8_full_pipeline()")
    print("想换 step，编辑下面这一行 ↓")

    # ─────── 在这里选择要跑的 step ───────
    step_8_full_pipeline()
    # step_1_check_adb()
    # step_2_screen_size()
    # step_3_screenshot()
    # step_4_call_ai()
    # step_5_tap()
    # step_6_input()