import json
import pytest
from pathlib import Path
from bigbear_device_record.capture.recorder import SnapshotHandler
from bigbear_device_record.capture.storage import Storage
from tests.conftest import MockDeviceConnector


@pytest.fixture
def handler(tmp_output_dir: Path):
    connector = MockDeviceConnector()
    storage = Storage(str(tmp_output_dir))
    return SnapshotHandler(
        connector=connector,
        storage=storage,
        platform="mock",
        vision_config=None,
    )


def test_capture_saves_png_and_json(handler, tmp_output_dir):
    json_path = handler.capture(module="1-2-3", func="登录", desc="首次")
    batch_dir = json_path.parent.parent
    assert (batch_dir / "img" / "screenshot_001.png").exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["module"] == "1-2-3"
    assert data["func"] == "登录"
    assert data["desc"] == "首次"


def test_capture_increments_index(handler):
    handler.capture(module="m", func="", desc="")
    handler.capture(module="m", func="", desc="")
    handler.capture(module="m", func="", desc="")
    files = list((handler.storage.get_module_dir("mock", "m") / "json").glob("mock_*.json"))
    assert len(files) == 3


def test_capture_uses_connector_dump(handler):
    handler.connector._ui_hierarchy = "<hierarchy>HELLO</hierarchy>"
    json_path = handler.capture(module="m", func="", desc="")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["content"] == "<hierarchy>HELLO</hierarchy>"


def test_capture_without_vision_omits_vision_fields(handler):
    json_path = handler.capture(module="m", func="", desc="")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "interface_desc" not in data
    assert "layout_desc" not in data
    assert "elements_desc" not in data


def test_capture_with_vision_merges_result(tmp_output_dir):
    from unittest.mock import patch
    connector = MockDeviceConnector()
    storage = Storage(str(tmp_output_dir))
    handler = SnapshotHandler(
        connector=connector,
        storage=storage,
        platform="mock",
        vision_config={"api_key": "k", "base_url": "u", "model": "m"},
    )
    fake_vision = {
        "interface_desc": "i", "layout_desc": "l", "elements_desc": ["e"]
    }
    with patch(
        "bigbear_device_record.capture.recorder.analyze_screenshot_with_vision",
        return_value=fake_vision,
    ):
        json_path = handler.capture(module="m", func="", desc="")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["interface_desc"] == "i"
    assert data["layout_desc"] == "l"
    assert data["elements_desc"] == ["e"]


def test_vision_failure_does_not_block_save(tmp_output_dir):
    from unittest.mock import patch
    connector = MockDeviceConnector()
    storage = Storage(str(tmp_output_dir))
    handler = SnapshotHandler(
        connector=connector,
        storage=storage,
        platform="mock",
        vision_config={"api_key": "k", "base_url": "u", "model": "m"},
    )
    with patch(
        "bigbear_device_record.capture.recorder.analyze_screenshot_with_vision",
        return_value=None,
    ):
        json_path = handler.capture(module="m", func="", desc="")  # 不应抛
    assert json_path.exists()
