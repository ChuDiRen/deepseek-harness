# -*- coding: utf-8 -*-
"""Browser connection management via Playwright CDP"""
import io
import base64
import subprocess
import platform
import time
import sys
from typing import Optional

import requests
from PIL import Image
from loguru import logger
from playwright.sync_api import sync_playwright, Browser, Page

# 配置日志级别，默认只输出 WARNING 及以上
logger.remove()
logger.add(sys.stderr, level="WARNING", format="{time:HH:mm:ss} | {level} | {message}", colorize=False)


class PlaywrightBrowser:
    """Browser connection manager using Playwright CDP"""

    _instance = None

    def __init__(self, debugger_address: str = None, headless: bool = False):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.debugger_address = debugger_address
        self.headless = headless
        self._owns_browser = debugger_address is None
        self._port = 9222

    @classmethod
    def get_instance(cls, debugger_address: str = None, headless: bool = False):
        """Get or create a singleton browser instance"""
        if cls._instance is not None:
            try:
                if cls._instance.page is not None and not cls._instance.page.is_closed():
                    cls._instance.page.title()
                    if cls._instance.playwright is not None:
                        return cls._instance
            except Exception:
                pass
            try:
                cls._instance._close_sync()
            except Exception:
                pass
            cls._instance = None

        cls._instance = cls(debugger_address, headless)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance"""
        if cls._instance is not None:
            try:
                cls._instance._close_sync()
            except:
                pass
        cls._instance = None

    def _get_cdp_url(self, address: str) -> str:
        """Get CDP WebSocket URL from debugging address"""
        resp = requests.get(f"http://{address}/json/version", timeout=5)
        return resp.json()["webSocketDebuggerUrl"]

    def connect(self, debugger_address: str = None, port: int = 9222, auto_launch: bool = True, user_data_dir: str = None) -> Page:
        """Connect to browser via CDP

        Args:
            debugger_address: CDP 调试地址
            port: 端口号
            auto_launch: 是否自动启动浏览器
            user_data_dir: 用户数据目录（用于保持会话、Cookie 等）
        """
        if debugger_address:
            self.debugger_address = debugger_address
        self._port = port
        self._user_data_dir = user_data_dir

        if self.page is not None and not self.page.is_closed():
            try:
                self.page.title()
                return self.page
            except Exception:
                self.page = None

        if auto_launch:
            return self._check_and_relaunch_if_needed(port)

        try:
            return self._connect_sync()
        except Exception as e:
            raise

    def verify_browser_scale(self) -> bool:
        """检测浏览器DPI缩放设置是否符合要求"""
        try:
            dpr = self.page.evaluate("window.devicePixelRatio")
            logger.debug("检测到 devicePixelRatio: {}", dpr)
            if dpr != 1:
                logger.warning("浏览器DPI缩放不等于1，当前为 {}，可能导致坐标计算错误", dpr)
                return False
            return True
        except Exception as e:
            logger.warning("无法获取 devicePixelRatio: {}", e)
            return False

    def _check_and_relaunch_if_needed(self, port: int = 9222) -> Page:
        """检查浏览器设置，如有需要则重启"""
        try:
            page = self._connect_sync()
        except Exception as e:
            logger.info("未检测到运行中的浏览器，正在启动新浏览器...")
            self._launch_and_disconnect(port=port, user_data_dir=self._user_data_dir)
            page = self.page
            if not self.verify_browser_scale():
                logger.warning("检测到浏览器DPI设置不符合要求，尝试重启...")
                self._close_sync()
                time.sleep(1)
                self._launch_and_disconnect(port=port, user_data_dir=self._user_data_dir)
                page = self.page
                if self.verify_browser_scale():
                    logger.info("浏览器已重启，DPI设置正确")
                else:
                    logger.error("重启后仍无法确认DPI设置正确，请手动关闭不符合要求的Chrome后重试")
            return page

        if not self.verify_browser_scale():
            logger.warning("检测到浏览器DPI设置不符合要求，尝试重启...")
            self._close_sync()
            time.sleep(1)
            self._launch_and_disconnect(port=port, user_data_dir=self._user_data_dir)
            page = self.page
            if self.verify_browser_scale():
                logger.info("浏览器已重启，DPI设置正确")
            else:
                logger.error("重启后仍无法确认DPI设置正确，请手动关闭不符合要求的Chrome后重试")
        return page

    def get_dpr(self) -> float:
        """获取当前浏览器的 devicePixelRatio"""
        try:
            return self.page.evaluate("window.devicePixelRatio")
        except Exception as e:
            logger.warning("无法获取 devicePixelRatio: {}", e)
            return 1.0

    def _connect_sync(self):
        """Synchronous connection"""
        self.playwright = sync_playwright().start()
        cdp_url = self._get_cdp_url(self.debugger_address or f"127.0.0.1:{self._port}")
        self.browser = self.playwright.chromium.connect_over_cdp(cdp_url)
        if not self.browser.contexts:
            self.page = self.browser.new_page()
        else:
            ctx = self.browser.contexts[0]
            self.page = ctx.pages[0] if ctx.pages else ctx.new_page()
        self.page.wait_for_load_state('load')
        self.page.title()
        return self.page

    def _launch_and_disconnect(self, port: int = 9222, user_data_dir: str = None):
        """Launch browser using subprocess, then connect via CDP"""
        chrome_paths = {
            "Windows": "chrome.exe",
            "Darwin": "Google Chrome",
            "Linux": "google-chrome"
        }

        chrome = chrome_paths.get(platform.system(), "google-chrome")

        cmd = [
            chrome,
            f"--remote-debugging-port={port}",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--high-dpi-support=1",
            "--force-device-scale-factor=1",
        ]

        if self.headless:
            cmd.append("--headless")

        if user_data_dir:
            cmd.append(f"--user-data-dir={user_data_dir}")

        # Launch browser as separate process (keeps running after python exits)
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

        # Connect to the running browser via CDP
        cdp_url = self._get_cdp_url(f"127.0.0.1:{port}")
        self.browser = self.playwright.chromium.connect_over_cdp(cdp_url)
        if not self.browser.contexts:
            self.page = self.browser.new_page()
        else:
            ctx = self.browser.contexts[0]
            self.page = ctx.pages[0] if ctx.pages else ctx.new_page()
        self.page.wait_for_load_state('load')
        self.page.title()

    def get_screenshot(self, timeout: int = 30000, use_jpeg: bool = True) -> tuple:
        """Get screenshot as base64, PIL Image and DPR

        Args:
            timeout: 截图超时时间(ms)，默认30秒
            use_jpeg: 是否使用JPEG格式（更快），默认True
        """
        if not self.page or self.page.is_closed():
            raise Exception("Browser not connected")
        screenshot_options = {
            'timeout': timeout,
            'animations': 'disabled',
            'type': 'jpeg' if use_jpeg else 'png',
        }
        if use_jpeg:
            screenshot_options['quality'] = 85
        img_bytes = self.page.screenshot(**screenshot_options)
        img_base64_str = base64.b64encode(img_bytes).decode('ascii')
        original_image = Image.open(io.BytesIO(img_bytes))
        viewport_size = self.page.viewport_size
        dpr = self.get_dpr()
        logger.debug("截图信息 - PIL尺寸: {}x{}, Viewport: {}, DPR: {}, 字节数: {}",
                    original_image.size[0], original_image.size[1], viewport_size, dpr, len(img_bytes))
        return img_base64_str, original_image, dpr

    def navigate(self, url: str):
        """Navigate to URL"""
        if not self.page or self.page.is_closed():
            raise Exception("Browser not connected")
        self.page.goto(url)

    def is_connected(self) -> bool:
        """检查浏览器连接是否正常"""
        try:
            if self.page and not self.page.is_closed():
                self.page.title()
                return self.playwright is not None
        except Exception:
            pass
        return False

    def _close_sync(self):
        """Synchronous close"""
        try:
            if self.page and not self.page.is_closed():
                self.page.close()
        except Exception:
            pass
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

        self.page = None
        self.browser = None
        self.playwright = None
        PlaywrightBrowser._instance = None

    def close(self):
        """Close the browser connection"""
        self._close_sync()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
