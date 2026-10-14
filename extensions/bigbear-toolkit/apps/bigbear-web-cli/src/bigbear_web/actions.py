# -*- coding: utf-8 -*-
"""Basic browser actions: click, input, scroll using Playwright"""
import time
import re
from typing import Union

from playwright.sync_api import Page, Mouse, Keyboard


class BrowserActions:
    """Basic browser actions handler using Playwright"""

    def __init__(self, page: Page):
        """
        Initialize actions handler

        Args:
            page: Playwright Page instance
        """
        self.page = page

    def click_at(self, x: float, y: float):
        """
        Click at specified coordinates

        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.page.mouse.click(x, y)

    def input_text(self, x: float, y: float, text: str):
        """
        点击坐标位置并输入文本

        Args:
            x: X坐标（先点击）
            y: Y坐标（先点击）
            text: 要输入的文本
        """
        # 点击以获得焦点
        self.page.mouse.click(x, y)
        time.sleep(0.1)

        # 先清空现有内容（Ctrl+A全选，然后Delete删除）
        self.page.keyboard.press("Control+a")
        time.sleep(0.05)
        self.page.keyboard.press("Delete")
        time.sleep(0.05)

        # 检测是否包含中文，中文使用 insert_text 方式
        if re.search(r'[一-鿿]', text):
            # 直接使用 insert_text 输入中文
            self.page.keyboard.insert_text(text)
            time.sleep(0.1)
        else:
            # 非中文内容直接使用键盘输入
            self.page.keyboard.type(text, delay=50)

    def scroll_down(self, clicks: int = 1):
        """
        Scroll down the page

        Args:
            clicks: Number of page down key presses
        """
        for _ in range(clicks):
            self.page.keyboard.press("PageDown")
            time.sleep(0.3)

    def scroll_up(self, clicks: int = 1):
        """
        Scroll up the page

        Args:
            clicks: Number of page up key presses
        """
        for _ in range(clicks):
            self.page.keyboard.press("PageUp")
            time.sleep(0.3)

    def scroll_left(self, clicks: int = 1):
        """
        Scroll left the page

        Args:
            clicks: Number of left arrow key presses
        """
        for _ in range(clicks):
            self.page.keyboard.press("ArrowLeft")
            time.sleep(0.3)

    def scroll_right(self, clicks: int = 1):
        """
        Scroll right the page

        Args:
            clicks: Number of right arrow key presses
        """
        for _ in range(clicks):
            self.page.keyboard.press("ArrowRight")
            time.sleep(0.3)

    def scroll_to_element(self, x: float, y: float, direction: str = "down", clicks: int = 3):
        """
        Scroll to element by dragging to focus first then scrolling

        Args:
            x: X coordinate in scroll region (safe area)
            y: Y coordinate in scroll region (safe area)
            direction: "down", "up", "left", "right"
            clicks: Number of scroll key presses
        """
        # 通过鼠标拖拽将焦点固定到区域
        center_x, center_y = x, y
        drag_distance = 100

        if direction == "down":
            start_x, start_y = center_x, center_y
            end_x, end_y = center_x, center_y - drag_distance
        elif direction == "up":
            start_x, start_y = center_x, center_y
            end_x, end_y = center_x, center_y + drag_distance
        elif direction == "left":
            start_x, start_y = center_x, center_y
            end_x, end_y = center_x + drag_distance, center_y
        elif direction == "right":
            start_x, start_y = center_x, center_y
            end_x, end_y = center_x - drag_distance, center_y
        else:
            start_x, start_y = center_x, center_y
            end_x, end_y = center_x, center_y

        # 1. 瞬移到起点 (steps=0 防止路过触发 hover)
        self.page.mouse.move(start_x, start_y, steps=0)

        # 2. 按下左键
        self.page.mouse.down()

        # 3. 瞬移到终点 (steps=0 不给浏览器反应时间)
        self.page.mouse.move(end_x, end_y, steps=0)

        # 4. 松开
        self.page.mouse.up()

        # 5. 清除选中
        self.page.evaluate("window.getSelection().removeAllRanges();")

        # 6. 等待一下
        self.page.wait_for_timeout(50)

        # 滚动
        for _ in range(clicks):
            if direction == "down":
                self.page.keyboard.press("PageDown")
            elif direction == "up":
                self.page.keyboard.press("PageUp")
            elif direction == "left":
                self.page.keyboard.press("ArrowLeft")
            elif direction == "right":
                self.page.keyboard.press("ArrowRight")
            self.page.wait_for_timeout(300)

    def maximize(self):
        """最大化浏览器窗口"""
        self.page.bring_to_front()
        self.page.viewportSize = None
        self.page.evaluate("""
            if (document.documentElement.requestFullscreen) {
                document.documentElement.requestFullscreen();
            } else if (document.documentElement.webkitRequestFullScreen) {
                document.documentElement.webkitRequestFullScreen();
            }
        """)

    def wait(self, seconds: float = 1):
        """Wait for page to load"""
        time.sleep(seconds)