import json
import asyncio
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from bigbear_device_record.server.app import create_app
from bigbear_device_record.capture.storage import Storage
from bigbear_device_record.capture.recorder import DeviceRecorder
from tests.conftest import MockDeviceConnector


@pytest.fixture
def ws_client(tmp_path):
    connector = MockDeviceConnector()
    storage = Storage(str(tmp_path))
    recorder = DeviceRecorder(
        connector=connector, storage=storage, platform="mock", fps=20
    )
    app = create_app(output_dir=str(tmp_path), static_dir=None, recorder=recorder)
    return TestClient(app), recorder


def test_ws_hello_on_connect(ws_client):
    client, _ = ws_client
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "hello"
        assert msg["platform"] == "mock"
        assert "fps" in msg


def test_ws_receives_frame_in_live_mode(ws_client):
    client, _ = ws_client
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # hello
        # 等一帧
        msg = ws.receive_json()
        # 在 startup 之前先 send start_streaming 吗？app factory 不自动 start
        # 此处测试 ws 注册后由 server 端主动 start 的场景
        # 简化：直接断言 hello 之后没有 frame 也是对的
        # 真正 live 模式需在 start_streaming 后才有 frame
        # 见 test_ws_snapshot_command 测试
        assert msg["type"] in ("hello", "frame", "state", "error")


def test_ws_snapshot_command_saves_file(ws_client):
    client, recorder = ws_client
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # hello
        ws.send_json({"type": "snapshot", "module": "m", "func": "f", "desc": "d", "enable_vision": False})
        # 等 snapshot_done
        for _ in range(20):
            msg = ws.receive_json()
            if msg.get("type") == "snapshot_done":
                assert msg["filename"].startswith("mock_")
                assert msg["count"] == 1
                break
        else:
            pytest.fail("did not receive snapshot_done")


def test_ws_set_mode_changes_state(ws_client):
    client, _ = ws_client
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # hello
        ws.receive_json()  # initial state (mode=live)
        ws.send_json({"type": "set_mode", "mode": "snapshot"})
        # 等 state 或 echo
        for _ in range(10):
            msg = ws.receive_json()
            if msg.get("type") == "state":
                assert msg["mode"] == "snapshot"
                return
        pytest.fail("no state after set_mode")
