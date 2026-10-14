"""原生工具设备发现:adb / xcrun simctl / hdc。"""
import subprocess
from typing import List

from .base import DeviceConnectionError, DeviceInfo


class ToolNotFoundError(DeviceConnectionError):
    """平台原生工具未安装(adb / hdc / xcrun)。"""


def _run(cmd: List[str], timeout: int) -> "subprocess.CompletedProcess":
    """封装 subprocess.run,把 FileNotFoundError → ToolNotFoundError,timeout → DeviceConnectionError。"""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise ToolNotFoundError(f"{cmd[0]} not found on PATH") from e
    except subprocess.TimeoutExpired as e:
        raise DeviceConnectionError(
            f"{cmd[0]} timed out after {timeout}s"
        ) from e


def list_adb_devices(timeout: int = 15) -> List[DeviceInfo]:
    """调 `adb devices -l`,解析为 DeviceInfo 列表。"""
    proc = _run(["adb", "devices", "-l"], timeout)
    if proc.returncode != 0:
        raise ToolNotFoundError(f"adb failed: {proc.stderr[:200]}")
    out: List[DeviceInfo] = []
    for line in proc.stdout.splitlines()[1:]:  # 跳过 "List of devices attached"
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        name = serial
        for p in parts[2:]:
            if p.startswith("model:"):
                name = p.split(":", 1)[1]
                break
        out.append(DeviceInfo(id=serial, name=name, platform="android", state=state))
    return out


def list_xcrun_devices(timeout: int = 15) -> List[DeviceInfo]:
    """调 `xcrun simctl list devices --json`。仅在 macOS 实际跑,其他平台返 []。"""
    import json
    import platform as _plat
    if _plat.system() != "Darwin":
        return []
    proc = _run(["xcrun", "simctl", "list", "devices", "--json"], timeout)
    if proc.returncode != 0:
        raise ToolNotFoundError(f"xcrun simctl failed: {proc.stderr[:200]}")
    data = json.loads(proc.stdout)
    out: List[DeviceInfo] = []
    for runtime, devices in data.get("devices", {}).items():
        for d in devices:
            if not d.get("isAvailable", True):
                continue
            state = "device" if d.get("state") == "Booted" else "offline"
            out.append(DeviceInfo(
                id=d["udid"], name=d["name"], platform="ios", state=state,
            ))
    return out


def list_hdc_targets(timeout: int = 15) -> List[DeviceInfo]:
    """调 `hdc list targets`,每行一个 device serial。"""
    proc = _run(["hdc", "list", "targets"], timeout)
    if proc.returncode != 0:
        raise ToolNotFoundError(f"hdc failed: {proc.stderr[:200]}")
    out: List[DeviceInfo] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("empty") or "[" in line:
            continue
        out.append(DeviceInfo(
            id=line, name=line, platform="harmony", state="device",
        ))
    return out
