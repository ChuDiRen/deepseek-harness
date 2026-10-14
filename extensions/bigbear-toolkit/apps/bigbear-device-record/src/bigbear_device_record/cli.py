"""CLI entry point for bigbear-device-record.

Usage:
  bigbear-device-record record --platform {android|ios|harmony|pc}
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from .capture.recorder import DeviceRecorder
from .capture.storage import Storage
from .device.manager import DeviceManager
from .server.app import create_app
from .debug import set_debug, debug, info, warn, error, step


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bigbear-device-record")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("record", help="Record device screens")
    p.add_argument("--platform", required=True, choices=["android", "ios", "harmony", "pc"])
    p.add_argument("--device-id", default=None)
    p.add_argument("--output", "-o", default="AI-信息采集")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--fps", type=int, default=2)
    p.add_argument("--enable-vision", action="store_true", default=False)
    p.add_argument("--debug", action="store_true", default=False)
    p.add_argument("--verbose", "-v", action="store_true", default=False)
    p.add_argument(
        "--no-browser",
        action="store_true",
        default=False,
        help="Do not open browser automatically",
    )
    return parser


def _load_cwd_env():
    """仅加载执行命令时当前工作目录下的 .env。"""
    env_path = Path.cwd() / ".env"
    if not env_path.is_file():
        return None

    load_dotenv(dotenv_path=env_path, override=False)
    return env_path


def _make_vision_config(enable: bool, debug_mode: bool = False) -> Optional[dict]:
    if not enable:
        return None

    api_key = (os.environ.get("DEVICE_VISION_API_KEY") or os.environ.get("DSH_BIGBEAR_DEVICE_VISION_API_KEY"))
    base_url = (os.environ.get("DEVICE_VISION_BASE_URL") or os.environ.get("DSH_BIGBEAR_DEVICE_VISION_BASE_URL"))
    model = os.environ.get("DEVICE_VISION_MODEL", "qwen3.6-flash-2026-04-16")

    debug(
        f"DEVICE_VISION_API_KEY={'已设置' if api_key else '未设置'}, "
        f"DEVICE_VISION_BASE_URL={'已设置' if base_url else '未设置'}"
    )
    if not api_key or not base_url:
        warn("--enable-vision 但 DEVICE_VISION_API_KEY 或 DEVICE_VISION_BASE_URL 未配置，vision 关闭")
        return None

    return {"api_key": api_key, "base_url": base_url, "model": model}


def main(argv=None):
    logging.basicConfig(
        level=logging.DEBUG if "--verbose" in (argv or sys.argv) else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    set_debug(args.debug)

    loaded_env_file = _load_cwd_env()
    if loaded_env_file:
        debug(f".env loaded: {loaded_env_file}")
    else:
        debug(".env not found in current directory")

    if args.command == "record":
        _run_record(args)
    else:
        parser.print_help()
        sys.exit(1)


async def _run_record_async(args):
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    info(f"Output directory: {output_dir}")

    info(f"Connecting to {args.platform} device...")
    manager = DeviceManager(platform=args.platform, device_id=args.device_id)
    try:
        info_dev = manager.connect()
    except NotImplementedError as e:
        error(str(e))
        error(f"{args.platform} connector is not implemented.")
        sys.exit(2)
    except Exception as e:
        error(f"Failed to connect: {e}")
        sys.exit(2)
    info(f"Connected to {info_dev.name} ({info_dev.id})")

    try:
        w, h = manager.connector.get_dimensions()
        info(f"Screen size: {w}x{h}")
    except Exception:
        pass

    storage = Storage(output_dir)
    vision_config = _make_vision_config(args.enable_vision, debug_mode=args.debug)
    if vision_config:
        info(f"Vision analysis enabled, model: {vision_config['model']}")

    recorder = DeviceRecorder(
        connector=manager.connector,
        storage=storage,
        platform=args.platform,
        fps=args.fps,
        vision_config=vision_config,
    )

    import bigbear_device_record

    pkg_dir = Path(bigbear_device_record.__file__).parent
    static_dir = pkg_dir / "static"
    app = create_app(
        output_dir=output_dir,
        static_dir=str(static_dir) if static_dir.exists() else None,
        recorder=recorder,
    )

    config = uvicorn.Config(app, host=args.host, port=args.port, log_level="warning")
    server = uvicorn.Server(config)

    async def run_server():
        await server.serve()

    server_task = asyncio.create_task(run_server())
    browser_closed_event = asyncio.Event()

    def on_browser_close():
        if not browser_closed_event.is_set():
            browser_closed_event.set()

    if not args.no_browser:
        url = f"http://{args.host}:{args.port}/"
        info(f"Opening browser at: {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            page.on("close", lambda _: on_browser_close())
            context.on("close", lambda _: on_browser_close())

            await page.goto(url)
            info("Browser opened. Close browser to exit.")

            await browser_closed_event.wait()

            await browser.close()
            info("Browser closed.")
    else:
        info(f"Server running on {args.host}:{args.port} ...")
        info("Press Ctrl+C to stop")
        try:
            await server_task
        except KeyboardInterrupt:
            info("Stopping...")

    server.should_exit = True
    await server_task

    try:
        manager.disconnect()
    except Exception:
        pass
    info("Disconnected. Bye.")


def _run_record(args):
    asyncio.run(_run_record_async(args))


if __name__ == "__main__":
    main()
