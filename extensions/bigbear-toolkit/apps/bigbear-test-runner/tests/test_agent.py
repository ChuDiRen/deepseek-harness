"""bigbear-test-runner agent 模块的 smoke 测试。

不依赖真实 API:用 sys.modules 注入假 agentscope 模块,验证:
- build_agent() 把 AGENT_AI_* 环境变量正确映射到 agentscope 入参
- run_streaming() 把 TEXT_BLOCK_DELTA 事件内容写到 stdout
- 缺失 AGENT_AI_API_KEY 时抛 _AgentMissingKeyError
"""
from __future__ import annotations

import asyncio
import os
import sys
import types
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import pytest


# ---- 替身 dataclass / enum:模拟 agentscope 的事件类型 ----

class _FakeEventType(Enum):
    TEXT_BLOCK_DELTA = "text_block_delta"
    THINKING_BLOCK_DELTA = "thinking_block_delta"
    TOOL_CALL_START = "tool_call_start"
    TOOL_RESULT_START = "tool_result_start"
    TOOL_RESULT_TEXT_DELTA = "tool_result_text_delta"
    MODEL_CALL_START = "model_call_start"
    MODEL_CALL_END = "model_call_end"
    REPLY_START = "reply_start"
    REPLY_END = "reply_end"
    HINT_BLOCK = "hint_block"
    REQUIRE_USER_CONFIRM = "require_user_confirm"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_END = "tool_call_end"
    TOOL_RESULT_DATA_DELTA = "tool_result_data_delta"
    TOOL_RESULT_END = "tool_result_end"
    OTHER = "other"


@dataclass
class _FakeEvent:
    """模拟 agentscope TextBlockDeltaEvent 的字段名(2026-09-10 修复:真实字段是 delta 不是 content)。"""

    type: _FakeEventType
    delta: str = ""


def _make_fake_user_msg(**kwargs: Any) -> Any:
    """模拟 agentscope.message.UserMsg,只要能被构造就行。"""
    return types.SimpleNamespace(**kwargs)


# ---- fixtures ----

@pytest.fixture
def fake_agentscope():
    """用 sys.modules 注入一个假 agentscope,让函数体内的 from agentscope.xxx import YYY
    拿到我们的 Fake 类。这样测试无需安装真实 agentscope 包。

    yield 风格:测试结束后恢复 sys.modules,避免污染其他测试。
    """
    captured: dict[str, Any] = {
        "credential_kwargs": [],
        "model_kwargs": [],
        "agent_kwargs": [],
        "toolkit_kwargs": [],
        "loader_kwargs": [],
        "events": [],
    }

    class FakeCredential:
        def __init__(self, **kwargs: Any) -> None:
            captured["credential_kwargs"].append(kwargs)

    class FakeModel:
        def __init__(self, **kwargs: Any) -> None:
            captured["model_kwargs"].append(kwargs)

    class FakeToolkit:
        def __init__(self, **kwargs: Any) -> None:
            captured["toolkit_kwargs"].append(kwargs)
            self.kwargs = kwargs

    class FakeFunctionTool:
        def __init__(self, func, **kwargs: Any) -> None:
            self.func = func
            self.kwargs = kwargs
            self.name = kwargs.get("name", getattr(func, "__name__", "function"))

    class FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured["agent_kwargs"].append(kwargs)
            self.kwargs = kwargs
            # 把 agentscope Agent 的关键字段挂到 self,模拟 duck typing
            self.name = kwargs.get("name", "fake-agent")
            self.model = kwargs.get("model")
            # state 通常是 AgentState 实例(BYPass mode 测试需要读它)
            self.state = kwargs.get("state")

        async def reply_stream(self, user_msg: Any):
            for ev in captured.get("events", []):
                yield ev

    class FakeLocalSkillLoader:
        """模拟 agentscope.skill.LocalSkillLoader(directory=, scan_subdir=)。"""

        def __init__(
            self,
            directory: str | None = None,
            scan_subdir: bool = False,
            **kwargs: Any,
        ) -> None:
            captured["loader_kwargs"].append(
                {"directory": directory, "scan_subdir": scan_subdir},
            )
            self.directory = directory
            self.scan_subdir = scan_subdir

    class FakeBash:
        def __init__(self) -> None:
            pass

    # 记下原始 sys.modules 里已有的 agentscope.* 项(若有),便于恢复
    # 关键:不替换 sys.modules['agentscope'] 顶层包(否则 import 失败),
    # 只在 sys.modules 里覆盖子模块;并把 fake 子模块挂到真实包上。
    # 但 agentscope.message **不替换**(相对 import 会失败,state/toolkit 等子模块
    # 依赖它),只 monkeypatch UserMsg 为 fake。
    to_restore: dict[str, Any] = {}
    fake_names = [
        "agentscope.credential",
        "agentscope.model",
        "agentscope.agent",
        "agentscope.tool",
        "agentscope.event",
        "agentscope.skill",
    ]
    for name in fake_names:
        if name in sys.modules:
            to_restore[name] = sys.modules[name]

    # 确保真实 agentscope 包被 import(并因此在 sys.modules 里),后续 attribute
    # 代理需要真实包存在
    if "agentscope" not in sys.modules:
        import agentscope  # noqa: F401

    real_pkg = sys.modules["agentscope"]
    backup_attrs: dict[str, Any] = {}
    fake_subattrs: dict[str, Any] = {
        "credential": types.ModuleType("agentscope.credential"),
        "model": types.ModuleType("agentscope.model"),
        "agent": types.ModuleType("agentscope.agent"),
        "tool": types.ModuleType("agentscope.tool"),
        "event": types.ModuleType("agentscope.event"),
        "skill": types.ModuleType("agentscope.skill"),
    }

    mod_credential = fake_subattrs["credential"]
    mod_credential.DashScopeCredential = FakeCredential  # type: ignore[attr-defined]
    sys.modules["agentscope.credential"] = mod_credential
    backup_attrs["credential"] = getattr(real_pkg, "credential", None)
    real_pkg.credential = mod_credential  # type: ignore[attr-defined]

    mod_model = fake_subattrs["model"]
    mod_model.DashScopeChatModel = FakeModel  # type: ignore[attr-defined]
    sys.modules["agentscope.model"] = mod_model
    backup_attrs["model"] = getattr(real_pkg, "model", None)
    real_pkg.model = mod_model  # type: ignore[attr-defined]

    mod_agent = fake_subattrs["agent"]
    mod_agent.Agent = FakeAgent  # type: ignore[attr-defined]
    sys.modules["agentscope.agent"] = mod_agent
    backup_attrs["agent"] = getattr(real_pkg, "agent", None)
    real_pkg.agent = mod_agent  # type: ignore[attr-defined]

    mod_tool = fake_subattrs["tool"]
    mod_tool.Toolkit = FakeToolkit  # type: ignore[attr-defined]
    mod_tool.Bash = FakeBash  # type: ignore[attr-defined]
    mod_tool.FunctionTool = FakeFunctionTool  # type: ignore[attr-defined]
    sys.modules["agentscope.tool"] = mod_tool
    backup_attrs["tool"] = getattr(real_pkg, "tool", None)
    real_pkg.tool = mod_tool  # type: ignore[attr-defined]

    mod_event = fake_subattrs["event"]
    mod_event.EventType = _FakeEventType  # type: ignore[attr-defined]
    sys.modules["agentscope.event"] = mod_event
    backup_attrs["event"] = getattr(real_pkg, "event", None)
    real_pkg.event = mod_event  # type: ignore[attr-defined]

    # agentscope.message 不替换(相对 import 会失败),只 monkeypatch UserMsg
    import agentscope.message as _real_message  # noqa: F401
    backup_attrs["_message_UserMsg"] = _real_message.UserMsg
    _real_message.UserMsg = _make_fake_user_msg  # type: ignore[attr-defined]

    mod_skill = fake_subattrs["skill"]
    mod_skill.LocalSkillLoader = FakeLocalSkillLoader  # type: ignore[attr-defined]
    sys.modules["agentscope.skill"] = mod_skill
    backup_attrs["skill"] = getattr(real_pkg, "skill", None)
    real_pkg.skill = mod_skill  # type: ignore[attr-defined]

    yield captured

    # teardown:恢复 sys.modules 与真实包属性
    for name in fake_names:
        sys.modules.pop(name, None)
    for name, mod in to_restore.items():
        sys.modules[name] = mod
    # 恢复 real_pkg 属性(包括 message.UserMsg)
    for name, attr in backup_attrs.items():
        if name == "_message_UserMsg":
            _real_message.UserMsg = attr
            continue
        if attr is None:
            try:
                delattr(real_pkg, name)
            except AttributeError:
                pass
        else:
            setattr(real_pkg, name, attr)


# ---- 测试 1:AGENT_AI_API_KEY 缺失时抛 _AgentMissingKeyError ----

def test_build_agent_missing_api_key_raises(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """2026-09-10 骨架:AGENT_AI_API_KEY 缺失时 build_agent() 抛 _AgentMissingKeyError。

    用 fake_agentscope fixture 注入假 agentscope 模块,避免测试环境需要安装 agentscope。
    """
    monkeypatch.delenv("AGENT_AI_API_KEY", raising=False)

    from bigbear_test_runner.agent import _AgentMissingKeyError, build_agent

    with pytest.raises(_AgentMissingKeyError) as exc_info:
        build_agent()
    assert "AGENT_AI_API_KEY" in str(exc_info.value)


# ---- 测试 2:环境变量正确映射到 DashScopeCredential / DashScopeChatModel / Agent ----

def test_build_agent_maps_env_to_agentscope_args(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """AGENT_AI_API_KEY / AGENT_AI_MODEL / AGENT_AI_BASE_URL 应正确传入 agentscope。

    2026-09-10:agentscope 2.0.8 的 DashScopeChatModel 走 OpenAI 兼容协议,
    base_url 必须由 DashScopeCredential 持有,而不是模型。修复 #a6f3322 后的断言。
    """
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key-abc")
    monkeypatch.setenv("AGENT_AI_MODEL", "qwen-max")
    monkeypatch.setenv("AGENT_AI_BASE_URL", "https://example.com/v1")
    monkeypatch.delenv("AGENTSCOPE_MODEL", raising=False)

    from bigbear_test_runner.agent import build_agent

    build_agent()

    # base_url 应该传到 credential,不是 model
    assert fake_agentscope["credential_kwargs"] == [
        {"api_key": "test-key-abc", "base_url": "https://example.com/v1"},
    ]
    assert len(fake_agentscope["model_kwargs"]) == 1
    model_kwargs = fake_agentscope["model_kwargs"][0]
    assert model_kwargs["model"] == "qwen-max"
    # 模型层不应该出现 server_url / base_url —— 它们是 credential 的职责
    assert "server_url" not in model_kwargs
    assert "base_url" not in model_kwargs

    assert len(fake_agentscope["agent_kwargs"]) == 1
    agent_kwargs = fake_agentscope["agent_kwargs"][0]
    assert agent_kwargs["name"] == "bigbear-test-runner"
    # 2026-09-10 改造:build_agent 不再写默认 system_prompt,由 cli 调
    # prompt_builder.build_system_prompt 后透传;未传时应为空串。
    assert agent_kwargs["system_prompt"] == ""


def test_build_agent_uses_default_model_when_unset(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """AGENT_AI_MODEL 未设置时,默认 qwen-plus;AGENT_AI_BASE_URL 未设置时,credential 也不带 base_url。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.delenv("AGENT_AI_MODEL", raising=False)
    monkeypatch.delenv("AGENT_AI_BASE_URL", raising=False)

    from bigbear_test_runner.agent import build_agent

    build_agent()

    model_kwargs = fake_agentscope["model_kwargs"][0]
    assert model_kwargs["model"] == "qwen-plus"
    # base_url 未设置时,credential_kwargs 只含 api_key,不含 base_url
    assert fake_agentscope["credential_kwargs"] == [{"api_key": "test-key"}]


# ---- 测试 3:run_streaming 把 TEXT_BLOCK_DELTA 写入 stdout ----

def test_run_streaming_writes_text_block_delta_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
    capsys: pytest.CaptureFixture,
) -> None:
    """run_streaming 收到 TEXT_BLOCK_DELTA 事件时,event.delta 被写入 stdout 并 flush。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")

    fake_agentscope["events"] = [
        _FakeEvent(type=_FakeEventType.TEXT_BLOCK_DELTA, delta="你好,"),
        _FakeEvent(type=_FakeEventType.TEXT_BLOCK_DELTA, delta="我是 Friday。"),
        _FakeEvent(type=_FakeEventType.OTHER, delta="<ignored>"),
    ]

    from bigbear_test_runner.agent import run_streaming

    asyncio.run(run_streaming("hello"))

    captured = capsys.readouterr()
    assert captured.out == "你好,我是 Friday。\n"


# ---- 测试 4:run_streaming 缺失 AGENT_AI_API_KEY 时抛 _AgentMissingKeyError ----

def test_run_streaming_missing_key_propagates_error(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """run_streaming 不吞 _AgentMissingKeyError,而是向上抛。"""
    monkeypatch.delenv("AGENT_AI_API_KEY", raising=False)

    from bigbear_test_runner.agent import _AgentMissingKeyError, run_streaming

    with pytest.raises(_AgentMissingKeyError):
        asyncio.run(run_streaming("hello"))


# ---- 测试 5:--skills-dir 透传给 Toolkit(skills_or_loaders=...) ----

def test_build_agent_no_skills_dirs_passes_empty(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """不传 skills_dirs 时,Toolkit 不带 skills_or_loaders(行为不变)。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")

    from bigbear_test_runner.agent import build_agent

    build_agent()

    assert len(fake_agentscope["toolkit_kwargs"]) == 1
    toolkit_kwargs = fake_agentscope["toolkit_kwargs"][0]
    # 不带 skills_or_loaders(或为 None/空),与旧行为一致
    assert not toolkit_kwargs.get("skills_or_loaders")
    # 同时不应该构造任何 LocalSkillLoader
    assert fake_agentscope["loader_kwargs"] == []


def test_build_agent_single_skills_dir(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """传 1 个 skills_dir 时,构造 LocalSkillLoader(directory=, scan_subdir=True)。

    2026-09-10 修复 #9c82773:bigbear 的 skill 布局是 skills/<name>/SKILL.md,
    必须 scan_subdir=True,否则根目录无 SKILL.md 就找不到任何 skill。
    """
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")

    from bigbear_test_runner.agent import build_agent

    build_agent(skills_dirs=["/path/to/skills"])

    # LocalSkillLoader 应被以 (directory=path, scan_subdir=True) 调用
    assert fake_agentscope["loader_kwargs"] == [
        {"directory": "/path/to/skills", "scan_subdir": True},
    ]
    # Toolkit 收到的 skills_or_loaders 是 loader 实例列表
    toolkit_kwargs = fake_agentscope["toolkit_kwargs"][0]
    assert len(toolkit_kwargs["skills_or_loaders"]) == 1
    assert toolkit_kwargs["skills_or_loaders"][0].directory == "/path/to/skills"
    assert toolkit_kwargs["skills_or_loaders"][0].scan_subdir is True


def test_build_agent_multiple_skills_dirs(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """传多个 skills_dir 时,每个都构造一个 LocalSkillLoader(scan_subdir=True),顺序保持。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")

    from bigbear_test_runner.agent import build_agent

    build_agent(skills_dirs=["/skills-a", "/skills-b", "../bigbear-web-cli/skiils"])

    assert fake_agentscope["loader_kwargs"] == [
        {"directory": "/skills-a", "scan_subdir": True},
        {"directory": "/skills-b", "scan_subdir": True},
        {"directory": "../bigbear-web-cli/skiils", "scan_subdir": True},
    ]


def test_run_streaming_forwards_skills_dirs(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """run_streaming 接收 skills_dirs 后,build_agent 内的 LocalSkillLoader 收到正确入参。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    fake_agentscope["events"] = []

    from bigbear_test_runner.agent import run_streaming

    asyncio.run(run_streaming("hi", skills_dirs=["/p1", "/p2"]))

    assert fake_agentscope["loader_kwargs"] == [
        {"directory": "/p1", "scan_subdir": True},
        {"directory": "/p2", "scan_subdir": True},
    ]


# ---- 测试 6:默认装上 agentscope 内置工具 ----

def _tool_kinds(fake_agentscope: dict[str, Any]) -> list[str]:
    """从 toolkit_kwargs 提取装入的工具类型名列表(顺序保持)。"""
    assert fake_agentscope["toolkit_kwargs"], "Toolkit 未被构造"
    tools = fake_agentscope["toolkit_kwargs"][0].get("tools") or []
    return [type(t).__name__ for t in tools]


def test_build_agent_default_builtin_tools(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """未传项目时只装 Bash,不注册无意义的空动态函数工具。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.setattr("sys.platform", "linux")  # 不管平台都应一致

    from bigbear_test_runner.agent import build_agent

    build_agent()

    assert _tool_kinds(fake_agentscope) == ["FakeBash"]


def test_build_agent_registers_dynamic_function_tool(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
    tmp_path,
) -> None:
    """动态函数路径和环境应固化进专用工具,无需 agent 拼 shell。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    script = tmp_path / "中文目录" / "demo.py"

    from bigbear_test_runner.agent import build_agent
    from bigbear_test_runner.plan_loader import (
        DynamicFunction,
        EnvVars,
        ProjectBundle,
    )

    build_agent(
        project=ProjectBundle(
            project_dir=tmp_path,
            env=EnvVars(env_name="default", values={"TOKEN": "secret"}),
            dynamic_functions=[
                DynamicFunction(
                    function_code="demo",
                    function_type="通用工具",
                    abs_path=script,
                ),
            ],
        ),
    )

    tools = fake_agentscope["toolkit_kwargs"][0]["tools"]
    dynamic_tool = next(
        tool
        for tool in tools
        if getattr(tool, "name", "") == "run_dynamic_function"
    )
    assert callable(dynamic_tool.func)


# ---- 测试 7:超时/重试配置 (2026-09-10 修复 hang) ----

def test_build_agent_default_timeout_and_retries(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """默认 max_retries=1 + client_kwargs.timeout=30,避免 hang。

    agentscope 默认 max_retries=3 × openai 默认 timeout=600s = 单次失败
    最多 hang 30 分钟;骨架阶段默认压短到 30 秒 1 次重试。
    """
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.delenv("AGENT_AI_TIMEOUT", raising=False)
    monkeypatch.delenv("AGENT_AI_MAX_RETRIES", raising=False)

    from bigbear_test_runner.agent import build_agent

    build_agent()

    model_kwargs = fake_agentscope["model_kwargs"][0]
    assert model_kwargs["max_retries"] == 1
    assert model_kwargs["client_kwargs"] == {"timeout": 30}


def test_build_agent_timeout_overridable_via_env(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """AGENT_AI_TIMEOUT / AGENT_AI_MAX_RETRIES 覆盖默认(对齐 bigbear-test-runner)。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_AI_TIMEOUT", "5")
    monkeypatch.setenv("AGENT_AI_MAX_RETRIES", "0")

    from bigbear_test_runner.agent import build_agent

    build_agent()

    model_kwargs = fake_agentscope["model_kwargs"][0]
    assert model_kwargs["max_retries"] == 0
    assert model_kwargs["client_kwargs"] == {"timeout": 5}


def test_build_agent_timeout_invalid_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """AGENT_AI_TIMEOUT 非数字 → fallback 到默认 30,而不是抛异常让 CLI 崩。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_AI_TIMEOUT", "not-a-number")

    from bigbear_test_runner.agent import build_agent

    build_agent()

    model_kwargs = fake_agentscope["model_kwargs"][0]
    assert model_kwargs["client_kwargs"] == {"timeout": 30}


# ---- 测试 9:事件摘要让 debug 日志可读 ----

from bigbear_test_runner.events import _summarize_event


# ---- 测试 10:tool call input 摘要(让用户看到 agent 实际跑什么命令) ----

from bigbear_test_runner.events import _format_tool_input


def test_format_tool_input_powershell_includes_command() -> None:
    """PowerShell/Bash 的 input 包含 command 字段。"""
    out = _format_tool_input(
        {"command": "Get-ChildItem D:\\work", "description": "列出目录"},
    )
    assert "command=" in out
    assert "Get-ChildItem D:" in out or "Get-ChildItem" in out


def test_format_tool_input_truncates_long_values() -> None:
    """任意字段值超过 _INPUT_MAX_VALUE_LEN 截断。"""
    long_cmd = "ls " + "x" * 500
    out = _format_tool_input({"command": long_cmd})
    assert "..." in out
    assert len(out) < 600  # 总长度也限制


def test_format_tool_input_handles_non_dict() -> None:
    """非 dict 输入(字符串/None)不抛,返回 str() 截断。"""
    out = _format_tool_input("just a string")
    assert isinstance(out, str)
    assert "just a string" in out


def test_format_tool_input_empty_dict_returns_empty_marker() -> None:
    """空 dict(累积未完成)返回空标记,避免刷 '<>'。"""
    assert _format_tool_input({}) == ""


def test_summarize_event_text_block_delta_includes_delta() -> None:
    """TEXT_BLOCK_DELTA 摘要包含 (text) 标签和 delta 内容。"""
    ev = _FakeEvent(type=_FakeEventType.TEXT_BLOCK_DELTA, delta="你好,世界。")
    out = _summarize_event(ev)
    assert "(text)" in out
    assert "你好,世界。" in out


def test_summarize_event_thinking_block_delta_includes_delta() -> None:
    """THINKING_BLOCK_DELTA 摘要包含 (thinking) 标签和 delta 内容。"""
    ev = _FakeEvent(type=_FakeEventType.THINKING_BLOCK_DELTA, delta="让我想想")
    out = _summarize_event(ev)
    assert "(thinking)" in out
    assert "让我想想" in out


def test_summarize_event_long_delta_is_truncated() -> None:
    """超长 delta 截断(避免刷屏),但保留尾部省略号。"""
    long_delta = "x" * 500
    ev = _FakeEvent(type=_FakeEventType.TEXT_BLOCK_DELTA, delta=long_delta)
    out = _summarize_event(ev)
    # 全文应 < 500 字符,且有截断标记
    assert len(out) < 500
    assert "..." in out


def test_summarize_event_tool_call_start_includes_name() -> None:
    """ToolCallStartEvent 摘要包含 tool_call_name。"""

    @dataclass
    class _Ev:
        type: _FakeEventType
        tool_call_name: str = ""
        tool_call_id: str = ""

    ev = _Ev(type=_FakeEventType.TOOL_CALL_START, tool_call_name="Bash", tool_call_id="c1")
    out = _summarize_event(ev)
    assert "Bash" in out
    assert "tool call" in out


def test_summarize_event_tool_result_start_includes_name() -> None:
    """ToolResultStartEvent 摘要包含 tool_call_name。"""

    @dataclass
    class _Ev:
        type: _FakeEventType
        tool_call_name: str = ""
        tool_call_id: str = ""

    ev = _Ev(
        type=_FakeEventType.TOOL_RESULT_START,
        tool_call_name="Bash",
        tool_call_id="c1",
    )
    out = _summarize_event(ev)
    assert "Bash" in out
    assert "tool result" in out


def test_summarize_event_unknown_type_returns_friendly_fallback() -> None:
    """未知事件类型不抛,返回带 type 名的兜底字符串。"""
    ev = _FakeEvent(type=_FakeEventType.OTHER, delta="<ignored>")
    out = _summarize_event(ev)
    # 不抛异常,包含类型名
    assert "OTHER" in out or "other" in out


def test_build_agent_uses_bypass_permission_mode(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """Agent 默认 BYPASS permission mode,不让 CLI 卡在 REQUIRE_USER_CONFIRM。

    根因:agentscope PermissionMode.DEFAULT 让所有写操作 ASK,
    没有 UI 的 CLI 收到 RequireUserConfirmEvent 就 hang 在那里。
    骨架 CLI 由用户在命令行启动 = 授权,用 BYPASS 全部 ALLOW。
    """
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")

    from bigbear_test_runner.agent import build_agent

    a = build_agent()

    # state 应是 AgentState(非 None),permission_context.mode == BYPASS
    assert a.state is not None, "Agent.state 应是 AgentState 实例"
    mode = a.state.permission_context.mode
    assert mode.value == "bypass", f"permission mode 应为 bypass,实际 {mode!r}"


def test_build_agent_with_skills_dirs_still_has_tools(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """传 skills_dirs 时,内置工具仍装入(与 skill 加载独立)。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.setattr("sys.platform", "linux")

    from bigbear_test_runner.agent import build_agent

    build_agent(skills_dirs=["/path/to/skills"])

    kinds = _tool_kinds(fake_agentscope)
    assert kinds == ["FakeBash"]
    # skill loader 也照常装
    assert fake_agentscope["loader_kwargs"] == [
        {"directory": "/path/to/skills", "scan_subdir": True},
    ]


# ---- 2026-09-10 改造:build_agent 接收 system_prompt 透传给 Agent ----

def test_build_agent_passes_system_prompt_through(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """build_agent(system_prompt=...) 应把 system_prompt 直接透传给 Agent。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")

    from bigbear_test_runner.agent import build_agent

    build_agent(system_prompt="你是测试计划执行 AI")

    agent_kwargs = fake_agentscope["agent_kwargs"][0]
    assert agent_kwargs["system_prompt"] == "你是测试计划执行 AI"


def test_run_streaming_forwards_system_prompt_to_build_agent(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """run_streaming(system_prompt=...) 应把 system_prompt 传给 build_agent。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    fake_agentscope["events"] = []

    from bigbear_test_runner.agent import run_streaming

    asyncio.run(run_streaming("hi", system_prompt="custom-sys-prompt"))

    agent_kwargs = fake_agentscope["agent_kwargs"][0]
    assert agent_kwargs["system_prompt"] == "custom-sys-prompt"


def test_run_streaming_registers_dynamic_functions(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope: dict[str, Any],
) -> None:
    """run_streaming 应把计划函数注册表交给专用工具。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    fake_agentscope["events"] = []

    from bigbear_test_runner.agent import run_streaming
    from bigbear_test_runner.plan_loader import (
        DynamicFunction,
        EnvVars,
        ProjectBundle,
    )

    asyncio.run(
        run_streaming(
            "hi",
            project=ProjectBundle(
                project_dir=Path("D:/project"),
                env=EnvVars(env_name="default", values={"ENV_A": "value-a"}),
                dynamic_functions=[
                    DynamicFunction(
                        function_code="demo",
                        function_type="通用工具",
                        abs_path=Path("D:/project/demo.py"),
                    ),
                ],
            ),
        ),
    )

    tools = fake_agentscope["toolkit_kwargs"][0]["tools"]
    assert any(getattr(tool, "name", "") == "run_dynamic_function" for tool in tools)
