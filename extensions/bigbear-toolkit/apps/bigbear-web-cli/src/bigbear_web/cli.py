# -*- coding: utf-8 -*-
"""BigBear Web CLI - AI-powered browser control via Playwright CDP"""
import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple


def get_version():
    """Get package version dynamically from installed package"""
    try:
        from importlib.metadata import version
        return version("bigbear-web-cli")
    except Exception:
        return "unknown"


def load_config():
    """Load configuration from environment or .env file"""
    import dotenv
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        dotenv.load_dotenv(env_path)

    return {
        "api_key": os.getenv("WEB_AUTOMATION_AI_API_KEY", ""),
        "base_url": os.getenv("WEB_AUTOMATION_AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "model": os.getenv("WEB_AUTOMATION_AI_MODEL", "qwen3.6-flash-2026-04-16"),
        "user_data_dir": os.getenv("WEB_AUTOMATION_USER_DATA", ""),
    }


def get_browser(args, auto_launch: bool = True):
    """Connect to browser at specified CDP address"""
    from .browser import PlaywrightBrowser
    browser = PlaywrightBrowser.get_instance(headless=args.headless)
    port = args.port or 9222
    # Priority: command-line argument > environment variable > .env config
    cmd_user_data = getattr(args, 'user_data_dir', None)
    config = load_config()
    env_user_data = config.get("user_data_dir", "")
    user_data_dir = cmd_user_data if cmd_user_data else env_user_data if env_user_data else None
    browser.connect(debugger_address=f"127.0.0.1:{port}", port=port, auto_launch=auto_launch, user_data_dir=user_data_dir)
    return browser


def require_api_key():
    """Ensure AI_API_KEY is configured"""
    config = load_config()
    if not config["api_key"]:
        print("[FAIL] 错误: 请设置 AI_API_KEY 环境变量或在 .env 文件中配置")
        sys.exit(1)
    return config


class StepTimer:
    """简单耗时统计"""
    def __init__(self):
        self.times = {}

    def record(self, name: str, duration: float):
        self.times[name] = duration

    def print_stats(self, cmd_name: str):
        total = sum(self.times.values())
        print(f"\n{'='*50}")
        print(f"[STAT] {cmd_name} 命令耗时统计 (总计 {total:.3f}s)")
        print(f"{'='*50}")
        for step, duration in self.times.items():
            pct = duration / total * 100 if total > 0 else 0
            print(f"  - {step}: {duration:.3f}s ({pct:.1f}%)")
        print(f"{'='*50}\n")


def init_ai_command(args) -> Tuple:
    """
    初始化 AI 命令的公共步骤：配置检查、浏览器连接、截图

    Returns: (config, browser, ai, actions, timer, img_base64, original_image, dpr)
    """
    from .ai_control import AIControl
    from .actions import BrowserActions

    config = require_api_key()
    timer = StepTimer()

    t0 = time.time()
    browser = get_browser(args, auto_launch=False)
    timer.record('连接浏览器', time.time() - t0)

    ai = AIControl(config["api_key"], config["base_url"], config["model"])
    actions = BrowserActions(browser.page)

    t1 = time.time()
    img_base64, original_image, dpr = browser.get_screenshot(use_jpeg=True)
    timer.record('截图', time.time() - t1)

    return config, browser, ai, actions, timer, img_base64, original_image, dpr


def save_screenshot(browser, path: str, timer: StepTimer):
    """保存截图的公共逻辑"""
    t = time.time()
    img_base64, _, _ = browser.get_screenshot(use_jpeg=True)
    with open(path, "wb") as f:
        f.write(__import__('base64').b64decode(img_base64))
    timer.record('保存截图', time.time() - t)
    print(path)


def cmd_start(args):
    """Start or connect to browser"""
    try:
        browser = get_browser(args, auto_launch=True)
        print(f"[OK] Browser connected (port: {args.port or 9222})")
    except Exception as e:
        # 打印异常堆栈
        import traceback
        traceback.print_exc()

        print(f"[FAIL] Browser connection failed: {e}")
        sys.exit(1)


def cmd_navigate(args):
    """Navigate to URL"""
    from .actions import BrowserActions
    browser = get_browser(args, auto_launch=False)
    browser.navigate(args.url)
    # 自动最大化浏览器窗口
    actions = BrowserActions(browser.page)
    actions.maximize()
    print(f"[OK] 已打开网址: {args.url}，窗口已最大化")

    if args.screenshot:
        img_base64, _, _ = browser.get_screenshot(use_jpeg=True)
        with open(args.screenshot, "wb") as f:
            f.write(__import__('base64').b64decode(img_base64))
        print(args.screenshot)


def cmd_click(args):
    """Click on element using AI vision"""
    from .ai_control import AIControl

    config, browser, ai, actions, timer, img_base64, original_image, dpr = init_ai_command(args)
    debug = args.debug

    try:
        t2 = time.time()
        x, y = ai.find_element(img_base64, original_image, args.element, args.enhanced or "", debug=debug, dpr=dpr)
        timer.record('AI元素识别', time.time() - t2)

        t3 = time.time()
        actions.click_at(x, y)
        timer.record('点击', time.time() - t3)

        print(f"[OK] 已点击坐标: ({x:.1f}, {y:.1f})")

        if args.screenshot:
            save_screenshot(browser, args.screenshot, timer)

        if debug:
            timer.print_stats("click")

    except Exception as e:
        print(f"[FAIL] 点击失败: {e}")
        sys.exit(1)


def cmd_input(args):
    """Input text using AI vision"""
    from .ai_control import AIControl

    config, browser, ai, actions, timer, img_base64, original_image, dpr = init_ai_command(args)
    debug = args.debug

    try:
        t2 = time.time()
        x, y = ai.find_element(img_base64, original_image, args.element, args.enhanced or "", debug=debug, dpr=dpr)
        timer.record('AI元素识别', time.time() - t2)

        t3 = time.time()
        actions.input_text(x, y, args.text)
        timer.record('输入文本', time.time() - t3)

        print(f"[OK] 已在坐标 ({x:.1f}, {y:.1f}) 输入文本: {args.text}")

        if args.screenshot:
            save_screenshot(browser, args.screenshot, timer)

        if debug:
            timer.print_stats("input")

    except Exception as e:
        print(f"[FAIL] 输入失败: {e}")
        sys.exit(1)


def cmd_scroll(args):
    """Scroll the page"""
    from .ai_control import AIControl
    from .actions import BrowserActions

    direction = args.direction.lower()
    if direction not in ["up", "down", "left", "right"]:
        print(f"[FAIL] 无效方向: {direction}，使用 up/down/left/right")
        sys.exit(1)

    if args.region:
        # AI 识别区域并拖拽聚焦滚动
        config, browser, ai, _, timer, img_base64, original_image, _ = init_ai_command(args)
        debug = args.debug

        t2 = time.time()
        result = ai.get_content_ai(img_base64, original_image, args.region, debug=debug)
        timer.record('AI区域识别', time.time() - t2)

        bbox = result.get('bbox', [])
        if len(bbox) >= 4:
            x1, y1, x2, y2 = bbox
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            actions = BrowserActions(browser.page)
            actions.scroll_to_element(center_x, center_y, direction, args.count)
            print(f"[OK] 已滚动 {direction} {args.count} 次 (区域: {args.region})")
        else:
            print(f"[FAIL] 区域识别失败: {args.region}")
            sys.exit(1)
    else:
        # 无区域指定，使用纯键盘滚动
        browser = get_browser(args, auto_launch=False)
        actions = BrowserActions(browser.page)

        if direction == "down":
            actions.scroll_down(args.count)
        elif direction == "up":
            actions.scroll_up(args.count)
        elif direction == "left":
            actions.scroll_left(args.count)
        elif direction == "right":
            actions.scroll_right(args.count)
        print(f"[OK] 已滚动 {direction} {args.count} 次")

    if args.screenshot:
        save_screenshot(browser, args.screenshot, StepTimer())


def cmd_screenshot(args):
    """Take a screenshot"""
    browser = get_browser(args)

    img_base64, _, _ = browser.get_screenshot(use_jpeg=False)
    with open(args.output, "wb") as f:
        f.write(__import__('base64').b64decode(img_base64))
    print(args.output)


def cmd_close(args):
    """Close the current page/tab"""
    browser = get_browser(args)
    if browser.page:
        browser.page.close()
        print("[OK] 页面已关闭")
    else:
        print("[INFO] 没有打开的页面")


def cmd_get(args):
    """Get content from a specified region using AI vision (structured description)"""
    from .ai_control import AIControl

    config, browser, ai, _, timer, img_base64, original_image, _ = init_ai_command(args)
    debug = args.debug

    try:
        t2 = time.time()
        result = ai.describe_region_ai(img_base64, original_image, args.description, debug=debug)
        timer.record('AI内容描述', time.time() - t2)

        desc = result.get('description', {}) or {}

        def _fmt(value, fallback='无'):
            """对 description 字段做容错:None / 非 str 都 fallback"""
            if value is None:
                return fallback
            if isinstance(value, str):
                return value or fallback
            return str(value) if value else fallback

        def _fmt_icons(value):
            """icons 字段专门处理:list 拼接,空给'无',非 list fallback 到字符串"""
            if value is None:
                return '无'
            if isinstance(value, list):
                return ', '.join(str(x) for x in value) if value else '无'
            return str(value) if value else '无'

        layout = _fmt(desc.get('layout'))
        icons = _fmt_icons(desc.get('icons'))
        text = _fmt(desc.get('text'))
        intro = _fmt(desc.get('intro'))

        print("[OK] 区域描述:")
        print(f"  布局: {layout}")
        print(f"  图标: {icons}")
        print(f"  文字: {text}")
        print(f"  介绍: {intro}")

        if args.screenshot:
            # 没有 bbox 了 —— 仅保存原图供用户对照
            screenshot_path = args.screenshot
            browser.page.screenshot(path=screenshot_path)
            print(f"[OK] 截图已保存: {screenshot_path}")

        if debug:
            timer.print_stats("get")

    except Exception as e:
        print(f"[FAIL] 获取内容失败: {e}")
        sys.exit(1)


def cmd_batch(args):
    """Batch input/click using AI vision - parallel element recognition"""
    from .ai_control import AIControl

    config, browser, ai, actions, timer, img_base64, original_image, dpr = init_ai_command(args)
    debug = args.debug

    # 解析每个指令: click 描述 | input 描述::值
    instructions = []
    i = 0
    while i < len(args.instructions):
        op = args.instructions[i].strip().lower()
        if op not in ("click", "input"):
            print(f"[WARN] 未知操作: {op}，跳过")
            i += 1
            continue
        if op == "click":
            if i + 1 >= len(args.instructions):
                print(f"[WARN] click 缺少描述参数")
                i += 1
                continue
            element = args.instructions[i + 1].strip()
            value = ""
            i += 2
        else:  # input
            if i + 1 >= len(args.instructions):
                print(f"[WARN] input 缺少描述参数")
                i += 1
                continue
            rest = args.instructions[i + 1].strip()
            if "::" in rest:
                elem_end = rest.index("::")
                element = rest[:elem_end].strip()
                value = rest[elem_end + 2:].strip()
            else:
                element = rest
                value = ""
            i += 2

        instructions.append((op, element, value))

    if not instructions:
        print("[FAIL] 没有有效的指令")
        sys.exit(1)

    # 构建元素列表: [(element_info, enhanced), ...]
    elements = [(instr[1], "") for instr in instructions]

    # 并行AI识别
    t2 = time.time()
    results = ai.find_element_batch(img_base64, original_image, elements, debug=debug, dpr=dpr)
    timer.record('AI并行识别', time.time() - t2)

    success_count = 0
    fail_count = 0

    # 逐个执行操作
    t3 = time.time()
    for i, (op, element, value) in enumerate(instructions):
        if i < len(results):
            elem_result = results[i]
            if len(elem_result) >= 3 and elem_result[1] is not None and elem_result[2] is not None:
                _, x, y = elem_result
                if op == "click":
                    actions.click_at(x, y)
                    print(f"[OK] click: {element} -> ({x:.1f}, {y:.1f})")
                elif op == "input":
                    actions.input_text(x, y, value)
                    print(f"[OK] input: {element} = {value} -> ({x:.1f}, {y:.1f})")
                success_count += 1
            else:
                print(f"[FAIL] {op}: {element} - 识别失败")
                fail_count += 1
        else:
            print(f"[FAIL] {op}: {element} - 无结果")
            fail_count += 1
        time.sleep(0.5)
    timer.record('执行操作', time.time() - t3)

    print(f"\n[STAT] batch 完成: 成功 {success_count}, 失败 {fail_count}")

    if args.screenshot:
        save_screenshot(browser, args.screenshot, timer)

    if debug:
        timer.print_stats("batch")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="BigBear Web CLI - AI-powered browser control via Playwright CDP",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--headless", action="store_true", help="运行在无头模式")
    parser.add_argument("--port", "-p", type=int, default=9222, help="浏览器端口 (默认: 9222)")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--version", action="version", version=f"bigbear-web-cli {get_version()}")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # start command
    start_parser = subparsers.add_parser("start", help="启动/连接浏览器")
    start_parser.add_argument("--user-data-dir", "-u", type=str, help="用户数据目录（用于保持会话、Cookie 等）")

    # navigate command
    nav_parser = subparsers.add_parser("navigate", help="打开网址")
    nav_parser.add_argument("url", help="目标网址")
    nav_parser.add_argument("--screenshot", "-s", type=str, help="保存截图路径")

    # click command
    click_parser = subparsers.add_parser("click", help="AI点击元素")
    click_parser.add_argument("element", help="元素描述")
    click_parser.add_argument("--enhanced", "-e", type=str, help="元素查找加强说明")
    click_parser.add_argument("--screenshot", "-s", type=str, help="保存截图路径")

    # input command
    input_parser = subparsers.add_parser("input", help="AI输入文本")
    input_parser.add_argument("element", help="元素描述")
    input_parser.add_argument("text", help="要输入的文本")
    input_parser.add_argument("--enhanced", "-e", type=str, help="元素查找加强说明")
    input_parser.add_argument("--screenshot", "-s", type=str, help="保存截图路径")

    # scroll command
    scroll_parser = subparsers.add_parser("scroll", help="滚动页面")
    scroll_parser.add_argument("direction", choices=["up", "down", "left", "right"], help="滚动方向")
    scroll_parser.add_argument("--region", type=str, help="滚动区域描述，AI识别区域后聚焦滚动")
    scroll_parser.add_argument("--count", "-c", type=int, default=1, help="滚动次数 (默认1)")
    scroll_parser.add_argument("--screenshot", "-s", type=str, help="保存截图路径")

    # screenshot command
    screenshot_parser = subparsers.add_parser("screenshot", help="截图")
    screenshot_parser.add_argument("output", help="截图保存路径")

    # close command
    close_parser = subparsers.add_parser("close", help="关闭浏览器")

    # batch command
    batch_parser = subparsers.add_parser("batch", help="批量并行输入/点击")
    batch_parser.add_argument("instructions", nargs="+", help="批量指令，格式: click 描述 | input 描述::值 ...")
    batch_parser.add_argument("--screenshot", "-s", type=str, help="操作后保存截图路径")

    # get command
    get_parser = subparsers.add_parser("get", help="获取指定区域内容描述(布局/图标/文字/介绍,不含坐标)")
    get_parser.add_argument("description", help="区域描述，如'标题下方的正文'")
    get_parser.add_argument("--screenshot", "-s", type=str, help="保存原图路径(不加红框——本命令不返回坐标)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate command handler
    if args.command == "start":
        cmd_start(args)
    elif args.command == "navigate":
        cmd_navigate(args)
    elif args.command == "click":
        cmd_click(args)
    elif args.command == "input":
        cmd_input(args)
    elif args.command == "scroll":
        cmd_scroll(args)
    elif args.command == "screenshot":
        cmd_screenshot(args)
    elif args.command == "close":
        cmd_close(args)
    elif args.command == "get":
        cmd_get(args)
    elif args.command == "batch":
        cmd_batch(args)


if __name__ == "__main__":
    main()