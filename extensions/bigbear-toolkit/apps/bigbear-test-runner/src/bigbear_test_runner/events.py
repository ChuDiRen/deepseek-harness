"""agentscope 事件摘要工具。

职责:把 agentscope 的事件对象浓缩成可读字符串,供 debug 日志使用。
duck typing 设计,不依赖具体事件类(避免 agentscope API 调整时大面积改动)。

公开函数:
  - _summarize_event(event)         一行摘要
  - _format_tool_input(input_obj)   tool call input 的 key=value 摘要
"""
from __future__ import annotations

# 单条 delta 截断长度:超过这个字符就截 + "...",避免长回复刷屏 stderr
_DELTA_MAX_LEN = 200
# 单个字段值截断长度:tool call input 里 command/content 可能很长
_INPUT_MAX_VALUE_LEN = 300


def _format_tool_input(input_obj: object) -> str:
    """把 tool call 的 input 浓缩成可读字符串。

    input 可能是 dict(JSON 解析后的)或 str(原始 JSON 字符串)。
    返回形如 'command="..." description="..." file_path="..."' 的 key=value 列表,
    单值超长截断。空 dict 返回 ''。
    """
    if isinstance(input_obj, dict):
        items = input_obj.items()
    elif isinstance(input_obj, str):
        import json

        try:
            parsed = json.loads(input_obj)
            if isinstance(parsed, dict):
                items = parsed.items()
            else:
                items = [("input", str(parsed))]
        except (ValueError, TypeError):
            items = [("input", input_obj)]
    elif input_obj is None:
        return ""
    else:
        items = [("input", str(input_obj))]

    parts: list[str] = []
    for k, v in items:
        s = str(v)
        if len(s) > _INPUT_MAX_VALUE_LEN:
            s = s[:_INPUT_MAX_VALUE_LEN] + "..."
        parts.append(f"{k}={s!r}")
    return " ".join(parts)


def _summarize_event(event: object) -> str:
    """把 agentscope 事件浓缩成一行可读字符串,供 debug 日志打印。

    设计:
      - duck typing:不依赖具体事件类(避免 agentscope API 调整导致代码改动)
      - TEXT/THINKING/TOOL_RESULT delta:返回 "(text) ...",带内容预览
      - TOOL_CALL_START/END/RESULT_START:返回工具名
      - REPLY/MODEL 边界:返回简短状态
      - 未知事件:返回带 type 名的兜底,不抛
    """
    et = getattr(event, "type", None)
    name = getattr(et, "name", str(et))

    # 流式文本/思考/工具结果 delta:带内容预览 + 截断
    if name in ("TEXT_BLOCK_DELTA", "THINKING_BLOCK_DELTA", "TOOL_RESULT_TEXT_DELTA"):
        delta = getattr(event, "delta", "")
        tag = {
            "TEXT_BLOCK_DELTA": "text",
            "THINKING_BLOCK_DELTA": "thinking",
            "TOOL_RESULT_TEXT_DELTA": "tool-result",
        }[name]
        if len(delta) > _DELTA_MAX_LEN:
            delta = delta[:_DELTA_MAX_LEN] + "..."
        return f"({tag}) {delta}"

    # 工具调用开始 / 工具结果开始:展示工具名
    if name == "TOOL_CALL_START":
        return f"tool call: name={getattr(event, 'tool_call_name', '?')!r} id={getattr(event, 'tool_call_id', '?')!r}"
    if name == "TOOL_RESULT_START":
        return f"tool result: name={getattr(event, 'tool_call_name', '?')!r} id={getattr(event, 'tool_call_id', '?')!r}"

    # 模型调用边界
    if name == "MODEL_CALL_START":
        return f"model call: model={getattr(event, 'model_name', '?')!r}"
    if name == "MODEL_CALL_END":
        return (
            f"model call end: in={getattr(event, 'input_tokens', '?')} "
            f"out={getattr(event, 'output_tokens', '?')} "
            f"reason={getattr(event, 'finished_reason', '?')!r}"
        )

    # Reply 边界
    if name == "REPLY_START":
        return f"reply start: name={getattr(event, 'name', '?')!r}"
    if name == "REPLY_END":
        return (
            f"reply end: reason={getattr(event, 'finished_reason', '?')!r} "
            f"error={getattr(event, 'error', None)!r}"
        )

    # 提示块
    if name == "HINT_BLOCK":
        return f"hint: source={getattr(event, 'source', '?')!r} {getattr(event, 'hint', '')}"

    # 等用户确认(我们走 BYPASS 不会触发,但 debug 时仍可见)
    if name == "REQUIRE_USER_CONFIRM":
        tool_calls = getattr(event, "tool_calls", []) or []
        names = [getattr(t, "name", "?") for t in tool_calls]
        return f"require user confirm: tools={names!r}"

    # 累积中/无关键信息的事件:简短标注即可
    if name == "TOOL_CALL_DELTA":
        return "tool call delta: (accumulating input)"
    if name == "TOOL_CALL_END":
        return f"tool call end: id={getattr(event, 'tool_call_id', '?')!r}"
    if name == "TOOL_RESULT_DATA_DELTA":
        return f"tool result data: media={getattr(event, 'media_type', '?')!r} url={getattr(event, 'url', '')}"
    if name == "TOOL_RESULT_END":
        return f"tool result end: id={getattr(event, 'tool_call_id', '?')!r} state={getattr(event, 'state', '?')!r}"

    return f"(other) type={name}"
