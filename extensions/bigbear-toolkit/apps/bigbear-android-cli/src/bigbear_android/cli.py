# -*- coding: utf-8 -*-
"""BigBear Android CLI - AI-powered Android device control via adb commands"""
import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional, Tuple


def get_version():
    """Get package version dynamically"""
    try:
        from importlib.metadata import version
        return version("bigbear-android-cli")
    except Exception:
        return "unknown"


def _load_cwd_env():
    """仅加载执行命令时当前工作目录下的 .env。"""
    import dotenv

    env_path = Path.cwd() / ".env"
    if not env_path.is_file():
        return None

    dotenv.load_dotenv(dotenv_path=env_path, override=False)
    return env_path


def load_config():
    """从当前进程环境读取 AI 配置。"""
    return {
        "api_key": os.getenv("ANDROID_AI_API_KEY", ""),
        "base_url": os.getenv("ANDROID_AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "model": os.getenv("ANDROID_AI_MODEL", "qwen-vl-max"),
    }


def get_adb(args) -> "ADBManager":
    """获取 ADBManager 单例，初始化并选择设备"""
    from .adb import ADBManager
    adb = ADBManager.get_instance()
    serial = None
    if hasattr(args, "serial") and args.serial:
        serial = args.serial
    adb.select_device(serial)
    return adb


def get_actions(args) -> Tuple["ADBManager", "AndroidActions"]:
    """获取 ADBManager 和 AndroidActions 实例"""
    from .actions import AndroidActions
    adb = get_adb(args)
    actions = AndroidActions(adb)
    return adb, actions


def require_api_key():
    """确保 AI API_KEY 已配置（仅 AI 命令需要）"""
    config = load_config()
    if not config["api_key"]:
        print("[FAIL] 错误: 请设置 ANDROID_AI_API_KEY 环境变量或在 .env 文件中配置")
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
    """初始化 AI 命令的公共步骤：API 检查、设备连接、截图"""
    from .ai_control import AIControl

    config = require_api_key()
    timer = StepTimer()

    t0 = time.time()
    adb = get_adb(args)
    actions_tuple = None  # actions 由调用方创建
    timer.record('连接设备', time.time() - t0)

    ai = AIControl(config["api_key"], config["base_url"], config["model"])

    t1 = time.time()
    img_base64, original_image = adb.screencap_base64(use_jpeg=True)
    timer.record('截图', time.time() - t1)

    return config, adb, ai, timer, img_base64, original_image


def save_screenshot(adb, path: str, timer: StepTimer):
    """保存截图的公共逻辑"""
    t = time.time()
    img_base64, _ = adb.screencap_base64(use_jpeg=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(img_base64))
    timer.record('保存截图', time.time() - t)
    print(path)


# =============================================================================
# 命令实现
# =============================================================================

def cmd_devices(args):
    """列出所有 adb 设备"""
    from .adb import ADBManager
    adb = ADBManager.get_instance()
    try:
        devices = adb.list_devices()
    except Exception as e:
        print(f"[FAIL] 获取设备列表失败: {e}")
        sys.exit(1)

    if not devices:
        print("[INFO] 未检测到任何设备。请检查 USB 连接和调试授权。")
        return

    print(f"[OK] 检测到 {len(devices)} 个设备:")
    print(f"{'SERIAL':<30} {'STATE':<10} {'MODEL':<20} USB")
    print("-" * 80)
    for dev in devices:
        print(f"{dev['serial']:<30} {dev['state']:<10} {dev['model']:<20} {dev['usb']}")


def cmd_start(args):
    """连接/选择设备"""
    try:
        adb = get_adb(args)
        serial = adb.device_serial
        w, h = adb.get_screen_size(refresh=True)
        print(f"[OK] 已选择设备: {serial} (屏幕: {w}x{h})")
    except Exception as e:
        print(f"[FAIL] 设备连接失败: {e}")
        sys.exit(1)


def cmd_launch(args):
    """启动应用"""
    from .actions import AndroidActions
    adb, actions = get_actions(args)
    try:
        actions.launch_app(args.package, args.activity)
        time.sleep(0.5)
        print(f"[OK] 已启动应用: {args.package}"
              + (f"/{args.activity}" if args.activity else ""))
    except Exception as e:
        print(f"[FAIL] 启动失败: {e}")
        sys.exit(1)


def cmd_stop(args):
    """强制停止应用"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    try:
        actions.stop_app(args.package)
        print(f"[OK] 已停止应用: {args.package}")
    except Exception as e:
        print(f"[FAIL] 停止失败: {e}")
        sys.exit(1)


def cmd_click(args):
    """AI 点击元素"""
    from .actions import AndroidActions

    config, adb, ai, timer, img_base64, original_image = init_ai_command(args)
    debug = args.debug
    actions = AndroidActions(adb)

    try:
        t2 = time.time()
        x, y = ai.find_element(img_base64, original_image, args.element, debug=debug)
        timer.record('AI元素识别', time.time() - t2)

        t3 = time.time()
        actions.click_at(x, y)
        timer.record('点击', time.time() - t3)

        print(f"[OK] 已点击坐标: ({x:.1f}, {y:.1f})")

        if args.screenshot:
            save_screenshot(adb, args.screenshot, timer)

        if debug:
            timer.print_stats("click")

    except Exception as e:
        print(f"[FAIL] 点击失败: {e}")
        sys.exit(1)


def cmd_click_at(args):
    """无 AI 原始坐标点击"""
    from .adb import tap
    try:
        tap(serial=getattr(args, "serial", None), x=args.x, y=args.y)
    except Exception as e:
        print(f"[FAIL] 点击失败: {e}")
        sys.exit(1)


def cmd_input_at(args):
    """无 AI 原始坐标输入：先点击坐标聚焦，再输入文本"""
    _, actions = get_actions(args)
    try:
        actions.input_text(args.x, args.y, args.text)
        print(f"[OK] 已在坐标 ({args.x}, {args.y}) 输入文本: {args.text}")
    except Exception as e:
        print(f"[FAIL] 输入失败: {e}")
        sys.exit(1)


def cmd_input(args):
    """AI 输入文本"""
    from .actions import AndroidActions

    config, adb, ai, timer, img_base64, original_image = init_ai_command(args)
    debug = args.debug
    actions = AndroidActions(adb)

    try:
        t2 = time.time()
        x, y = ai.find_element(img_base64, original_image, args.element, debug=debug)
        timer.record('AI元素识别', time.time() - t2)

        t3 = time.time()
        actions.input_text(x, y, args.text)
        timer.record('输入文本', time.time() - t3)

        print(f"[OK] 已在坐标 ({x:.1f}, {y:.1f}) 输入文本: {args.text}")

        if args.screenshot:
            save_screenshot(adb, args.screenshot, timer)

        if debug:
            timer.print_stats("input")

    except Exception as e:
        print(f"[FAIL] 输入失败: {e}")
        sys.exit(1)


def cmd_pinch(args):
    """双指缩小（pinch / zoom out）"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    try:
        actions.pinch(args.x, args.y, args.scale, args.duration)
        print(f"[OK] 已在 ({args.x}, {args.y}) 双指缩小 (scale={args.scale}, duration={args.duration}ms)")
    except Exception as e:
        print(f"[FAIL] pinch 失败: {e}")
        sys.exit(1)


def cmd_zoom(args):
    """双指放大（zoom / zoom in）"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    try:
        actions.zoom(args.x, args.y, args.scale, args.duration)
        print(f"[OK] 已在 ({args.x}, {args.y}) 双指放大 (scale={args.scale}, duration={args.duration}ms)")
    except Exception as e:
        print(f"[FAIL] zoom 失败: {e}")
        sys.exit(1)


def cmd_longpress(args):
    """AI 长按元素"""
    from .actions import AndroidActions

    config, adb, ai, timer, img_base64, original_image = init_ai_command(args)
    debug = args.debug
    actions = AndroidActions(adb)
    duration = args.duration or 1000

    try:
        t2 = time.time()
        x, y = ai.find_element(img_base64, original_image, args.element, debug=debug)
        timer.record('AI元素识别', time.time() - t2)

        t3 = time.time()
        actions.long_press(x, y, duration)
        timer.record('长按', time.time() - t3)

        print(f"[OK] 已在坐标 ({x:.1f}, {y:.1f}) 长按 {duration}ms")

        if args.screenshot:
            save_screenshot(adb, args.screenshot, timer)

        if debug:
            timer.print_stats("longpress")

    except Exception as e:
        print(f"[FAIL] 长按失败: {e}")
        sys.exit(1)


def cmd_swipe(args):
    """滑动（带 AI 区域识别）"""
    from .actions import AndroidActions

    direction = args.direction.lower()
    if direction not in ["up", "down", "left", "right"]:
        print(f"[FAIL] 无效方向: {direction}，使用 up/down/left/right")
        sys.exit(1)

    if args.region:
        # AI 识别区域后聚焦滑动
        config, adb, ai, timer, img_base64, original_image = init_ai_command(args)
        debug = args.debug

        t2 = time.time()
        result = ai.get_content_ai(img_base64, original_image, args.region, debug=debug)
        timer.record('AI区域识别', time.time() - t2)

        bbox = result.get('bbox', [])
        if len(bbox) >= 4:
            x1, y1, x2, y2 = bbox
            actions = AndroidActions(adb)
            actions.swipe_in_region((x1, y1, x2, y2), direction, args.distance)
            print(f"[OK] 已在区域 {bbox} 内向 {direction} 滑动")
        else:
            print(f"[FAIL] 区域识别失败: {args.region}")
            sys.exit(1)
    else:
        # 整屏滑动
        adb, actions = get_actions(args)
        if direction == "down":
            actions.swipe_down(args.count, args.distance)
        elif direction == "up":
            actions.swipe_up(args.count, args.distance)
        elif direction == "left":
            actions.swipe_left(args.count, args.distance)
        elif direction == "right":
            actions.swipe_right(args.count, args.distance)
        print(f"[OK] 已向 {direction} 滑动 {args.count} 次")

    if args.screenshot:
        save_screenshot(adb, args.screenshot, StepTimer())


def cmd_swipe_to(args):
    """显式坐标滑动"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    duration = args.duration or 500
    try:
        actions.swipe(
            args.x1, args.y1, args.x2, args.y2, duration,
        )
        print(f"[OK] 已从 ({args.x1}, {args.y1}) 滑动至 ({args.x2}, {args.y2})，时长 {duration}ms")
    except Exception as e:
        print(f"[FAIL] 滑动失败: {e}")
        sys.exit(1)


def cmd_keyevent(args):
    """按键"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    code = args.code
    try:
        # 尝试解析为整数，否则按别名
        if code.isdigit():
            actions.keyevent(int(code))
        else:
            actions.keyevent(code)
        print(f"[OK] 已发送按键: {code}")
    except Exception as e:
        print(f"[FAIL] 按键失败: {e}")
        sys.exit(1)


def cmd_screenshot(args):
    """截图"""
    adb = get_adb(args)
    try:
        img_base64, _ = adb.screencap_base64(use_jpeg=False)
        with open(args.output, "wb") as f:
            f.write(base64.b64decode(img_base64))
        print(args.output)
    except Exception as e:
        print(f"[FAIL] 截图失败: {e}")
        sys.exit(1)


def cmd_close(args):
    """回到桌面（等同 press_home）"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    actions.go_home()
    print("[OK] 已回到桌面")


def cmd_get(args):
    """AI 获取指定区域内容描述(结构化:布局/图标/文字/介绍)"""
    config, adb, ai, timer, img_base64, original_image = init_ai_command(args)
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
            img_base64_to_save, _ = adb.screencap_base64(use_jpeg=True)
            with open(args.screenshot, "wb") as f:
                f.write(base64.b64decode(img_base64_to_save))
            print(f"[OK] 截图已保存: {args.screenshot}")

        if debug:
            timer.print_stats("get")

    except Exception as e:
        print(f"[FAIL] 获取内容失败: {e}")
        sys.exit(1)


def cmd_batch(args):
    """批量并行输入/点击"""
    from .actions import AndroidActions

    config, adb, ai, timer, img_base64, original_image = init_ai_command(args)
    debug = args.debug
    actions = AndroidActions(adb)

    # 解析每个指令: click 描述 | input 描述::值
    instructions = []
    i = 0
    while i < len(args.instructions):
        op = args.instructions[i].strip().lower()
        if op not in ("click", "input", "longpress"):
            print(f"[WARN] 未知操作: {op}，跳过")
            i += 1
            continue
        if op == "click" or op == "longpress":
            if i + 1 >= len(args.instructions):
                print(f"[WARN] {op} 缺少描述参数")
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

    # 仅 click/longpress 需要 AI 识别，input 已含 value
    elements_to_find = [
        instr[1] for instr in instructions if instr[0] in ("click", "longpress")
    ]

    # 批量 AI 识别
    t2 = time.time()
    results = []
    if elements_to_find:
        results = ai.find_element_batch(img_base64, original_image, elements_to_find, debug=debug)
    timer.record('AI并行识别', time.time() - t2)

    # 构建 name -> (x, y) 映射
    coord_map = {r[0]: (r[1], r[2]) for r in results}

    success_count = 0
    fail_count = 0

    t3 = time.time()
    for op, element, value in instructions:
        if op in ("click", "longpress"):
            if element in coord_map and coord_map[element][0] is not None:
                x, y = coord_map[element]
                if op == "click":
                    actions.click_at(x, y)
                    print(f"[OK] click: {element} -> ({x:.1f}, {y:.1f})")
                else:
                    actions.long_press(x, y, 1000)
                    print(f"[OK] longpress: {element} -> ({x:.1f}, {y:.1f})")
                success_count += 1
            else:
                print(f"[FAIL] {op}: {element} - 识别失败")
                fail_count += 1
        elif op == "input":
            # input 需要先点击（AI 识别输入框位置）— 简化为屏幕中央
            # 注：批量 input 当前以屏幕中心为点击点，更精确的做法是单独 AI 识别
            try:
                w, h = adb.get_screen_size()
                actions.input_text(w // 2, h // 2, value)
                print(f"[OK] input: {value} -> (屏幕中心 {w//2}, {h//2})")
                success_count += 1
            except Exception as e:
                print(f"[FAIL] input: {value} - {e}")
                fail_count += 1
        time.sleep(0.5)
    timer.record('执行操作', time.time() - t3)

    print(f"\n[STAT] batch 完成: 成功 {success_count}, 失败 {fail_count}")

    if args.screenshot:
        save_screenshot(adb, args.screenshot, timer)

    if debug:
        timer.print_stats("batch")


def cmd_shell(args):
    """adb shell 透传"""
    from .adb import ADBManager
    adb = ADBManager.get_instance()
    serial = args.serial if hasattr(args, "serial") and args.serial else None
    adb.select_device(serial)
    try:
        rc, stdout, stderr = adb.shell(*args.cmd)
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)
        if rc != 0:
            sys.exit(rc)
    except Exception as e:
        print(f"[FAIL] adb shell 执行失败: {e}")
        sys.exit(1)


def cmd_dump_ui(args):
    """UI 层次 dump（XML）"""
    from .adb import ADBManager
    adb = ADBManager.get_instance()
    serial = args.serial if hasattr(args, "serial") and args.serial else None
    adb.select_device(serial)
    try:
        output_path = adb.dump_ui(args.output)
        print(f"[OK] UI 层次已保存: {output_path}")
    except Exception as e:
        print(f"[FAIL] dump-ui 失败: {e}")
        sys.exit(1)


def cmd_appinfo(args):
    """应用信息"""
    from .adb import ADBManager
    adb = ADBManager.get_instance()
    serial = args.serial if hasattr(args, "serial") and args.serial else None
    adb.select_device(serial)
    try:
        info = adb.appinfo(args.package)
        print(info)
    except Exception as e:
        print(f"[FAIL] 获取应用信息失败: {e}")
        sys.exit(1)


def cmd_current_app(args):
    """获取当前前台应用（package + activity）"""
    try:
        adb = get_adb(args)
        info = adb.get_current_app()
        if args.format == "json":
            print(json.dumps(info, ensure_ascii=False))
        else:
            # 默认文本：单行 "package/activity"（activity 为空时省略 /）
            line = info["package"]
            if info.get("activity"):
                line = f"{line}/{info['activity']}"
            print(line)
    except Exception as e:
        print(f"[FAIL] 获取当前应用失败: {e}")
        sys.exit(1)


def cmd_wake(args):
    """唤醒屏幕"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    actions.wake_screen()
    print("[OK] 屏幕已唤醒")


def cmd_sleep(args):
    """休眠屏幕"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    actions.sleep_screen()
    print("[OK] 屏幕已休眠")


def cmd_recents(args):
    """打开最近任务列表（应用快速切换）"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    actions.open_recents()
    print("[OK] 已打开最近任务列表")


def cmd_notifications(args):
    """下拉通知栏"""
    from .actions import AndroidActions
    _, actions = get_actions(args)
    actions.open_notifications()
    print("[OK] 已下拉通知栏")


# =============================================================================
# argparse 入口
# =============================================================================

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="BigBear Android CLI - AI-powered Android device control via adb commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("-s", "--serial", type=str, help="设备序列号（默认首个 device）")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--version", action="version", version=f"bigbear-android-cli {get_version()}")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # devices
    subparsers.add_parser("devices", help="列出所有 adb 设备")

    # start
    subparsers.add_parser("start", help="连接/选择设备")

    # launch
    launch_parser = subparsers.add_parser("launch", help="启动应用")
    launch_parser.add_argument("package", help="应用包名")
    launch_parser.add_argument("activity", nargs="?", help="Activity 名（可选）")

    # stop
    stop_parser = subparsers.add_parser("stop", help="停止应用")
    stop_parser.add_argument("package", help="应用包名")

    # click
    click_parser = subparsers.add_parser("click", help="AI 点击元素")
    click_parser.add_argument("element", help="元素描述")
    click_parser.add_argument("--screenshot", "-s", type=str, help="保存截图路径")

    # click-at（无 AI 原始坐标点击）
    click_at_parser = subparsers.add_parser("click-at", help="点击原始 (x, y) 坐标（无 AI）")
    click_at_parser.add_argument("x", type=int, help="X 坐标")
    click_at_parser.add_argument("y", type=int, help="Y 坐标")

    # input-at (raw coordinates input, no AI)
    input_at_parser = subparsers.add_parser("input-at", help="在原始 (x, y) 坐标聚焦后输入文本（无 AI）")
    input_at_parser.add_argument("x", type=int, help="X 坐标")
    input_at_parser.add_argument("y", type=int, help="Y 坐标")
    input_at_parser.add_argument("text", help="要输入的文本")

    # input
    input_parser = subparsers.add_parser("input", help="AI 输入文本")
    input_parser.add_argument("element", help="元素描述")
    input_parser.add_argument("text", help="要输入的文本")
    input_parser.add_argument("--screenshot", "-s", type=str, help="保存截图路径")

    # longpress
    longpress_parser = subparsers.add_parser("longpress", help="AI 长按元素")
    longpress_parser.add_argument("element", help="元素描述")
    longpress_parser.add_argument("--duration", "-d", type=int, default=1000, help="按住时长(ms)")
    longpress_parser.add_argument("--screenshot", "-s", type=str, help="保存截图路径")

    # swipe
    swipe_parser = subparsers.add_parser("swipe", help="滑动")
    swipe_parser.add_argument("direction", choices=["up", "down", "left", "right"], help="方向")
    swipe_parser.add_argument("--region", type=str, help="滑动区域描述（AI 识别）")
    swipe_parser.add_argument("--count", "-c", type=int, default=1, help="滑动次数")
    swipe_parser.add_argument("--distance", type=float, default=0.6, help="滑动距离比例 0.1~1.0")
    swipe_parser.add_argument("--screenshot", "-s", type=str, help="保存截图路径")

    # swipe-to
    swipe_to_parser = subparsers.add_parser("swipe-to", help="显式坐标滑动")
    swipe_to_parser.add_argument("x1", type=int, help="起点 X")
    swipe_to_parser.add_argument("y1", type=int, help="起点 Y")
    swipe_to_parser.add_argument("x2", type=int, help="终点 X")
    swipe_to_parser.add_argument("y2", type=int, help="终点 Y")
    swipe_to_parser.add_argument("--duration", "-d", type=int, default=500, help="时长(ms)")

    # pinch（双指缩小）
    pinch_parser = subparsers.add_parser("pinch", help="双指缩小（pinch / zoom out）")
    pinch_parser.add_argument("x", type=int, help="中心点 X 坐标")
    pinch_parser.add_argument("y", type=int, help="中心点 Y 坐标")
    pinch_parser.add_argument("--scale", "-s", type=float, default=0.5, help="缩放比例 0.1~1.0，默认 0.5")
    pinch_parser.add_argument("--duration", "-d", type=int, default=500, help="单指时长(ms)")

    # zoom（双指放大）
    zoom_parser = subparsers.add_parser("zoom", help="双指放大（zoom / zoom in）")
    zoom_parser.add_argument("x", type=int, help="中心点 X 坐标")
    zoom_parser.add_argument("y", type=int, help="中心点 Y 坐标")
    zoom_parser.add_argument("--scale", "-s", type=float, default=2.0, help="缩放比例 1.0~5.0，默认 2.0")
    zoom_parser.add_argument("--duration", "-d", type=int, default=500, help="单指时长(ms)")

    # keyevent
    key_parser = subparsers.add_parser("keyevent", help="按键")
    key_parser.add_argument("code", help="按键码或别名(back/home/enter 等)")

    # screenshot
    screenshot_parser = subparsers.add_parser("screenshot", help="截图")
    screenshot_parser.add_argument("output", help="截图保存路径")

    # close
    subparsers.add_parser("close", help="回到桌面")

    # get
    get_parser = subparsers.add_parser("get", help="获取指定区域内容描述(布局/图标/文字/介绍,不含坐标)")
    get_parser.add_argument("description", help="区域描述")
    get_parser.add_argument("--screenshot", "-s", type=str, help="保存原图路径(不加红框——本命令不返回坐标)")

    # batch
    batch_parser = subparsers.add_parser("batch", help="批量并行输入/点击")
    batch_parser.add_argument("instructions", nargs="+", help="批量指令: click 描述 | input 描述::值 | longpress 描述")
    batch_parser.add_argument("--screenshot", "-s", type=str, help="操作后保存截图")

    # shell
    shell_parser = subparsers.add_parser("shell", help="adb shell 透传")
    shell_parser.add_argument("cmd", nargs="+", help="要执行的命令")

    # dump-ui
    dump_parser = subparsers.add_parser("dump-ui", help="UI 层次 dump (XML)")
    dump_parser.add_argument("output", help="XML 保存路径")

    # appinfo
    appinfo_parser = subparsers.add_parser("appinfo", help="应用信息")
    appinfo_parser.add_argument("package", help="应用包名")

    # current-app
    current_app_parser = subparsers.add_parser("current-app", help="获取当前前台应用（package/activity）")
    current_app_parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")

    # wake / sleep / recents / notifications
    subparsers.add_parser("wake", help="唤醒屏幕")
    subparsers.add_parser("sleep", help="休眠屏幕")
    subparsers.add_parser("recents", help="打开最近任务（应用快速切换）")
    subparsers.add_parser("notifications", help="下拉通知栏")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    _load_cwd_env()

    # 命令路由
    handlers = {
        "devices": cmd_devices,
        "start": cmd_start,
        "launch": cmd_launch,
        "stop": cmd_stop,
        "click": cmd_click,
        "click-at": cmd_click_at,
        "input-at": cmd_input_at,
        "input": cmd_input,
        "longpress": cmd_longpress,
        "swipe": cmd_swipe,
        "swipe-to": cmd_swipe_to,
        "pinch": cmd_pinch,
        "zoom": cmd_zoom,
        "keyevent": cmd_keyevent,
        "screenshot": cmd_screenshot,
        "close": cmd_close,
        "get": cmd_get,
        "batch": cmd_batch,
        "shell": cmd_shell,
        "dump-ui": cmd_dump_ui,
        "appinfo": cmd_appinfo,
        "current-app": cmd_current_app,
        "wake": cmd_wake,
        "sleep": cmd_sleep,
        "recents": cmd_recents,
        "notifications": cmd_notifications,
    }
    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()