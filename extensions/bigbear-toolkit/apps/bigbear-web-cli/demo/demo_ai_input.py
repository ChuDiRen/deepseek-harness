# -*- coding: utf-8 -*-
"""
Demo 2: AI 找元素版（完整流程，使用 0-1000 归一化坐标）

目标：演示「AI 视觉识别 + Playwright 自动化」的完整链路
特点：搜索框坐标由 AI 自动识别，不再写死
重点：坐标计算用 0-1000 归一化方案（和官方源码一致，最稳定）

跑这个命令： python demo_ai_input.py

前置条件：
  1. 已经 pip install -r requirements.txt
  2. 已经 playwright install chromium
  3. 已经在 .env 里填好 WEB_AUTOMATION_AI_API_KEY 等配置
"""

import os
import io
import base64
import time
import json
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 第三方库
# ─────────────────────────────────────────────────────────────
from dotenv import load_dotenv        # 读 .env 文件
from openai import OpenAI             # 调 AI（兼容 OpenAI 接口的都能用）
from PIL import Image, ImageDraw      # 处理图片 + 画红框（debug 用）
from playwright.sync_api import sync_playwright


# ─────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────
DEBUG = True  # True = 额外保存一张红框标注图；False = 节省时间

# 要找的元素（自然语言告诉 AI）
ELEMENT_DESC = "搜索框"

# 要输入的文本
INPUT_TEXT = "Playwright 真好用"

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 要打开的网址
TARGET_URL = "https://www.baidu.com"


# ─────────────────────────────────────────────────────────────
# 加载配置
# ─────────────────────────────────────────────────────────────
def load_config():
    """从 .env 读 AI 接口配置"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        raise FileNotFoundError(
            f"找不到 .env 文件：{env_path}\n"
            "请先复制 .env.example 为 .env 并填入配置"
        )
    load_dotenv(env_path)

    config = {
        "api_key": (os.getenv("WEB_AUTOMATION_AI_API_KEY") or os.getenv("DSH_BIGBEAR_WEB_AUTOMATION_AI_API_KEY")),
        "base_url": (os.getenv("WEB_AUTOMATION_AI_BASE_URL") or os.getenv("DSH_BIGBEAR_WEB_AUTOMATION_AI_BASE_URL")),
        "model": (os.getenv("WEB_AUTOMATION_AI_MODEL") or os.getenv("DSH_BIGBEAR_WEB_AUTOMATION_AI_MODEL")),
    }

    for k, v in config.items():
        if not v:
            raise ValueError(f".env 里的 {k.upper()} 是空的，请填上")

    return config


# ─────────────────────────────────────────────────────────────
# 核心：0-1000 归一化坐标 → 真实像素
# ─────────────────────────────────────────────────────────────
def convert_bbox_to_pixel(bbox_1000, image_width, image_height):
    """把 AI 返回的 0-1000 归一化坐标转换成真实像素

    这是整个 demo 最关键的函数！

    输入 bbox_1000: [x1, y1, x2, y2]，值在 0-1000 范围
    输出 bbox_pixel: [x1, y1, x2, y2]，值在 0-image_width 范围

    公式很简单：归一化值 × (真实尺寸 / 1000)
    """
    scale_x = image_width / 1000
    scale_y = image_height / 1000

    x1 = bbox_1000[0] * scale_x
    y1 = bbox_1000[1] * scale_y
    x2 = bbox_1000[2] * scale_x
    y2 = bbox_1000[3] * scale_y

    return [int(x1), int(y1), int(x2), int(y2)]


def get_center(bbox):
    """取 bbox 的中心点（点击元素中间最稳）"""
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    return cx, cy


# ─────────────────────────────────────────────────────────────
# AI 视觉识别
# ─────────────────────────────────────────────────────────────
def call_ai_to_find_element(client, model, image_base64, image_width, image_height, element_desc):
    """让 AI 看截图，返回元素坐标

    提示词明确告诉 AI：使用 0-1000 归一化坐标
    这样不管图片实际多大，输出格式都稳定

    出错时会打印完整的诊断信息（finish_reason / usage / 全 message），
    方便定位"为什么 AI 没返回内容"
    """
    print(f"[DEMO2]   调 AI 找 '{element_desc}' ...")

    prompt = f"""## Role
You are an AI assistant specialized in UI element localization on web pages.

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
- (0, 0) = top-left corner, (1000, 1000) = bottom-right corner.
- bbox values must be integers between 0 and 1000.

## User Description
Find: {element_desc}

## Screenshot Analysis
- Image size: {image_width}x{image_height} pixels
- You must scale your bbox to the 0-1000 normalized space.
"""

    completion = client.chat.completions.create(
        model=model,
        temperature=0.1,
        max_tokens=512,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    )

    # ── 关键：拿到原始 message 和 finish_reason ──
    message = completion.choices[0].message
    finish_reason = completion.choices[0].finish_reason
    ai_text = message.content

    # 把关键信息打出来（帮助诊断 None 的根因）
    print(f"[DEMO2]   finish_reason = {finish_reason}")
    print(f"[DEMO2]   content 类型  = {type(ai_text).__name__}")
    print(f"[DEMO2]   content 长度  = {len(ai_text) if ai_text else 0}")

    # ── 防御式：AI 没返回内容时的诊断 ──
    if not ai_text:
        print()
        print("=" * 60)
        print("[DEMO2] ✗ AI 返回了空内容")
        print("=" * 60)
        print()
        print("可能的原因：")
        print()

        # 场景 1：模型不支持图片（最常见）
        print("  ① 你用的模型不是视觉模型（最常见！）")
        print(f"     当前 Model = {model}")
        print("     请确认 .env 里的 WEB_AUTOMATION_AI_MODEL 是视觉模型：")
        print("       - 阿里云：qwen-vl-plus、qwen-vl-max、qwen2-vl-72b")
        print("       - OpenAI：gpt-4o、gpt-4-vision-preview")
        print("       - 其他平台请查文档")
        print()

        # 场景 2：finish_reason 提示
        if finish_reason == "content_filter":
            print("  ② finish_reason=content_filter：内容被安全策略拦截")
            print("     换一个简单的网页重试，或修改提示词")
        elif finish_reason == "length":
            print("  ③ finish_reason=length：max_tokens 不够，调大")
        elif finish_reason == "stop":
            print("  ② finish_reason=stop（正常结束）但内容为空")
            print("     这通常意味着模型根本没看懂图片，或者返回了非文本内容")
        print()

        # 场景 3：图片大小
        print(f"  ③ 图片太大？当前 base64 长度 = {len(image_base64)} 字符")
        print(f"     图片尺寸 = {image_width}x{image_height} 像素")
        print("     如果超过 1MB，可能超出模型输入限制")
        print()

        # 把原始响应打出来
        print("  原始 message 对象：")
        print(f"     {message}")
        print()
        if hasattr(message, 'refusal') and message.refusal:
            print(f"  模型拒绝原因：{message.refusal}")
            print()

        raise Exception(
            f"AI 返回了空内容（model={model}, finish_reason={finish_reason}）。"
            f"最常见原因是模型不是视觉模型，请检查 .env 配置"
        )

    print(f"[DEMO2]   AI 响应：{ai_text[:200]}{'...' if len(ai_text) > 200 else ''}")

    # ── 防御式：AI 返回的不是合法 JSON ──
    try:
        result = json.loads(ai_text)
    except json.JSONDecodeError as e:
        print()
        print(f"[DEMO2] ✗ AI 返回的不是合法 JSON：{e}")
        print(f"     原始内容：{ai_text}")
        raise Exception(f"AI 返回的不是合法 JSON：{ai_text[:200]}")

    if not result.get("found"):
        raise Exception(f"AI 没找到 '{element_desc}'")

    bbox_1000 = result["bbox"]
    if len(bbox_1000) != 4:
        raise Exception(f"AI 返回的 bbox 格式不对：{bbox_1000}")

    # ── 关键步骤：0-1000 → 真实像素 ──
    bbox_pixel = convert_bbox_to_pixel(bbox_1000, image_width, image_height)
    cx, cy = get_center(bbox_pixel)

    return (cx, cy), bbox_pixel, bbox_1000


# ─────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Demo 2: AI 找元素版（0-1000 归一化坐标）")
    print("=" * 60)

    # [1] 加载配置
    print("[DEMO2] 读配置 ...")
    config = load_config()
    print(f"[DEMO2]   Model: {config['model']}")
    print(f"[DEMO2]   Base URL: {config['base_url']}")
    api_key_masked = config["api_key"][:8] + "***"
    print(f"[DEMO2]   API Key: {api_key_masked}")

    # [2] 构造 AI 客户端
    ai_client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"]
    )

    # [3] 启动浏览器
    print("[DEMO2] 第 1 步：启动浏览器 ...")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()

    try:
        # [4] 打开网页
        print(f"[DEMO2] 第 2 步：打开 {TARGET_URL} ...")
        page.goto(TARGET_URL)
        page.wait_for_load_state("networkidle", timeout=10000)

        # [5] 截图
        print("[DEMO2] 第 3 步：截图 ...")
        img_bytes = page.screenshot()

        # 同时拿到三种格式：
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")  # 给 AI 用
        img_pil = Image.open(io.BytesIO(img_bytes))              # 本地处理
        img_w, img_h = img_pil.size                              # 真实尺寸
        print(f"[DEMO2]   截图尺寸：{img_w} x {img_h} 像素")
        print(f"[DEMO2]   base64 长度：{len(img_base64)} 字符")

        # [6] 让 AI 找元素
        print("[DEMO2] 第 4 步：调 AI 找元素 ...")
        (cx, cy), bbox_pixel, bbox_1000 = call_ai_to_find_element(
            ai_client, config["model"],
            img_base64, img_w, img_h,
            ELEMENT_DESC
        )

        # 详细打印坐标换算过程（让你理解每一步）
        print()
        print(f"[DEMO2]   ── 坐标换算过程 ──")
        print(f"[DEMO2]   AI 返回（0-1000）: {bbox_1000}")
        print(f"[DEMO2]   缩放因子:           x={img_w/1000:.3f}, y={img_h/1000:.3f}")
        print(f"[DEMO2]   还原成像素:         {bbox_pixel}")
        print(f"[DEMO2]   中心点:             ({cx:.0f}, {cy:.0f})")

        # [6.5] debug 模式：保存一张红框标注图
        if DEBUG:
            marked_path = OUTPUT_DIR / "ai_marked.png"
            # 在原图上画 AI 返回的像素 bbox
            debug_img = img_pil.copy()
            draw = ImageDraw.Draw(debug_img)
            draw.rectangle(bbox_pixel, outline="red", width=4)
            draw.text((bbox_pixel[0], max(bbox_pixel[1] - 25, 5)),
                      f"AI 框 ({ELEMENT_DESC})", fill="red")
            debug_img.save(marked_path)
            print(f"[DEMO2]   ✓ 已保存标注图：{marked_path}")

        # [7] 点击 + 输入
        print()
        print(f"[DEMO2] 第 5 步：在 ({cx:.0f}, {cy:.0f}) 点击 + 输入 '{INPUT_TEXT}' ...")
        page.mouse.click(cx, cy)
        time.sleep(0.3)
        page.keyboard.press("Control+a")
        time.sleep(0.05)
        page.keyboard.press("Delete")
        time.sleep(0.05)
        page.keyboard.type(INPUT_TEXT, delay=50)

        # [8] 截图（输入后）
        after_path = OUTPUT_DIR / "ai_after.png"
        page.screenshot(path=str(after_path))
        print(f"[DEMO2] 第 6 步：截图（输入后）→ {after_path}")

        print()
        print("=" * 60)
        print("[DEMO2] 完成！")
        print(f"  - 看效果：    {after_path}")
        if DEBUG:
            print(f"  - 看 AI 框：  {OUTPUT_DIR / 'ai_marked.png'}")
            print()
            print("  排查指引：")
            print("    - 红色框 ✓ 完整包住搜索框 = AI 找对了")
            print("    - 红色框 ❌ 偏到别处 = AI 找错了（描述换更具体的）")
            print("    - 没有红色框 = 元素没找到（描述换更宽泛的）")
        print("=" * 60)

    finally:
        print()
        print("[DEMO2] 3 秒后关闭浏览器 ...")
        time.sleep(3)
        browser.close()
        playwright.stop()


if __name__ == "__main__":
    main()