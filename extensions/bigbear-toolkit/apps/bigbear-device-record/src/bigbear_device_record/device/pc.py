"""PC 端 connector:经由 @midscene/computer@1 调 npx 截屏。

两种连接模式:
- 本地: connect(display_id)  →  midscene connect --display-id <id>
- RDP  : connect_rdp(host, port, ...)  →  midscene connect --host ... --port ...
"""
import re
import socket
from typing import List, Optional

from .base import DeviceInfo, DeviceConnectionError
from .midscene import MidsceneConnector, MidsceneError


def _local_pc_info() -> DeviceInfo:
    """无 midscene display 信息时的兜底。"""
    return DeviceInfo(
        id="local-pc", name=socket.gethostname(),
        platform="pc", state="device",
    )


def _parse_computer_displays(stdout: str) -> List[DeviceInfo]:
    """解析 `midscene list_displays` 输出:
        Available displays:
        - id=\\\\.\\DISPLAY1, name=\\\\.\\DISPLAY1
    """
    out: List[DeviceInfo] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        m_id = re.search(r"id=([^,]+)", line)
        m_name = re.search(r"name=(.+)$", line)
        if not m_id:
            continue
        raw_id = m_id.group(1).strip()
        raw_name = m_name.group(1).strip() if m_name else raw_id
        out.append(DeviceInfo(
            id=raw_id, name=raw_name, platform="pc", state="device",
        ))
    return out


class ComputerConnector(MidsceneConnector):
    platform = "pc"
    midscene_pkg = "@midscene/computer@1"
    device_id_arg = "--display-id"  # midscene-computer 不用 --device-id
    needs_screen_capture_path = True  # midscene 内部 screenCapture_*.bat 需要 PATH

    def list_devices(self) -> List[DeviceInfo]:
        _, stdout, _ = self._runner(
            [self.midscene_pkg, "list_displays"],
            self.LIST_DEVICES_TIMEOUT,
        )
        return _parse_computer_displays(stdout) or [_local_pc_info()]

    def connect_rdp(
        self,
        host: str,
        *,
        port: int = 3389,
        username: Optional[str] = None,
        password: Optional[str] = None,
        domain: Optional[str] = None,
        security_protocol: Optional[str] = None,
        ignore_certificate: bool = False,
        admin_session: bool = False,
        desktop_width: Optional[int] = None,
        desktop_height: Optional[int] = None,
    ) -> None:
        """经 RDP 远程连接 Windows 桌面。失败抛 DeviceConnectionError。

        对应 midscene-computer 的 RDP 模式(传 --host 触发)。其他 RDP 选项
        (--port/--username/--password 等)仅当 --host 设置时生效。
        """
        if self._connected_to:
            raise DeviceConnectionError(
                f"already connected to {self._connected_to}"
            )
        args = [self.midscene_pkg, "connect", "--host", host, "--port", str(port)]
        if username is not None:
            args += ["--username", username]
        if password is not None:
            args += ["--password", password]
        if domain is not None:
            args += ["--domain", domain]
        if security_protocol is not None:
            args += ["--security-protocol", security_protocol]
        if ignore_certificate:
            args += ["--ignore-certificate"]
        if admin_session:
            args += ["--admin-session"]
        if desktop_width is not None:
            args += ["--desktop-width", str(desktop_width)]
        if desktop_height is not None:
            args += ["--desktop-height", str(desktop_height)]
        try:
            self._runner(args, self.CONNECT_TIMEOUT)
        except MidsceneError as e:
            raise DeviceConnectionError(str(e)) from e
        # 用 rdp://user@host:port 作为连接标识(便于 UI 展示)
        user_part = f"{username}@" if username else ""
        self._connected_to = f"rdp://{user_part}{host}:{port}"

