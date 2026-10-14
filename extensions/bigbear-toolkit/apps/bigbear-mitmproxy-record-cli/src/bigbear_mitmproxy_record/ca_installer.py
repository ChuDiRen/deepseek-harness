"""mitmproxy CA 证书生成与跨平台安装。

首次部署流程：
1. 临时启动 mitmdump 1-2 秒，让 mitmproxy 生成 ~/.mitmproxy/mitmproxy-ca-cert.cer
2. 按平台调用系统命令把证书装到系统根证书库
3. 失败时打印手动安装指引，不阻断录制启动
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

from .platform_utils import (
    find_mitmweb,
    is_windows,
    is_macos,
    is_linux,
)

# mitmproxy 默认 CA 路径（所有平台一致）
MITM_CA_DIR = Path.home() / ".mitmproxy"
MITM_CA_FILE = MITM_CA_DIR / "mitmproxy-ca-cert.cer"
MITM_CA_PEM = MITM_CA_DIR / "mitmproxy-ca-cert.pem"


def ensure_ca_generated(mitmproxy_bin: str, port: int = 1) -> bool:
    """临时启一次 mitmdump 触发证书生成。返回是否成功。"""
    from .debug import info, warn

    if MITM_CA_FILE.exists() or MITM_CA_PEM.exists():
        return True

    MITM_CA_DIR.mkdir(parents=True, exist_ok=True)

    # mitmproxy 10+ 同时生成 .cer（DER）和 .pem
    cmd = [mitmproxy_bin, "--listen-port", str(port), "--set", f"confdir={MITM_CA_DIR}"]
    info(f"临时启动 {mitmproxy_bin} 触发证书生成...")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        warn(f"启动 mitmdump 失败：{e}")
        return False

    # 等最多 10 秒让证书落盘
    for _ in range(50):
        if MITM_CA_FILE.exists() or MITM_CA_PEM.exists():
            break
        time.sleep(0.2)
    else:
        warn("10 秒内未生成证书")

    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    return MITM_CA_FILE.exists() or MITM_CA_PEM.exists()


def install_ca_windows() -> Tuple[bool, str]:
    """Windows: certutil -addstore -f "Root" <cert>"""
    cert = MITM_CA_FILE if MITM_CA_FILE.exists() else MITM_CA_PEM
    cmd = ["certutil", "-addstore", "-f", "Root", str(cert)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.returncode == 0, (r.stderr or r.stdout).strip())


def install_ca_macos() -> Tuple[bool, str]:
    """macOS: sudo security add-trusted-cert ..."""
    cert = MITM_CA_FILE if MITM_CA_FILE.exists() else MITM_CA_PEM
    cmd = [
        "sudo", "security", "add-trusted-cert",
        "-d", "-r", "trustRoot",
        "-k", "/Library/Keychains/System.keychain",
        str(cert),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.returncode == 0, (r.stderr or r.stdout).strip())


def install_ca_linux_debian() -> Tuple[bool, str]:
    """Linux (Debian/Ubuntu): 复制到 /usr/local/share/ca-certificates/ + update-ca-certificates"""
    cert_src = MITM_CA_PEM if MITM_CA_PEM.exists() else MITM_CA_FILE
    if not cert_src.exists():
        return False, "CA 证书不存在"
    target = Path("/usr/local/share/ca-certificates/mitmproxy.crt")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cert_src, target)
    except PermissionError as e:
        return False, f"权限不足：{e}"
    r = subprocess.run(["sudo", "update-ca-certificates"], capture_output=True, text=True)
    return (r.returncode == 0, (r.stderr or r.stdout).strip())


def install_ca_linux_redhat() -> Tuple[bool, str]:
    """Linux (RHEL/Fedora/CentOS): 复制到 /etc/pki/ca-trust/source/anchors/ + update-ca-trust"""
    cert_src = MITM_CA_PEM if MITM_CA_PEM.exists() else MITM_CA_FILE
    if not cert_src.exists():
        return False, "CA 证书不存在"
    target = Path("/etc/pki/ca-trust/source/anchors/mitmproxy.crt")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cert_src, target)
    except PermissionError as e:
        return False, f"权限不足：{e}"
    r = subprocess.run(["sudo", "update-ca-trust"], capture_output=True, text=True)
    return (r.returncode == 0, (r.stderr or r.stdout).strip())


def install_ca() -> int:
    """install-ca 子命令入口。"""
    from .debug import info, warn

    mitmweb = find_mitmweb()
    if not mitmweb:
        warn("未找到 mitmweb，请先执行: pip install mitmproxy")
        return 2

    if not ensure_ca_generated(mitmweb):
        warn("证书生成失败")
        return 1

    if is_windows():
        ok, msg = install_ca_windows()
    elif is_macos():
        ok, msg = install_ca_macos()
    elif is_linux():
        # 优先尝试 Debian/Ubuntu 风格，失败回退 RHEL/Fedora 风格
        ok, msg = install_ca_linux_debian()
        if not ok and "update-ca-certificates" in msg:
            ok, msg = install_ca_linux_redhat()
    else:
        warn(f"不支持的平台：{sys.platform}")
        return 2

    if ok:
        info(f"[OK] CA 证书已安装到系统证书库")
        info(f"     路径：{MITM_CA_FILE if MITM_CA_FILE.exists() else MITM_CA_PEM}")
        return 0
    else:
        warn(f"[FAIL] CA 证书安装失败：{msg}")
        _print_manual_install_hint()
        return 1


def _print_manual_install_hint() -> None:
    """权限不足时打印手动安装指引。"""
    cert = MITM_CA_FILE if MITM_CA_FILE.exists() else MITM_CA_PEM
    print()
    print("=" * 60)
    print("  请手动执行以下命令安装 CA 证书：")
    print("=" * 60)
    if is_windows():
        print(f"  certutil -addstore -f \"Root\" \"{cert}\"")
        print("  (需要以管理员身份打开 PowerShell)")
    elif is_macos():
        print(f"  sudo security add-trusted-cert -d -r trustRoot \\")
        print(f"    -k /Library/Keychains/System.keychain \\")
        print(f"    \"{cert}\"")
    elif is_linux():
        print(f"  # Debian/Ubuntu:")
        print(f"  sudo cp {cert} /usr/local/share/ca-certificates/mitmproxy.crt")
        print(f"  sudo update-ca-certificates")
        print(f"  # RHEL/Fedora:")
        print(f"  sudo cp {cert} /etc/pki/ca-trust/source/anchors/mitmproxy.crt")
        print(f"  sudo update-ca-trust")
    print("=" * 60)
    print()
    print("  或重新用管理员/sudo 身份运行本命令。")
    print("=" * 60)