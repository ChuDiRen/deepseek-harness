# -*- coding: utf-8 -*-
"""
Demo 3: 逐步拆解版（理解每一层，使用 0-1000 归一化坐标）

目标：把「截图 → AI → 坐标 → 键鼠」拆成 7 个独立可运行的步骤
特点：每步可以单独跑，每步都有详细打印说明数据流

跑这个命令： python demo_step_by_step.py

⚠️ 用法：在文件最末尾的 if __name__ == "__main__" 里选择要跑哪个 step

⚠️ 重要：本 demo 用 0-1000 归一化坐标（和官方源码一致）
       不要再用「像素坐标」方案——多数 AI 模型不听提示，会返回 0-1000
"""

import os
import io
import time
import json
import base64
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 第三方库
# ─────────────────────────────────────────────────────────────
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from playwright.sync_api import sync_playwright


# ─────────────────────────────────────────────────────────────
# 全局配置
# ─────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TARGET_URL = "https://www.baidu.com"
ELEMENT_DESC = "搜索框"
INPUT_TEXT = "一步一步学自动化"


# ─────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────
def load_config():
    """读 .env 里的 AI 配置"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        raise FileNotFoundError(
            f"找不到 .env：{env_path}\n"
            f"请先复制 .env.example 为 .env 并填好配置"
        )
    load_dotenv(env_path)
    return {
        "api_key": os.getenv("WEB_AUTOMATION_AI_API_KEY"),
        "base_url": os.getenv("WEB_AUTOMATION_AI_BASE_URL"),
        "model": os.getenv("WEB_AUTOMATION_AI_MODEL"),
    }


def hr(title):
    """打印分隔线"""
    print()
    print("─" * 60)
    print(f"  {title}")
    print("─" * 60)


def bbox_1000_to_pixel(bbox_1000, w, h):
    """0-1000 归一化坐标 → 真实像素坐标

    这是整个 demo 最核心的换算函数！

    公式：归一化值 × (真实尺寸 / 1000)

    示例（图片 1920×1080，AI 返回 [400, 200, 800, 400]）:
      scale_x = 1920/1000 = 1.92
      scale_y = 1080/1000 = 1.08
      x1 = 400 × 1.92 = 768
      y1 = 200 × 1.08 = 216
      x2 = 800 × 1.92 = 1536
      y2 = 400 × 1.08 = 432
    → bbox_pixel = [768, 216, 1536, 432]
    → 中心点 = (1152, 324)
    """
    scale_x = w / 1000
    scale_y = h / 1000
    return [
        int(bbox_1000[0] * scale_x),
        int(bbox_1000[1] * scale_y),
        int(bbox_1000[2] * scale_x),
        int(bbox_1000[3] * scale_y),
    ]


# ─────────────────────────────────────────────────────────────
# STEP 1: 启动浏览器
# ─────────────────────────────────────────────────────────────
def step_1_launch_browser():
    """Playwright 三层结构：playwright → browser → page"""
    hr("STEP 1: 启动浏览器")

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()

    print("  ✓ 浏览器启动成功")
    print("    - playwright: 管家（管理浏览器进程）")
    print("    - browser:    浏览器进程（一个 Chrome 实例）")
    print("    - page:       标签页（具体操作的对象）")

    time.sleep(3)

    browser.close()
    playwright.stop()
    print("  ✓ 浏览器已关闭")


# ─────────────────────────────────────────────────────────────
# STEP 2: 打开网页
# ─────────────────────────────────────────────────────────────
def step_2_navigate():
    """page.goto(url) 让浏览器跳转到指定 URL"""
    hr("STEP 2: 打开网页")

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()

    print(f"  → 访问 {TARGET_URL}")
    page.goto(TARGET_URL)
    page.wait_for_load_state("networkidle", timeout=10000)
    print("  ✓ 页面加载完成")

    time.sleep(2)
    browser.close()
    playwright.stop()


# ─────────────────────────────────────────────────────────────
# STEP 3: 截图
# ─────────────────────────────────────────────────────────────
def step_3_screenshot():
    """page.screenshot() 返回图片 bytes，可以保存成 PNG"""
    hr("STEP 3: 截图并保存")

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(TARGET_URL)
    page.wait_for_load_state("networkidle", timeout=10000)

    print("  → 调用 page.screenshot() ...")
    img_bytes = page.screenshot()
    print(f"  ✓ 拿到 {len(img_bytes)} 字节图片数据")

    output_path = OUTPUT_DIR / "step3_screenshot.png"
    with open(output_path, "wb") as f:
        f.write(img_bytes)
    print(f"  ✓ 保存到：{output_path}")

    img = Image.open(io.BytesIO(img_bytes))
    w, h = img.size
    print(f"  ✓ 图片尺寸：{w} × {h} 像素")
    print()
    print("  📐 重要：图片尺寸决定后续坐标换算的缩放因子")
    print(f"     scale_x = {w} / 1000 = {w/1000:.3f}")
    print(f"     scale_y = {h} / 1000 = {h/1000:.3f}")

    time.sleep(2)
    browser.close()
    playwright.stop()


# ─────────────────────────────────────────────────────────────
# STEP 4: 调 AI（用 0-1000 归一化）
# ─────────────────────────────────────────────────────────────
def step_4_call_ai():
    """调 AI 识别元素，重点理解 0-1000 坐标的换算"""
    hr("STEP 4: 调 AI 识别元素（0-1000 归一化坐标）")

    config = load_config()
    print(f"  → 模型：{config['model']}")

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(TARGET_URL)
    page.wait_for_load_state("networkidle", timeout=10000)

    img_bytes = page.screenshot()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    img = Image.open(io.BytesIO(img_bytes))
    w, h = img.size

    print(f"  → 截图尺寸：{w} × {h}")
    print(f"  → base64 长度：{len(img_base64)} 字符")

    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])

    # 关键：提示词明确说 0-1000
    prompt = f"""你是一个 UI 元素定位专家。

请看截图，找到「{ELEMENT_DESC}」，并返回它的边界框坐标。

## 坐标系统（重要！）
- 使用 **0-1000 归一化坐标**
- (0, 0) 是左上角，(1000, 1000) 是右下角
- bbox 值必须是 0-1000 之间的整数

## 输出严格 JSON（不要其他任何文字）
{{
  "found": true,
  "bbox": [xmin, ymin, xmax, ymax]
}}

图片实际尺寸：{w}x{h} 像素（但请按 0-1000 系统输出，不要输出像素值）
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
                 "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                {"type": "text", "text": prompt}
            ]
        }]
    )

    ai_text = completion.choices[0].message.content
    print()
    print(f"  ← AI 原始响应：")
    print(f"     {ai_text}")

    result = json.loads(ai_text)
    bbox_1000 = result["bbox"]

    print()
    print(f"  ── 坐标换算（最关键的一步）──")
    print(f"  AI 返回（0-1000）: {bbox_1000}")
    print(f"  图片尺寸:           {w} × {h}")
    print(f"  缩放因子:           x={w/1000:.3f}, y={h/1000:.3f}")

    bbox_pixel = bbox_1000_to_pixel(bbox_1000, w, h)
    cx = (bbox_pixel[0] + bbox_pixel[2]) / 2
    cy = (bbox_pixel[1] + bbox_pixel[3]) / 2

    print(f"  还原成像素:         {bbox_pixel}")
    print(f"  中心点:             ({cx:.0f}, {cy:.0f})")
    print()
    print("  【你应该理解】")
    print("    - AI 返回的是 0-1000 范围内的数字（无论图片多大都一样）")
    print("    - 真实坐标 = (value × 图片尺寸 / 1000)")
    print("    - 这样不管 1280×720 还是 4K 图片，逻辑都一致")

    browser.close()
    playwright.stop()


# ─────────────────────────────────────────────────────────────
# STEP 5: 在坐标点击
# ─────────────────────────────────────────────────────────────
def step_5_click():
    """page.mouse.click(x, y) 模拟鼠标点击"""
    hr("STEP 5: 在坐标点击")

    X, Y = 640, 280  # 百度搜索框的大概位置

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(TARGET_URL)
    page.wait_for_load_state("networkidle", timeout=10000)

    print(f"  → 在坐标 ({X}, {Y}) 点击")
    page.mouse.click(X, Y)
    time.sleep(1)
    print(f"  ✓ 完成")

    print()
    print("  【你应该看到】搜索框里有闪烁的光标（焦点）")

    time.sleep(2)
    browser.close()
    playwright.stop()


# ─────────────────────────────────────────────────────────────
# STEP 6: 输入文本
# ─────────────────────────────────────────────────────────────
def step_6_input():
    """page.keyboard.type() 模拟键盘逐字输入"""
    hr("STEP 6: 输入文本")

    X, Y = 640, 280

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(TARGET_URL)
    page.wait_for_load_state("networkidle", timeout=10000)

    print(f"  → 点击 ({X}, {Y}) 获取焦点")
    page.mouse.click(X, Y)
    time.sleep(0.5)

    print(f"  → 输入 '{INPUT_TEXT}'")
    page.keyboard.press("Control+a")
    time.sleep(0.05)
    page.keyboard.press("Delete")
    time.sleep(0.05)
    page.keyboard.type(INPUT_TEXT, delay=50)

    output_path = OUTPUT_DIR / "step6_after_input.png"
    page.screenshot(path=str(output_path))
    print(f"  ✓ 输入完成，截图：{output_path}")

    time.sleep(2)
    browser.close()
    playwright.stop()


# ─────────────────────────────────────────────────────────────
# STEP 8: 完整流程
# ─────────────────────────────────────────────────────────────
def step_8_full_pipeline():
    """完整流程：截图 → AI（0-1000） → 还原像素 → 点击 → 输入 → 截图"""
    hr("STEP 8: 完整流程（截图 → AI → 坐标 → 键鼠）")

    config = load_config()

    print("  [1/6] 启动浏览器 ...")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()

    print(f"  [2/6] 打开 {TARGET_URL} ...")
    page.goto(TARGET_URL)
    page.wait_for_load_state("networkidle", timeout=10000)

    print("  [3/6] 截图 ...")
    img_bytes = page.screenshot()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    img = Image.open(io.BytesIO(img_bytes))
    w, h = img.size
    print(f"        尺寸：{w}×{h}, base64: {len(img_base64)} 字符")

    print(f"  [4/6] 调 AI 找「{ELEMENT_DESC}」 ...")
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    prompt = f"""找截图里的「{ELEMENT_DESC}」。

使用 **0-1000 归一化坐标**：(0,0) 是左上角，(1000,1000) 是右下角。

输出 JSON：
{{"found": true, "bbox": [xmin, ymin, xmax, ymax]}}

图片实际尺寸 {w}x{h} 像素，但请按 0-1000 系统输出 bbox。"""
    completion = client.chat.completions.create(
        model=config["model"],
        temperature=0.1,
        max_tokens=256,
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                {"type": "text", "text": prompt}
            ]
        }]
    )
    ai_text = completion.choices[0].message.content
    result = json.loads(ai_text)
    bbox_1000 = result["bbox"]
    bbox_pixel = bbox_1000_to_pixel(bbox_1000, w, h)
    cx = (bbox_pixel[0] + bbox_pixel[2]) / 2
    cy = (bbox_pixel[1] + bbox_pixel[3]) / 2
    print(f"        AI 返回（0-1000）: {bbox_1000}")
    print(f"        还原像素:          {bbox_pixel}")
    print(f"        中心点:            ({cx:.0f}, {cy:.0f})")

    print(f"  [5/6] 在 ({cx:.0f}, {cy:.0f}) 点击 + 输入 ...")
    page.mouse.click(cx, cy)
    time.sleep(0.5)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    time.sleep(0.1)
    page.keyboard.type(INPUT_TEXT, delay=50)

    print("  [6/6] 截图保存 ...")
    output_path = OUTPUT_DIR / "step8_final.png"
    page.screenshot(path=str(output_path))
    print(f"        截图：{output_path}")

    print()
    print("  ✅ 完整流程跑完了！")
    print(f"     查看 {output_path}")

    time.sleep(3)
    browser.close()
    playwright.stop()


# ─────────────────────────────────────────────────────────────
# 入口：选择要跑哪个 step
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Demo 3: 逐步拆解版（0-1000 归一化坐标方案）")
    print("=" * 60)
    print()
    print("可用 step：")
    print("  step_1_launch_browser()  - 只启动浏览器")
    print("  step_2_navigate()         - 打开百度")
    print("  step_3_screenshot()       - 截图并保存")
    print("  step_4_call_ai()          - 调 AI 找元素（需 API Key）")
    print("  step_5_click()            - 在坐标点击")
    print("  step_6_input()            - 输入文本")
    print("  step_8_full_pipeline()    - 完整流程")
    print()
    print("默认跑：step_8_full_pipeline()")
    print("想换 step，编辑下面这一行 ↓")

    # ─────── 在这里选择要跑的 step ───────
    step_8_full_pipeline()
    # step_1_launch_browser()
    # step_2_navigate()
    # step_3_screenshot()
    # step_4_call_ai()
    # step_5_click()
    # step_6_input()