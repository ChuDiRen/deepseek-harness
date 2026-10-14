"""CLI entry point for bigbear-mitmproxy-record.

子命令：
  - record       启动 mitmweb + 录制
  - install-ca   仅安装 CA 证书到系统证书库
  - check        环境检查
  - stop         终止后台录制
"""
import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from . import __version__
from .debug import debug, info, set_debug, step, warn, error
from .platform_utils import (
    find_mitmweb,
    open_url,
    pip_install,
    run_check,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bigbear-mitmproxy-record",
        description="录制任意 HTTP/HTTPS 客户端的网络流量到与 bigbear-api-record 兼容的 raw{NN}.json",
    )
    parser.add_argument(
        "--debug", action="store_true", help="详细调试日志"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---------- record ----------
    p_record = sub.add_parser(
        "record", help="启动录制（默认打开 mitmweb Web UI + 浏览器）"
    )
    p_record.add_argument(
        "--port", type=int, default=8080,
        help="mitmproxy 代理端口（客户端指向 127.0.0.1:<port>）",
    )
    p_record.add_argument(
        "--web-port", type=int, default=8081,
        help="mitmweb Web UI 端口（关闭此端口监听 = 停止录制）",
    )
    p_record.add_argument(
        "--control-port", type=int, default=9090,
        help="控制面板包装层端口（注入'停止录制'按钮的 HTTP 代理）",
    )
    p_record.add_argument(
        "--output", "-o", default="AI-信息采集",
        help="输出根目录（默认 ./AI-信息采集）",
    )
    p_record.add_argument(
        "--batch-id", default=None,
        help="批次号，不指定则用 YYYYMMDD-HHMMSS",
    )
    p_record.add_argument(
        "--exclude-pattern", action="append", default=[],
        help="排除的 URL 正则（可多次）",
    )
    p_record.add_argument(
        "--include-pattern", action="append", default=[],
        help="白名单正则（必须命中至少一条才保留）",
    )
    p_record.add_argument(
        "--resource-filter", default="off",
        choices=["off", "static", "api-only"],
        help=(
            "资源过滤预设：off=全收（默认）；"
            "static=跳过 URL 后缀为 css/js/png/jpg/font/视频/压缩包 等静态资源；"
            "api-only=在 static 基础上，再过滤掉响应 Content-Type 为 HTML 的页面，"
            "只保留 AJAX（json/xml/form/text/plain/javascript）"
        ),
    )
    p_record.add_argument(
        "--no-browser", action="store_true",
        help="不打开引导浏览器（APP/桌面应用场景，代理已配好）",
    )
    p_record.add_argument(
        "--ui-timeout", type=int, default=0,
        help="Web UI 不可用 N 秒后停止（0 = 不超时）",
    )
    p_record.add_argument(
        "--skip-ca-install", action="store_true",
        help="跳过 CA 证书安装（用户已手动装好）",
    )
    p_record.add_argument(
        "--no-stop-on-ui-close", action="store_true",
        help="关闭 mitmweb UI 也不停止（手动 Ctrl+C）",
    )
    p_record.add_argument(
        "--raw-index-start", type=int, default=1,
        help="raw 文件起始编号，默认 1",
    )
    p_record.add_argument(
        "--auto-split-by-domain", action="store_true",
        help="按 host 自动分文件（每 host 一个 raw{NN}.json）",
    )

    # ---------- install-ca ----------
    p_install = sub.add_parser(
        "install-ca", help="仅安装/重装 mitmproxy CA 证书到系统"
    )

    # ---------- check ----------
    p_check = sub.add_parser("check", help="检查环境与依赖")

    # ---------- stop ----------
    p_stop = sub.add_parser("stop", help="停止后台录制")
    p_stop.add_argument(
        "--pid-file", default=None,
        help="PID 文件路径，默认 ~/.bigbear-mitmproxy-record.pid",
    )

    return parser


def _write_addon_entry(
    addon_path: Path,
    batch_dir: Path,
    raw_index_start: int,
    exclude: list,
    include: list,
    auto_split: bool,
    resource_filter: str,
) -> None:
    """生成 mitmproxy -s 加载的 addon 入口脚本。

    mitmproxy 的 -s 只接受 Python 模块路径，所以 saver / addon 参数必须
    通过动态生成脚本的方式传递。脚本里直接构造 RecorderAddon(saver, ...)。
    """
    safe_batch = str(batch_dir).replace("\\", "\\\\")
    addon_path.parent.mkdir(parents=True, exist_ok=True)
    content = f'''"""Auto-generated addon entry for bigbear-mitmproxy-record.
由 bigbear-mitmproxy-record CLI 动态生成，请勿手工编辑。
"""
from bigbear_mitmproxy_record.recorder.saver import FlowSaver
from bigbear_mitmproxy_record.recorder.addon import RecorderAddon

saver = FlowSaver(
    batch_dir=r"{safe_batch}",
    raw_index_start={raw_index_start},
    exclude_patterns={exclude!r},
    include_patterns={include!r},
    auto_split_by_domain={auto_split},
)
addons = [
    RecorderAddon(
        saver=saver,
        exclude_patterns={exclude!r},
        include_patterns={include!r},
        resource_filter={resource_filter!r},
    )
]
'''
    addon_path.write_text(content, encoding="utf-8")


def _run_child(cmd: list, log_fp) -> subprocess.Popen:
    """启动 mitmweb 子进程，stdout/stderr 重定向到日志文件。"""
    debug(f"启动子进程: {' '.join(cmd)}")
    return subprocess.Popen(
        cmd,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        # Windows 上要开一个新进程组，方便 Ctrl+C 只杀当前 CLI 不连带 mitmweb
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )


def run_record(args) -> int:
    """record 子命令主流程。"""
    from . import ca_installer, process_manager
    from .recorder import webui_monitor

    # ---------- 1. 环境检查 ----------
    mitmweb = find_mitmweb()
    if not mitmweb:
        step("未找到 mitmweb，正在 pip install mitmproxy...")
        rc = pip_install(["mitmproxy"])
        if rc != 0:
            error("mitmproxy 安装失败，请手动: pip install mitmproxy")
            return 2
        mitmweb = find_mitmweb()
    if not mitmweb:
        error("仍然找不到 mitmweb")
        return 2
    info(f"mitmweb: {mitmweb}")

    # ---------- 2. 批次目录 ----------
    batch_id = args.batch_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    batch_dir = Path(args.output).resolve() / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    info(f"批次目录: {batch_dir}")

    # ---------- 3. CA 证书首部署 ----------
    if not args.skip_ca_install:
        ca_installer.ensure_ca_generated(mitmweb)
        # 装到系统证书库。失败不阻断，只 warn。
        ok, msg = _try_install_ca()
        if ok:
            info("[OK] CA 证书已安装到系统")
        elif msg:
            warn(f"CA 安装失败（不阻断录制）：{msg}")

    # ---------- 4. 生成 addon 入口脚本 ----------
    addon_path = Path.home() / ".bigbear-mitmproxy-record" / "addon_entry.py"
    _write_addon_entry(
        addon_path,
        batch_dir,
        args.raw_index_start,
        args.exclude_pattern,
        args.include_pattern,
        args.auto_split_by_domain,
        args.resource_filter,
    )

    # ---------- 5. 启动 mitmweb ----------
    conf_dir = Path.home() / ".bigbear-mitmproxy-record" / "conf"
    conf_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        mitmweb,
        "--listen-port", str(args.port),
        "--web-port", str(args.web_port),
        "--set", f"confdir={conf_dir}",
        "--set", "verbosity=info",
        "--ssl-insecure",
        "-s", str(addon_path),
    ]
    log_path = batch_dir / "mitmweb.log"
    log_fp = log_path.open("w", encoding="utf-8")
    proc = _run_child(cmd, log_fp)
    process_manager.write_pid(proc.pid)
    info(f"mitmweb 已启动 (PID {proc.pid})，日志: {log_path}")

    # ---------- 6. 等待 Web UI 就绪 ----------
    if not webui_monitor.wait_for_webui_ready(
        "127.0.0.1", args.web_port, deadline_sec=30
    ):
        error(f"mitmweb Web UI 启动超时（端口 {args.web_port} 未就绪）")
        try:
            proc.kill()
        except Exception:
            pass
        return 2
    info(f"Web UI 已就绪: http://127.0.0.1:{args.web_port}/")

    # ---------- 7. 打开浏览器（除非 --no-browser） ----------
    # 启动控制面板包装层（注入"停止录制"浮动按钮）
    from .recorder.control_panel import ControlPanel
    panel_stop_event = threading.Event()

    def _on_panel_stop():
        panel_stop_event.set()

    panel = ControlPanel(mitmweb_port=args.web_port, on_stop=_on_panel_stop)
    panel_started = panel.start(port=args.control_port)

    if not panel_started:
        warn(f"控制面板启动失败（端口 {args.control_port} 已被占用？）")
        warn("将直接打开 mitmweb Web UI（无'停止录制'按钮，需 Ctrl+C 停止）")
        panel = None

    if not args.no_browser:
        url = f"http://127.0.0.1:{panel.port}/" if panel_started else f"http://127.0.0.1:{args.web_port}/"
        if not open_url(url):
            warn("打开浏览器失败，请手动访问上面的地址")

    # ---------- 用户引导 ----------
    print()
    step("=" * 60)
    step(" bigbear-mitmproxy-record 已启动")
    step("=" * 60)
    if panel_started:
        step(f"  控制面板（含'停止录制'按钮）: http://127.0.0.1:{panel.port}/")
        step(f"  mitmweb Web UI (原始):          http://127.0.0.1:{args.web_port}/")
    else:
        step(f"  mitmweb Web UI: http://127.0.0.1:{args.web_port}/")
    step(f"  HTTP 代理:      127.0.0.1:{args.port}  ← 客户端指向这里")
    if not args.skip_ca_install:
        step("  HTTPS 已自动解密（CA 证书已安装到系统）")
    if args.resource_filter != "off":
        step(f"  资源过滤模式:   {args.resource_filter}"
             + ("（跳过 css/js/png/字体/视频/压缩包等）" if args.resource_filter == "static"
                else "（仅保留 AJAX：json/xml/form/text/plain/javascript）"))
    step("")
    step("  使用方式：")
    step("    浏览器/APP/桌面应用 配置代理 127.0.0.1:" + str(args.port))
    step("    正常使用客户端，所有 HTTP/HTTPS 请求被录制")
    if panel_started:
        step("    点击页面右下角'🛑 停止录制'按钮  = 停止录制")
    step("    或按 Ctrl+C 停止")
    step(f"  输出目录: {batch_dir}")
    step("=" * 60)
    print()

    # ---------- 8. 等待停止信号 ----------
    if args.no_stop_on_ui_close or not panel_started:
        # 用户明确要求不监听 UI 关闭；用占位 Event，永远不 set
        class _DummyEvent:
            def is_set(self) -> bool:
                return False
            def wait(self, *_args, **_kwargs):
                return False
            def set(self):
                pass
        stop_event = _DummyEvent()
    else:
        # 主停止信号：用户在控制面板页面点击"🛑 停止录制"按钮
        stop_event = panel_stop_event

    start = time.time()
    try:
        while True:
            if stop_event.is_set():
                info("用户在控制面板点击'停止录制'，停止录制")
                break
            if proc.poll() is not None:
                info(f"mitmweb 进程退出 (returncode={proc.returncode})")
                break
            if args.ui_timeout > 0 and (time.time() - start) > args.ui_timeout:
                info(f"达到 UI 超时 {args.ui_timeout}s，停止录制")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        info("用户中断 (Ctrl+C)")

    # ---------- 9. 清理 ----------
    info("停止 mitmweb...")
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        warn("mitmweb 未响应 SIGTERM，强制 kill")
        try:
            proc.kill()
        except Exception:
            pass
    except Exception as e:
        warn(f"停止 mitmweb 失败：{e}")

    process_manager.clear_pid()
    try:
        addon_path.unlink()
    except OSError:
        pass
    try:
        log_fp.close()
    except Exception:
        pass

    # 关闭控制面板包装层
    if panel_started:
        try:
            panel.stop()
        except Exception:
            pass

    info("[OK] 录制完成")
    info(f"     输出目录: {batch_dir}")
    info("     检测方式：python .claude/skills/bigbear-mitmproxy-record/scripts/inspect_recording.py " + str(batch_dir))
    return 0


def _try_install_ca() -> "tuple[bool, str]":
    """CA 安装静默版：失败不抛异常，返回 (ok, msg)。"""
    from .ca_installer import (
        install_ca_windows, install_ca_macos,
        install_ca_linux_debian, install_ca_linux_redhat,
        MITM_CA_FILE, MITM_CA_PEM, _print_manual_install_hint,
    )
    from .platform_utils import is_windows, is_macos, is_linux

    if not (MITM_CA_FILE.exists() or MITM_CA_PEM.exists()):
        return False, "CA 证书未生成"

    try:
        if is_windows():
            ok, msg = install_ca_windows()
        elif is_macos():
            ok, msg = install_ca_macos()
        elif is_linux():
            ok, msg = install_ca_linux_debian()
            if not ok:
                ok, msg = install_ca_linux_redhat()
        else:
            return False, f"不支持的平台"
        if not ok:
            _print_manual_install_hint()
        return ok, msg
    except Exception as e:
        return False, str(e)


def _ensure_utf8_stdout() -> None:
    """强制 stdout/stderr 为 UTF-8，避免 Windows GBK 终端打印 emoji 崩溃。

    CPython 默认 stdout 在 Windows 中文环境是 GBK，遇到 🛑/✅/🎉 等 emoji 会
    抛 UnicodeEncodeError。Python 3.7+ 支持 reconfigure()，失败时静默回退。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _ensure_utf8_stdout()
    parser = build_parser()
    args = parser.parse_args()
    set_debug(args.debug)

    if args.command == "record":
        return run_record(args)
    if args.command == "install-ca":
        from .ca_installer import install_ca
        return install_ca()
    if args.command == "check":
        return run_check(args)
    if args.command == "stop":
        from .process_manager import run_stop
        return run_stop(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())