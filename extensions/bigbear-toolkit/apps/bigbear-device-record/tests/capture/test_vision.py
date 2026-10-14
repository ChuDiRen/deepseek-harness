import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from bigbear_device_record.capture.vision import analyze_screenshot_with_vision


def _fake_png(path: Path):
    # 合法 PNG header + 1px 内容（不需真实解码，openai client 也只 base64 编码）
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)


def test_returns_parsed_json(tmp_path: Path):
    png = tmp_path / "s.png"
    _fake_png(png)
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value.model_dump_json.return_value = json.dumps({
        "choices": [{"message": {"content": json.dumps({
            "interface_desc": "登录页",
            "layout_desc": "顶部+表单",
            "elements_desc": ["按钮"],
        })}}]
    })
    with patch("bigbear_device_record.capture.vision._get_client", return_value=fake_client):
        result = analyze_screenshot_with_vision(
            str(png), api_key="k", base_url="https://x", model="m"
        )
    assert result == {
        "interface_desc": "登录页",
        "layout_desc": "顶部+表单",
        "elements_desc": ["按钮"],
    }


def test_extracts_json_from_markdown_block(tmp_path: Path):
    png = tmp_path / "s.png"
    _fake_png(png)
    fake_client = MagicMock()
    response_text = "```json\n" + json.dumps({
        "interface_desc": "i", "layout_desc": "l", "elements_desc": ["e"]
    }) + "\n```"
    fake_client.chat.completions.create.return_value.model_dump_json.return_value = json.dumps({
        "choices": [{"message": {"content": response_text}}]
    })
    with patch("bigbear_device_record.capture.vision._get_client", return_value=fake_client):
        result = analyze_screenshot_with_vision(str(png), "k", "https://x", "m")
    assert result["interface_desc"] == "i"


def test_returns_none_on_openai_exception(tmp_path: Path):
    png = tmp_path / "s.png"
    _fake_png(png)
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = RuntimeError("network")
    with patch("bigbear_device_record.capture.vision._get_client", return_value=fake_client):
        result = analyze_screenshot_with_vision(str(png), "k", "https://x", "m")
    assert result is None
