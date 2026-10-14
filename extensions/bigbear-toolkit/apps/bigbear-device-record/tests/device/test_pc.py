"""ComputerConnector 测试:继承 MidsceneConnector,用 mock runner 验证。"""
import re
import socket
import pytest
from PIL import Image as PILImage
from bigbear_device_record.device.pc import (
    ComputerConnector,
    _local_pc_info,
    _parse_computer_displays,
)
from bigbear_device_record.device.base import DeviceInfo, DeviceConnectionError
from bigbear_device_record.device.midscene import MidsceneError


def test_local_pc_info():
    info = _local_pc_info()
    assert info.id == "local-pc"
    assert info.platform == "pc"
    assert info.state == "device"
    assert info.name == socket.gethostname()


def test_parse_computer_displays_extracts_id_and_name():
    sample = (
        "Available displays:\n"
        "- id=\\\\.\\DISPLAY1, name=\\\\.\\DISPLAY1\n"
        "- id=\\\\.\\DISPLAY2, name=Second Monitor\n"
    )
    devices = _parse_computer_displays(sample)
    assert len(devices) == 2
    assert devices[0].id == "\\\\.\\DISPLAY1"
    assert devices[0].name == "\\\\.\\DISPLAY1"
    assert devices[1].id == "\\\\.\\DISPLAY2"
    assert devices[1].name == "Second Monitor"


def test_parse_computer_displays_empty_for_no_displays():
    assert _parse_computer_displays("Available displays:\n") == []


def test_computer_connector_pkg_and_flags():
    assert ComputerConnector.platform == "pc"
    assert ComputerConnector.midscene_pkg == "@midscene/computer@1"
    assert ComputerConnector.needs_screen_capture_path is True
    assert ComputerConnector.device_id_arg == "--display-id"  # midscene-computer 用 --display-id


def test_list_devices_falls_back_to_local_pc_on_no_displays():
    def fake_runner(args, timeout):
        return (0, "Available displays:\n", "")

    c = ComputerConnector(runner=fake_runner)
    devices = c.list_devices()
    assert len(devices) == 1
    assert devices[0].id == "local-pc"


def test_list_devices_uses_midscene_list_displays():
    sample = (
        "Available displays:\n"
        "- id=\\\\.\\DISPLAY1, name=\\\\.\\DISPLAY1\n"
    )
    def fake_runner(args, timeout):
        assert args[1] == "list_displays"
        return (0, sample, "")

    c = ComputerConnector(runner=fake_runner)
    devices = c.list_devices()
    assert len(devices) == 1
    assert devices[0].id == "\\\\.\\DISPLAY1"


def test_connect_rdp_minimal_host_only():
    """仅传 host + 默认 port=3389,其他 RDP 选项不出现。"""
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")
    c = ComputerConnector(runner=fake_runner)
    c.connect_rdp("192.168.1.100")
    assert c.is_connected() is True
    assert c._connected_to == "rdp://192.168.1.100:3389"
    argv = calls[0]
    assert argv[:4] == ["@midscene/computer@1", "connect", "--host", "192.168.1.100"]
    assert argv[4:6] == ["--port", "3389"]
    # 未指定的选项不应出现
    assert "--username" not in argv
    assert "--password" not in argv
    assert "--domain" not in argv


def test_connect_rdp_with_credentials():
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")
    c = ComputerConnector(runner=fake_runner)
    c.connect_rdp("10.0.0.5", port=13389, username="admin", password="s3cret")
    assert c._connected_to == "rdp://admin@10.0.0.5:13389"
    argv = calls[0]
    assert "--host" in argv and "10.0.0.5" in argv
    assert "--port" in argv and "13389" in argv
    assert "--username" in argv and "admin" in argv
    assert "--password" in argv and "s3cret" in argv


def test_connect_rdp_with_all_options():
    calls = []
    def fake_runner(args, timeout):
        calls.append(list(args))
        return (0, "", "")
    c = ComputerConnector(runner=fake_runner)
    c.connect_rdp(
        "host.example.com",
        port=3389,
        username="u",
        password="p",
        domain="DOMAIN",
        security_protocol="nla",
        ignore_certificate=True,
        admin_session=True,
        desktop_width=1920,
        desktop_height=1080,
    )
    argv = calls[0]
    # 这些都该出现一次
    for opt in ("--host", "host.example.com", "--port", "3389",
                "--username", "u", "--password", "p",
                "--domain", "DOMAIN", "--security-protocol", "nla",
                "--ignore-certificate", "--admin-session",
                "--desktop-width", "1920", "--desktop-height", "1080"):
        assert opt in argv, f"missing {opt} in {argv}"
    # 计数:每个 bool 选项出现一次
    assert argv.count("--ignore-certificate") == 1
    assert argv.count("--admin-session") == 1


def test_connect_rdp_already_connected_raises():
    c = ComputerConnector(runner=lambda a, t: (0, "", ""))
    c.connect_rdp("first.host")
    with pytest.raises(DeviceConnectionError) as exc_info:
        c.connect_rdp("second.host")
    assert "already connected" in str(exc_info.value)
    assert "first.host" in str(exc_info.value)


def test_connect_rdp_failure_wraps_as_device_connection_error():
    def fail_runner(args, timeout):
        raise MidsceneError("rdp handshake failed")
    c = ComputerConnector(runner=fail_runner)
    with pytest.raises(DeviceConnectionError) as exc_info:
        c.connect_rdp("bad.host", username="u", password="wrong")
    assert "rdp handshake failed" in str(exc_info.value)
    assert c.is_connected() is False


def test_local_connect_then_rdp_also_raises_already_connected():
    """本地 connect() 后再调 connect_rdp() 也应被拒绝(共享 _connected_to)。"""
    c = ComputerConnector(runner=lambda a, t: (0, "", ""))
    c.connect("local-pc")
    with pytest.raises(DeviceConnectionError) as exc_info:
        c.connect_rdp("remote.host")
    assert "already connected" in str(exc_info.value)
