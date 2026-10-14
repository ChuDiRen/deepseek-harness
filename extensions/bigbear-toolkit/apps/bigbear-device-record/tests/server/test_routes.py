import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from bigbear_device_record.server.app import create_app
from bigbear_device_record.capture.storage import Storage
from bigbear_device_record.capture.recorder import DeviceRecorder, SnapshotHandler
from tests.conftest import MockDeviceConnector


@pytest.fixture
def client_with_recorder(tmp_path):
    connector = MockDeviceConnector()
    storage = Storage(str(tmp_path))
    recorder = DeviceRecorder(
        connector=connector, storage=storage, platform="mock", fps=2,
    )
    app = create_app(output_dir=str(tmp_path), static_dir=None, recorder=recorder)
    return TestClient(app), recorder, tmp_path


def test_api_devices_returns_list():
    app = create_app(output_dir="./_test", static_dir=None)
    # 替换 connector：使用 mock（直接 patch list_devices）
    from bigbear_device_record.device.pc import ComputerConnector
    original = ComputerConnector.list_devices
    ComputerConnector.list_devices = lambda self: [
        __import__("bigbear_device_record.device.base", fromlist=["DeviceInfo"]).DeviceInfo(
            id="x", name="X", platform="pc", state="device"
        )
    ]
    try:
        client = TestClient(app)
        resp = client.get("/api/devices?platform=pc")
        assert resp.status_code == 200
        data = resp.json()
        assert "devices" in data
    finally:
        ComputerConnector.list_devices = original


def test_api_snapshot_triggers_capture(client_with_recorder):
    client, recorder, tmp_path = client_with_recorder
    resp = client.post("/api/snapshot", json={
        "module": "1-2-3", "func": "登录", "desc": "首次"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "filename" in data
    assert data["filename"].startswith("mock_")
    # 文件应已落盘
    assert recorder.snapshot_count == 1


def test_api_output_tree_lists_batches(client_with_recorder):
    client, recorder, tmp_path = client_with_recorder
    # 先采一张
    client.post("/api/snapshot", json={"module": "1-2-3", "func": "", "desc": ""})
    resp = client.get("/api/output/tree")
    assert resp.status_code == 200
    data = resp.json()
    assert "tree" in data
