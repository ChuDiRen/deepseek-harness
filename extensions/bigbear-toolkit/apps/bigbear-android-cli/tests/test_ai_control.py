# -*- coding: utf-8 -*-
"""AIControl 单元测试（mock OpenAI 客户端）"""
import io
import json
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from bigbear_android.ai_control import AIControl


@pytest.fixture
def mock_ai():
    """构造 AIControl 实例，mock OpenAI 客户端"""
    with patch("bigbear_android.ai_control.OpenAI") as mock_openai:
        ai = AIControl(api_key="test-key", base_url="http://test", model="test-model")
        ai.client = MagicMock()
        yield ai


def _make_completion(content: str) -> MagicMock:
    """构造 mock completion 响应"""
    return MagicMock(
        model_dump_json=lambda: json.dumps({
            "choices": [{"message": {"content": content}}]
        })
    )


def _make_jpeg_bytes(width: int = 100, height: int = 100) -> bytes:
    """生成测试用 JPEG 字节"""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ===== 单元素识别 =====

def test_find_element_success(mock_ai):
    """成功识别单元素，返回中心点"""
    mock_response = json.dumps({"found": True, "bbox": [100, 200, 300, 400]})
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    img_b64 = "fake_base64"
    x, y = mock_ai.find_element(img_b64, pil_img, "登录按钮")

    # 中心点 = (200, 300)，1000x1000 屏幕上 scale=1
    assert x == 200.0
    assert y == 300.0


def test_find_element_scales_to_screen_size(mock_ai):
    """坐标按屏幕尺寸缩放"""
    mock_response = json.dumps({"found": True, "bbox": [500, 500, 1000, 1000]})
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    # 屏幕 2000x3000，scale = 2.0/3.0
    pil_img = Image.new("RGB", (2000, 3000), color="red")
    x, y = mock_ai.find_element("b64", pil_img, "按钮")

    # bbox[0]=500 → 1000, bbox[2]=1000 → 2000, center_x = 1500
    # bbox[1]=500 → 1500, bbox[3]=1000 → 3000, center_y = 2250
    assert x == 1500.0
    assert y == 2250.0


def test_find_element_handles_json_code_block(mock_ai):
    """识别 ```json ... ``` 代码块包裹"""
    content = '```json\n{"found": true, "bbox": [0, 0, 100, 100]}\n```'
    mock_ai.client.chat.completions.create.return_value = _make_completion(content)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    x, y = mock_ai.find_element("b64", pil_img, "按钮")
    assert x == 50.0
    assert y == 50.0


def test_find_element_not_found_raises(mock_ai):
    """找不到元素时抛异常（重试耗尽）"""
    mock_ai.client.chat.completions.create.return_value = _make_completion(
        json.dumps({"found": False})
    )

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    with pytest.raises(Exception, match="元素识别失败"):
        mock_ai.find_element("b64", pil_img, "不存在的按钮", max_retries=2)


def test_find_element_retries_on_error(mock_ai):
    """失败时自动重试"""
    mock_ai.client.chat.completions.create.side_effect = [
        Exception("network error"),
        _make_completion(json.dumps({"found": True, "bbox": [0, 0, 100, 100]})),
    ]
    pil_img = Image.new("RGB", (1000, 1000), color="red")
    x, y = mock_ai.find_element("b64", pil_img, "按钮", max_retries=3)
    assert mock_ai.client.chat.completions.create.call_count == 2


# ===== 批量识别 =====

def test_find_element_batch_all_found(mock_ai):
    """批量识别全部成功"""
    mock_response = json.dumps({
        "elements": [
            {"name": "按钮A", "found": True, "bbox": [100, 100, 200, 200]},
            {"name": "按钮B", "found": True, "bbox": [300, 300, 400, 400]},
        ]
    })
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    results = mock_ai.find_element_batch("b64", pil_img, ["按钮A", "按钮B"])

    assert len(results) == 2
    assert results[0] == ("按钮A", 150.0, 150.0)
    assert results[1] == ("按钮B", 350.0, 350.0)


def test_find_element_batch_partial(mock_ai):
    """批量识别部分失败"""
    mock_response = json.dumps({
        "elements": [
            {"name": "按钮A", "found": True, "bbox": [0, 0, 100, 100]},
            {"name": "按钮B", "found": False},
        ]
    })
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    results = mock_ai.find_element_batch("b64", pil_img, ["按钮A", "按钮B"])

    assert results[0] == ("按钮A", 50.0, 50.0)
    assert results[1] == ("按钮B", None, None)


def test_find_element_batch_failure_returns_none(mock_ai):
    """批量识别整体失败返回全 None"""
    mock_ai.client.chat.completions.create.side_effect = Exception("API error")

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    results = mock_ai.find_element_batch("b64", pil_img, ["A", "B"])

    assert results == [("A", None, None), ("B", None, None)]


# ===== 内容提取 =====

def test_get_content_ai_success(mock_ai):
    """成功提取区域内容"""
    mock_response = json.dumps({"bbox": [100, 100, 500, 300], "content": "标题文本"})
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    result = mock_ai.get_content_ai("b64", pil_img, "标题区域")

    assert result["content"] == "标题文本"
    assert result["bbox"] == [100, 100, 500, 300]


def test_get_content_ai_handles_list_format(mock_ai):
    """兼容 [bbox, content] 列表格式"""
    mock_response = json.dumps([[0, 0, 200, 200], "区域内容"])
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    result = mock_ai.get_content_ai("b64", pil_img, "区域")

    assert result["content"] == "区域内容"
    assert result["bbox"] == [0, 0, 200, 200]


def test_get_content_ai_unparseable_raises(mock_ai):
    """无法解析的响应抛错"""
    mock_ai.client.chat.completions.create.return_value = _make_completion("not json at all")

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    with pytest.raises(Exception, match="内容识别失败"):
        mock_ai.get_content_ai("b64", pil_img, "区域")


# ===== 辅助方法 =====

def test_extract_json_pure_json():
    """提取纯 JSON 字符串"""
    ai = AIControl(api_key="x", base_url="x", model="x")
    result = ai._extract_json('{"found": true}')
    assert result == '{"found": true}'


def test_extract_json_code_block():
    """提取 ```json ... ``` 块"""
    ai = AIControl(api_key="x", base_url="x", model="x")
    content = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
    result = ai._extract_json(content)
    assert result == '{"key": "value"}'


def test_extract_json_invalid():
    """无法提取时返回 None"""
    ai = AIControl(api_key="x", base_url="x", model="x")
    result = ai._extract_json("random text")
    assert result is None


# ===== 区域结构化描述 (describe_region_ai) =====

def test_describe_region_ai_success(mock_ai):
    """正常返回结构化描述（4 字段齐全）"""
    mock_response = json.dumps({
        "description": {
            "layout": "上下结构：顶部标题栏 + 中部表单 + 底部按钮",
            "icons": ["返回箭头图标", "搜索图标", "密码显示切换图标"],
            "text": "标题：登录\n账号：\n密码：\n[登录按钮]",
            "intro": "这是一个登录表单，用户输入账号密码后点击登录进入系统"
        }
    })
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    result = mock_ai.describe_region_ai("b64", pil_img, "登录表单区域")

    assert "description" in result
    desc = result["description"]
    assert desc["layout"].startswith("上下结构")
    assert len(desc["icons"]) == 3
    assert "登录" in desc["text"]
    assert "登录表单" in desc["intro"]
    # 关键断言：不含 bbox 字段
    assert "bbox" not in result


def test_describe_region_ai_with_empty_fields(mock_ai):
    """部分字段为空（icons 空数组、text 空串）"""
    mock_response = json.dumps({
        "description": {
            "layout": "单行",
            "icons": [],
            "text": "",
            "intro": "占位区域"
        }
    })
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    result = mock_ai.describe_region_ai("b64", pil_img, "占位区域")

    desc = result["description"]
    assert desc["layout"] == "单行"
    assert desc["icons"] == []
    assert desc["text"] == ""
    assert desc["intro"] == "占位区域"
    assert "bbox" not in result


def test_describe_region_ai_handles_code_block(mock_ai):
    """识别 ```json ... ``` 代码块包裹"""
    content = (
        '```json\n'
        '{"description": {"layout": "网格布局", "icons": ["滤镜1", "滤镜2"], '
        '"text": "滤镜列表", "intro": "图片滤镜选择区"}}\n'
        '```'
    )
    mock_ai.client.chat.completions.create.return_value = _make_completion(content)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    result = mock_ai.describe_region_ai("b64", pil_img, "滤镜区")

    desc = result["description"]
    assert desc["layout"] == "网格布局"
    assert desc["icons"] == ["滤镜1", "滤镜2"]
    assert "bbox" not in result


def test_describe_region_ai_missing_description_field(mock_ai):
    """AI 漏掉 description 字段时,返回空 dict（不抛错）"""
    mock_response = json.dumps({"foo": "bar"})
    mock_ai.client.chat.completions.create.return_value = _make_completion(mock_response)

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    result = mock_ai.describe_region_ai("b64", pil_img, "任意区域")

    assert result == {"description": {}}
    assert "bbox" not in result


def test_describe_region_ai_unparseable_raises(mock_ai):
    """无法解析的响应抛错（与 get_content_ai 行为一致）"""
    mock_ai.client.chat.completions.create.return_value = _make_completion("not json at all")

    pil_img = Image.new("RGB", (1000, 1000), color="red")
    with pytest.raises(Exception, match="内容识别失败"):
        mock_ai.describe_region_ai("b64", pil_img, "区域")