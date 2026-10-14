"""mitmweb Web UI 端口探活。

通过 TCP connect 探测 127.0.0.1:<web_port>：
- wait_for_webui_ready: 启动时等待端口就绪
- watch_webui: 后台线程监控端口，连续 N 次失败则置位 stop_event

设计要点：
- 首次就绪前的探活失败不算（避免误杀启动过程）
- 线程 daemon=True，主进程退出自动结束
"""
import socket
import threading
import time
from typing import Optional


def _probe(host: str, port: int, timeout: float = 0.5) -> bool:
    """单次 TCP 探活。返回是否成功连接。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_webui_ready(host: str, port: int, deadline_sec: int = 30) -> bool:
    """启动时等待端口就绪（只关心"是否能连上"，不关心曾经是否失败过）。"""
    end = time.time() + deadline_sec
    while time.time() < end:
        if _probe(host, port, timeout=0.5):
            return True
        time.sleep(0.5)
    return False


def watch_webui(
    host: str,
    port: int,
    fail_threshold: int = 3,
    poll_interval: float = 1.0,
) -> threading.Event:
    """后台线程：连续 fail_threshold 次探活失败（且期间曾经就绪过）则置位 stop_event。

    Returns: Event 对象，主进程可调 .is_set() 或 .wait(timeout=...)
    """
    stop_event = threading.Event()

    def _run():
        seen_ready = False
        fail_count = 0
        while not stop_event.is_set():
            ok = _probe(host, port, timeout=0.5)
            if ok:
                seen_ready = True
                fail_count = 0
            elif seen_ready:
                fail_count += 1
                if fail_count >= fail_threshold:
                    stop_event.set()
                    return
            stop_event.wait(poll_interval)

    t = threading.Thread(target=_run, daemon=True, name="webui-monitor")
    t.start()
    return stop_event