# -*- coding: utf-8 -*-
"""
Demo 1: 固定坐标版（0 基础入门）

目标：熟悉「启动浏览器 → 打开网页 → 截图 → 点击 → 输入」基础链路
特点：搜索框坐标是写死的，不调 AI，最容易跑通

跑这个命令： python demo_hardcoded.py
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright


# ─────────────────────────────────────────────────────────────
# 配置：搜索框在屏幕上的坐标（写死的）
# ─────────────────────────────────────────────────────────────
# 这两个数字是「百度首页」上搜索框大概的中心位置
# 如果以后百度改版了，可能要改
SEARCH_BOX_X = 640
SEARCH_BOX_Y = 280

# 要输入的文本
INPUT_TEXT = "hello Playwright"

# 输出目录（截图存这里）
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def step_1_launch_browser():
    """启动 Chromium 浏览器"""
    print("[DEMO1] 第 1 步：启动浏览器 ...")
    playwright = sync_playwright().start()
    # headless=False：能看到浏览器窗口
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    return playwright, browser, page


def step_2_navigate(page, url):
    """让浏览器打开指定网址"""
    print(f"[DEMO1] 第 2 步：打开 {url} ...")
    page.goto(url)
    page.wait_for_load_state("networkidle", timeout=10000)


def step_3_screenshot_before(page):
    """截一张图（输入之前的状态）"""
    output_path = OUTPUT_DIR / "01_before.png"
    print(f"[DEMO1] 第 3 步：截图（输入前） → {output_path}")
    page.screenshot(path=str(output_path))
    return output_path


def step_4_click(page, x, y):
    """在屏幕坐标 (x, y) 处点击一下"""
    print(f"[DEMO1] 第 4 步：在坐标 ({x}, {y}) 点击搜索框 ...")
    page.mouse.click(x, y)
    time.sleep(0.5)


def step_5_input(page, text):
    """在焦点处输入文本"""
    print(f"[DEMO1] 第 5 步：输入文本 '{text}' ...")
    page.keyboard.press("Control+a")
    time.sleep(0.05)
    page.keyboard.press("Delete")
    time.sleep(0.05)
    page.keyboard.type(text, delay=50)


def step_6_screenshot_after(page):
    """再截一张图（输入之后的状态）"""
    output_path = OUTPUT_DIR / "02_after.png"
    print(f"[DEMO1] 第 6 步：截图（输入后） → {output_path}")
    page.screenshot(path=str(output_path))
    return output_path


def cleanup(playwright, browser):
    """关闭浏览器"""
    print("[DEMO1] 3 秒后自动关闭浏览器 ...")
    time.sleep(3)
    browser.close()
    playwright.stop()
    print("[DEMO1] 浏览器已关闭")


def main():
    print("=" * 60)
    print("Demo 1: 固定坐标版")
    print("=" * 60)

    playwright, browser, page = step_1_launch_browser()

    try:
        step_2_navigate(page, "https://www.baidu.com")
        step_3_screenshot_before(page)
        step_4_click(page, SEARCH_BOX_X, SEARCH_BOX_Y)
        step_5_input(page, INPUT_TEXT)
        step_6_screenshot_after(page)
        print("[DEMO1] 完成！请打开 output/02_after.png 查看效果")
    finally:
        cleanup(playwright, browser)


if __name__ == "__main__":
    main()