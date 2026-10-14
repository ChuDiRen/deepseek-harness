"""平台判断 + pip 安装 + mitmweb 定位 + 跨平台 URL 打开。"""
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import List, Optional

# 项目惯例：清华源 + 华测私有源
TSINGHUA_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple/"
BIGBEAR_INDEX = "http://pypi.hctestedu.com/repository/test/simple/"


def is_windows() -> bool:
    return sys.platform == "win32"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def get_pip_command() -> List[str]:
    """统一用 `python -m pip` 跨平台调用。

    注：用户原描述里说 win 是 `pip`、mac/linux 是 `pip3`，但 `python -m pip`
    在所有平台都可用，且能保证用的是当前 Python 解释器对应的 pip。
    """
    return [sys.executable, "-m", "pip"]


def pip_install(pkgs: List[str], upgrade: bool = True) -> int:
    """安装 Python 包。先清华源，失败回退华测源。

    Returns: subprocess 退出码（0 = 成功）。
    """
    from .debug import info, warn

    base = get_pip_command() + ["install"]
    if upgrade:
        base.append("--upgrade")

    for mirror_name, mirror_url in [("清华源", TSINGHUA_INDEX), ("华测源", BIGBEAR_INDEX)]:
        cmd = base + ["-i", mirror_url] + pkgs
        info(f"pip install {pkgs} (镜像: {mirror_name})")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return 0
        warn(f"{mirror_name} 失败: {r.stderr.strip() or r.stdout.strip()}")

    return r.returncode


def find_mitmweb() -> Optional[str]:
    """定位 mitmweb 可执行文件。

    Returns: 可执行文件绝对路径，或 None（需要先 pip install mitmproxy）。
    """
    found = shutil.which("mitmweb")
    if found:
        return found

    # 平台特定回退路径
    candidates: List[str] = []
    if is_windows():
        candidates += [
            r"D:\Program Files\mitmproxy\bin\mitmweb.exe",
            r"C:\Program Files\mitmproxy\bin\mitmweb.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\mitmproxy\mitmweb.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts\mitmweb.exe"),
        ]
    elif is_macos():
        candidates += [
            "/usr/local/bin/mitmweb",
            "/opt/homebrew/bin/mitmweb",
            str(Path.home() / ".local" / "bin" / "mitmweb"),
        ]
    else:
        candidates += [
            "/usr/local/bin/mitmweb",
            "/usr/bin/mitmweb",
            str(Path.home() / ".local" / "bin" / "mitmweb"),
        ]

    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def open_url(url: str) -> bool:
    """跨平台用系统默认浏览器打开 URL。"""
    try:
        return webbrowser.open(url)
    except Exception:
        return False


def _check_cmd(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run_check(args) -> int:
    """check 子命令实现：打印环境诊断信息。"""
    from .debug import step, info

    step("=== bigbear-mitmproxy-record 环境检查 ===")
    info(f"Python:        {sys.version.split()[0]}")
    info(f"Platform:      {sys.platform} ({'Windows' if is_windows() else 'macOS' if is_macos() else 'Linux' if is_linux() else 'Unknown'})")

    mw = find_mitmweb()
    info(f"mitmweb:       {mw or '[未找到]'}")
    try:
        import mitmproxy
        # mitmproxy 某些版本没有 __version__ 属性，用 metadata 兜底
        version = getattr(mitmproxy, "__version__", None)
        if not version:
            try:
                from importlib.metadata import version as _v
                version = _v("mitmproxy")
            except Exception:
                version = "unknown"
        info(f"mitmproxy:     v{version}")
    except ImportError:
        info(f"mitmproxy:     [未安装]")

    ca = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.cer"
    info(f"CA 证书:       {ca}{' (已生成)' if ca.exists() else ' (未生成)'}")

    if is_windows():
        info(f"certutil:      {'OK' if _check_cmd('certutil') else '[缺失]'}")
    elif is_macos():
        info(f"security:      {'OK' if _check_cmd('security') else '[缺失]'}")
    else:
        info(f"update-ca-certificates: {'OK' if _check_cmd('update-ca-certificates') else '[缺失]'}")
        info(f"update-ca-trust:        {'OK' if _check_cmd('update-ca-trust') else '[缺失]'}")
    return 0