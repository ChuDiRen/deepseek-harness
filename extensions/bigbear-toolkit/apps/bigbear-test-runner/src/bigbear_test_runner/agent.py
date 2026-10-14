"""构造 AgentScope Agent，并把流式事件写入 stdout/stderr。"""
from __future__ import annotations

import os
import sys

from bigbear_test_runner.events import _format_tool_input, _summarize_event
from bigbear_test_runner.dynamic_function import build_dynamic_function_tool
from bigbear_test_runner.plan_loader import ProjectBundle


# ---- Windows GBK 控制台兼容 ----
# agent 流式输出可能包含 emoji(如 ✅)等 Unicode 字符,Windows 默认 GBK 控制台无法编码,
# 会抛 `UnicodeEncodeError: 'gbk' codec can't encode character '✅'`。
# 这里把 stdout/stderr 重配为 UTF-8 并启用 errors='replace' 兜底,
# 任何无法编码的字符会被替换为 '?' 而不是中断整个 run_streaming 循环。
def _reconfigure_console_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # Python < 3.7 或非标准流
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            # 已被重定向到不支持 reconfigure 的对象(如 pytest capture),
            # 静默忽略,后续 print 会自行处理或抛出更明确的错误。
            pass


_reconfigure_console_streams()


# ---- 默认值 ----
DEFAULT_MODEL = "qwen-plus"
DEFAULT_NAME = "bigbear-test-runner"
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_MAX_RETRIES = 1


class _AgentMissingKeyError(Exception):
    """缺 AGENT_AI_API_KEY 时抛出。"""


def build_agent(
    skills_dirs: list[str] | None = None,
    *,
    system_prompt: str = "",
    project: ProjectBundle | None = None,
):
    """组装 agentscope Agent。

    Args:
        skills_dirs: skill 根目录列表(可重复,散落多位置)。
        system_prompt:由调用方组装好的系统提示词。
        project:plan_loader 已解析的项目数据。动态函数工具自行提取启用函数和环境。
    """
    from agentscope.agent import Agent
    from agentscope.credential import DashScopeCredential
    from agentscope.model import DashScopeChatModel
    from agentscope.permission import PermissionContext, PermissionMode
    from agentscope.skill import LocalSkillLoader
    from agentscope.state import AgentState
    from agentscope.tool import Bash, Toolkit

    api_key = os.environ.get("AGENT_AI_API_KEY")
    if not api_key:
        raise _AgentMissingKeyError(
            "缺少环境变量 AGENT_AI_API_KEY,请在 .env 中配置后重试。"
        )
    cred_kwargs: dict = {"api_key": api_key}
    base_url = os.environ.get("AGENT_AI_BASE_URL")
    if base_url:
        cred_kwargs["base_url"] = base_url
    credential = DashScopeCredential(**cred_kwargs)

    timeout_raw = os.environ.get("AGENT_AI_TIMEOUT", "").strip()
    try:
        timeout = float(timeout_raw) if timeout_raw else DEFAULT_TIMEOUT_S
    except ValueError:
        timeout = DEFAULT_TIMEOUT_S

    retries_raw = os.environ.get("AGENT_AI_MAX_RETRIES", "").strip()
    try:
        max_retries = int(retries_raw) if retries_raw else DEFAULT_MAX_RETRIES
    except ValueError:
        max_retries = DEFAULT_MAX_RETRIES

    model = DashScopeChatModel(
        credential=credential,
        model=os.environ.get("AGENT_AI_MODEL", DEFAULT_MODEL),
        max_retries=max_retries,
        client_kwargs={"timeout": timeout},
    )

    # 测试执行无需文件工具。web/api 使用 Bash 调 playwright-cli；
    # dynamic-function 只使用专用工具。
    tools = [Bash()]
    if project is not None:
        tools.append(build_dynamic_function_tool(project))

    toolkit_kwargs: dict = {"tools": tools}
    if skills_dirs:
        toolkit_kwargs["skills_or_loaders"] = [
            LocalSkillLoader(directory=p, scan_subdir=True)
            for p in skills_dirs
        ]
    toolkit = Toolkit(**toolkit_kwargs)

    # CLI 没有交互式确认界面，命令行启动即视为允许执行计划中的工具调用。
    state = AgentState(
        permission_context=PermissionContext(mode=PermissionMode.BYPASS),
    )
    return Agent(
        name=DEFAULT_NAME,
        system_prompt=system_prompt,
        model=model,
        toolkit=toolkit,
        state=state,
    )


async def run_streaming(
    user_message: str,
    *,
    flow_id: str = "",
    system_prompt: str = "",
    debug: bool = False,
    skills_dirs: list[str] | None = None,
    project: ProjectBundle | None = None,
) -> str:
    """流式打印 agent 对 user_message 的回复到 stdout。

    Args:
        user_message:单个 Task 的 markdown(由 prompt_builder.build_task_message 产出)。
        flow_id:当前 Flow ID,用于区分并发执行日志。
        system_prompt:agent system_prompt 文本(由 prompt_builder.build_system_prompt 产出)。
        debug:是否打印每条非 TEXT 事件的摘要。
        skills_dirs:skill 根目录列表。
        project:plan_loader 已解析的项目数据,由动态函数工具解析运行时配置。

    阶段日志(2026-09-10 加强,默认开启,debug 时打印每条事件):
      - building / ready / sending / entering reply_stream / reply received / loop ended
    """
    from agentscope.message import UserMsg

    log_prefix = f"[agent:{flow_id}]" if flow_id else "[agent]"
    n_skills = len(skills_dirs or [])
    print(
        f"{log_prefix} building (skills={n_skills}, sys_prompt={len(system_prompt)} chars)...",
        file=sys.stderr,
        flush=True,
    )
    agent = build_agent(
        skills_dirs=skills_dirs,
        system_prompt=system_prompt,
        project=project,
    )
    model_name = getattr(getattr(agent, "model", None), "model", "?")
    print(
        f"{log_prefix} ready: name={agent.name!r} model={model_name!r}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"{log_prefix} sending message ({len(user_message)} chars)...",
        file=sys.stderr,
        flush=True,
    )

    user_msg = UserMsg(name="user", content=user_message)
    print(f"{log_prefix} entering reply_stream loop...", file=sys.stderr, flush=True)

    event_count = 0
    text_started = False
    text_parts: list[str] = []
    pending_line = ""
    # 2026-09-10:tool call input 累积字典,key=tool_call_id,
    # value=累积中的 JSON 输入字符串(由 TOOL_CALL_DELTA.delta 拼接)
    accumulated_inputs: dict[str, str] = {}
    async for event in agent.reply_stream(user_msg):
        event_count += 1
        et = getattr(event, "type", None)
        et_name = getattr(et, "name", str(et))
        if et_name == "TEXT_BLOCK_DELTA":
            if not text_started:
                print(
                    f"{log_prefix} reply received after {event_count} events",
                    file=sys.stderr,
                    flush=True,
                )
                text_started = True
            text_parts.append(event.delta)
            pending_line += event.delta
            while "\n" in pending_line:
                line, pending_line = pending_line.split("\n", 1)
                print(line, flush=True)
        elif et_name == "TOOL_CALL_START":
            # 新工具调用开始:初始化累积 buffer
            tid = getattr(event, "tool_call_id", None)
            if tid is not None:
                accumulated_inputs[tid] = ""
        elif et_name == "TOOL_CALL_DELTA":
            # 累积 input JSON 片段
            tid = getattr(event, "tool_call_id", None)
            if tid is not None:
                accumulated_inputs[tid] = accumulated_inputs.get(tid, "") + getattr(
                    event, "delta", ""
                )
        elif et_name == "TOOL_CALL_END":
            # input 已累积完整,打印
            if debug:
                tid = getattr(event, "tool_call_id", None)
                if tid is not None and accumulated_inputs.get(tid):
                    print(
                        f"{log_prefix}   input: {_format_tool_input(accumulated_inputs[tid])}",
                        file=sys.stderr,
                        flush=True,
                    )
        elif et_name == "TOOL_RESULT_START":
            # 兜底:如果 TOOL_CALL_END 没拿到,这里再打一次
            if debug:
                tid = getattr(event, "tool_call_id", None)
                if tid is not None and accumulated_inputs.get(tid):
                    print(
                        f"{log_prefix}   input: {_format_tool_input(accumulated_inputs[tid])}",
                        file=sys.stderr,
                        flush=True,
                    )
        elif debug:
            # debug 模式打印每条非 TEXT 事件的摘要
            summary = _summarize_event(event)
            print(f"{log_prefix} #{event_count} {summary}", file=sys.stderr, flush=True)
    if pending_line:
        print(pending_line, flush=True)
    print(
        f"{log_prefix} reply_stream loop ended, total events={event_count}",
        file=sys.stderr,
        flush=True,
    )
    return "".join(text_parts)
