import json
from pathlib import Path
import pytest
from bigbear_device_record.capture.storage import Storage


def test_batch_dir_created(tmp_path: Path):
    storage = Storage(str(tmp_path))
    path = storage.save_snapshot(
        png_bytes=b"\x89PNG_FAKE",
        platform="android",
        module="1-2-3",
        func="登录页",
        desc="首次进入",
        device_dump="<hierarchy/>",
        device_id="emu-5554",
        device_name="Pixel 7",
        dimensions=(1080, 1920),
    )
    batch_dir = path.parent.parent
    assert (batch_dir / "img" / "screenshot_001.png").exists()
    assert (batch_dir / "json" / "android_001.json").exists()


def test_module_with_dash_creates_subdirs(tmp_path: Path):
    storage = Storage(str(tmp_path))
    path = storage.save_snapshot(
        png_bytes=b"PNG",
        platform="pc",
        module="人事管理-企业员工",
        func="列表",
        desc="",
        device_dump="",
        device_id="localhost",
        device_name="DESKTOP",
        dimensions=(1920, 1080),
    )
    # 新结构：<output_dir>/<batch_id>/人事管理/企业员工
    batch_dir = storage.get_module_dir("pc", "人事管理-企业员工")
    expected_dir = batch_dir
    assert expected_dir.exists()
    # path 是 json/xxx.json；其上两级目录是 session_dir（包含 img/json）
    assert path.parent.parent == expected_dir
    # 模块子目录相对批次根的位置（batch_id 是 YYYYMMDD-HHMMSS）
    batch_id_dir = batch_dir.parent.parent
    assert batch_id_dir.name.startswith("20")
    assert batch_dir.relative_to(batch_id_dir) == Path("人事管理") / "企业员工"


def test_index_increments_within_batch(tmp_path: Path):
    storage = Storage(str(tmp_path))
    p1 = storage.save_snapshot(
        png_bytes=b"P1", platform="android", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    p2 = storage.save_snapshot(
        png_bytes=b"P2", platform="android", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    assert p1.name == "android_001.json"
    assert p2.name == "android_002.json"


def test_different_platforms_share_batch_dir(tmp_path: Path):
    """多 platform 共用同一批次目录，但通过文件名前缀区分（不再独立目录）。"""
    storage = Storage(str(tmp_path))
    p1 = storage.save_snapshot(
        png_bytes=b"X", platform="android", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    p2 = storage.save_snapshot(
        png_bytes=b"X", platform="ios", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    # 两个 json 同属一个 module 目录（即同一 batch 下的同一 module）
    assert p1.parent == p2.parent
    assert p1.name == "android_001.json"
    assert p2.name == "ios_001.json"
    # 旧中间层 AI-信息采集 已移除
    assert "AI-信息采集" not in str(p1)
    assert "AI-信息采集" not in str(p2)


def test_json_content_matches_web_record_schema(tmp_path: Path):
    storage = Storage(str(tmp_path))
    path = storage.save_snapshot(
        png_bytes=b"PNGBYTES",
        platform="android",
        module="1-2-3",
        func="登录页",
        desc="首次进入",
        device_dump="<hierarchy>...</hierarchy>",
        device_id="emu-5554",
        device_name="Pixel 7",
        dimensions=(1080, 1920),
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    # 必须与 web-record dom_NN.json 字段完全一致
    assert set(data.keys()) >= {
        "content", "img", "module", "func", "desc",
    }
    assert data["content"] == "<hierarchy>...</hierarchy>"
    assert data["img"] == "img/screenshot_001.png"
    assert data["module"] == "1-2-3"
    assert data["func"] == "登录页"
    assert data["desc"] == "首次进入"
    # 不写入设备专属字段到 JSON（与 web-record schema 对齐）
    assert "platform" not in data
    assert "device_id" not in data
    assert "dimensions" not in data


def test_update_with_vision_merges_fields(tmp_path: Path):
    storage = Storage(str(tmp_path))
    path = storage.save_snapshot(
        png_bytes=b"PNG", platform="pc", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    storage.update_with_vision(path, {
        "interface_desc": "登录页",
        "layout_desc": "顶部 + 表单",
        "elements_desc": ["按钮", "输入框"],
    })
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["interface_desc"] == "登录页"
    assert data["layout_desc"] == "顶部 + 表单"
    assert data["elements_desc"] == ["按钮", "输入框"]


def test_module_path_strips_traversal(tmp_path: Path):
    storage = Storage(str(tmp_path))
    parts = storage._module_parts("..-foo-..")
    assert ".." not in parts
    assert "." not in parts


def test_next_index_handles_non_numeric_files(tmp_path: Path):
    storage = Storage(str(tmp_path))
    # First call creates the batch dir; we need to find the actual json_dir
    p0 = storage.save_snapshot(
        png_bytes=b"X", platform="android", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    json_dir = p0.parent
    # Remove auto-created 001 and inject our own pre-existing files
    p0.unlink()
    (json_dir / "android_001.json").write_text("{}")
    (json_dir / "android_abc.json").write_text("{}")  # non-numeric, should be ignored
    # Force a save to trigger _next_index (reuses cached batch_dir)
    path = storage.save_snapshot(
        png_bytes=b"X", platform="android", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    assert path.name == "android_002.json"


def test_next_index_handles_gaps(tmp_path: Path):
    storage = Storage(str(tmp_path))
    # First call creates the batch dir
    p0 = storage.save_snapshot(
        png_bytes=b"X", platform="android", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    json_dir = p0.parent
    p0.unlink()
    # Pre-create with gap
    (json_dir / "android_001.json").write_text("{}")
    (json_dir / "android_003.json").write_text("{}")  # gap at 002
    path = storage.save_snapshot(
        png_bytes=b"X", platform="android", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    # Should pick max+1 = 4, not fill the gap
    assert path.name == "android_004.json"


def test_update_with_vision_drops_unknown_fields(tmp_path: Path):
    storage = Storage(str(tmp_path))
    path = storage.save_snapshot(
        png_bytes=b"PNG", platform="pc", module="m", func="", desc="",
        device_dump="", device_id="d", device_name="d", dimensions=(1, 1),
    )
    storage.update_with_vision(path, {
        "interface_desc": "ok",
        "rogue_field": "should not appear",
        "another_rogue": 123,
    })
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["interface_desc"] == "ok"
    assert "rogue_field" not in data
    assert "another_rogue" not in data
