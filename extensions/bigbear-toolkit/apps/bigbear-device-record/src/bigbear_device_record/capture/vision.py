"""多模态 vision 分析。移植自 bigbear-web-record，逻辑一致：
- 用 OpenAI 兼容接口调用多模态模型
- 期望返回 JSON: {interface_desc, layout_desc, elements_desc}
- 容错：解析失败返回 None（不抛异常）"""
import base64
import json
from typing import Optional

from ..debug import debug, error


def _get_client(api_key: str, base_url: str):
    """延迟 import openai，便于未安装时优雅降级。"""
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url)


_PROMPT = """请分析这张页面截图，返回一个纯JSON对象，不要包含任何其他文字、代码块标记或解释。

JSON格式：
{
  "interface_desc": "界面整体描述（一段话）",
  "layout_desc": "布局描述",
  "elements_desc": "元素描述列表"
}

只返回JSON，不要有其他内容。"""


def analyze_screenshot_with_vision(
    screenshot_path: str,
    api_key: str,
    base_url: str,
    model: str = "qwen3.6-flash-2026-04-16",
) -> Optional[dict]:
    try:
        with open(screenshot_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        client = _get_client(api_key, base_url)
        completion = client.chat.completions.create(
            model=model,
            max_tokens=10204,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                {"type": "text", "text": _PROMPT},
            ]}],
        )
        result_text = json.loads(completion.model_dump_json())['choices'][0]['message']['content']
        debug(f"Vision raw result (len={len(result_text)}): {result_text[:500]}")
        # 提取 markdown ```json ... ``` 块（如有）
        if "```json" in result_text:
            start = result_text.find("```json") + 7
            end = result_text.find("```", start)
            result_text = result_text[start:end].strip()
        elif "```" in result_text:
            start = result_text.find("```") + 3
            end = result_text.find("```", start)
            result_text = result_text[start:end].strip()
        result_text = result_text.strip()
        try:
            result = json.loads(result_text)
            debug(f"Vision parsed result: {result}")
            return result
        except json.JSONDecodeError as e:
            debug(f"JSON parse failed at pos {e.pos}: {e.msg}")
            # 尝试从乱码中提取首个 JSON 对象
            s, e_idx = result_text.find('{'), result_text.rfind('}')
            if s != -1 and e_idx != -1 and e_idx > s:
                extracted = result_text[s:e_idx+1]
                debug(f"Trying extracted JSON (len={len(extracted)}): {extracted[:300]}")
                try:
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    pass
            error(f"Vision JSON parse failed: {e}")
            return None
    except Exception as e:
        error(f"Vision analysis failed: {type(e).__name__}: {e}")
        return None
