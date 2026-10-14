"""后台 mitmweb 进程管理：PID 文件读写 + 跨平台停止。"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_PID_FILE = Path.home() / ".bigbear-mitmproxy-record.pid"


def write_pid(pid: int, path: Path = DEFAULT_PID_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid), encoding="utf-8")


def clear_pid(path: Path = DEFAULT_PID_FILE) -> None:
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _pid_alive(pid: int) -> bool:
    """跨平台判断 PID 是否存活。"""
    if os.name == "nt":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True, text=True,
        ).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop_by_pid(path: Path = DEFAULT_PID_FILE, timeout: int = 10) -> int:
    """根据 PID 文件优雅终止后台 mitmweb 进程。"""
    if not path.exists():
        print(f"[INFO] PID 文件不存在：{path}（没有后台录制在跑？）")
        return 0
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        print(f"[WARN] PID 文件格式错误：{path}")
        clear_pid(path)
        return 1

    if not _pid_alive(pid):
        print(f"[INFO] PID {pid} 已不存在")
        clear_pid(path)
        return 0

    print(f"[INFO] 终止 mitmweb (PID {pid})...")
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
            for _ in range(timeout * 2):
                if not _pid_alive(pid):
                    break
                time.sleep(0.5)
            if _pid_alive(pid):
                os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError as e:
        print(f"[ERROR] 无权终止 PID {pid}: {e}")
        return 2

    clear_pid(path)
    print("[OK] 已停止")
    return 0


def run_stop(args) -> int:
    """stop 子命令入口。"""
    path = Path(args.pid_file) if args.pid_file else DEFAULT_PID_FILE
    return stop_by_pid(path)