"""cli.py 边界处理测试。

不依赖真实 agentscope;验证 main() 在不同异常路径下返回正确的退出码。
通过 tmp_path 构造最小 project_data 目录,验证 cli 能加载 + 调 executor.execute_plan。
"""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest


# ---- fake agentscope 模块(与 test_agent.py 类似,但更轻量) ----

@pytest.fixture
def fake_agentscope_cli():
    """注入假 agentscope,让 cli.main 的 import 路径不依赖真实包。"""
    to_restore: dict[str, object] = {}
    for name in [
        "agentscope",
        "agentscope.credential",
        "agentscope.model",
        "agentscope.agent",
        "agentscope.tool",
        "agentscope.event",
        "agentscope.message",
        "agentscope.skill",
    ]:
        if name in sys.modules:
            to_restore[name] = sys.modules[name]

    fake_pkg = types.ModuleType("agentscope")
    sys.modules["agentscope"] = fake_pkg

    mod_credential = types.ModuleType("agentscope.credential")
    mod_credential.DashScopeCredential = type(  # type: ignore[attr-defined]
        "DashScopeCredential", (), {"__init__": lambda self, **kw: None},
    )
    sys.modules["agentscope.credential"] = mod_credential
    fake_pkg.credential = mod_credential  # type: ignore[attr-defined]

    mod_model = types.ModuleType("agentscope.model")
    mod_model.DashScopeChatModel = type(  # type: ignore[attr-defined]
        "DashScopeChatModel", (), {"__init__": lambda self, **kw: None},
    )
    sys.modules["agentscope.model"] = mod_model
    fake_pkg.model = mod_model  # type: ignore[attr-defined]

    mod_agent = types.ModuleType("agentscope.agent")
    mod_agent.Agent = type(  # type: ignore[attr-defined]
        "Agent", (), {"__init__": lambda self, **kw: None},
    )
    sys.modules["agentscope.agent"] = mod_agent
    fake_pkg.agent = mod_agent  # type: ignore[attr-defined]

    mod_tool = types.ModuleType("agentscope.tool")
    for name in ("Toolkit", "Bash"):
        setattr(mod_tool, name, type(name, (), {"__init__": lambda self, **kw: None}))
    sys.modules["agentscope.tool"] = mod_tool
    fake_pkg.tool = mod_tool  # type: ignore[attr-defined]

    class _EventType:
        TEXT_BLOCK_DELTA = "text_block_delta"

    mod_event = types.ModuleType("agentscope.event")
    mod_event.EventType = _EventType  # type: ignore[attr-defined]
    sys.modules["agentscope.event"] = mod_event
    fake_pkg.event = mod_event  # type: ignore[attr-defined]

    mod_message = types.ModuleType("agentscope.message")
    mod_message.UserMsg = lambda **kw: types.SimpleNamespace(**kw)  # type: ignore[attr-defined]
    sys.modules["agentscope.message"] = mod_message
    fake_pkg.message = mod_message  # type: ignore[attr-defined]

    mod_skill = types.ModuleType("agentscope.skill")
    mod_skill.LocalSkillLoader = type(  # type: ignore[attr-defined]
        "LocalSkillLoader", (), {"__init__": lambda self, **kw: None},
    )
    sys.modules["agentscope.skill"] = mod_skill
    fake_pkg.skill = mod_skill  # type: ignore[attr-defined]

    yield

    for name in [
        "agentscope.credential", "agentscope.model", "agentscope.agent",
        "agentscope.tool", "agentscope.event", "agentscope.message",
        "agentscope.skill", "agentscope",
    ]:
        sys.modules.pop(name, None)
    for name, mod in to_restore.items():
        sys.modules[name] = mod


# ---- 最小 project_data 构造 fixture ----

# 2026-09-10:用一个紧凑的 fixture 把 plan + flow + case + env + device + 动态函数全部铺出来。
# 这套结构跟 examples/project_data/ 一致,这样 cli 测试不依赖外部资源。

PLAN_ID = "plan-20260610182912"
FLOW_ID = "8b6030cb-cdc1-47cf-b9dd-96e9726dfddc"
CASE_ID = "244d5b6d8bc64535b9ef1ec72974e88c"
FUNCTION_CODE = "get_login_credentials"


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


@pytest.fixture
def mini_project(tmp_path: Path) -> Path:
    """构造一个最小可用的 project_data 目录(plan + flow + case + env + device + function)。

    返回 project_dir 的绝对路径。
    """
    project = tmp_path / "project_data"
    _write(
        project / "AI-自动化测试计划" / PLAN_ID / "meta.yaml",
        f"""id: {PLAN_ID}
name: 测试计划名
environmentKey: default
executionStrategy: serial
flows:
  - sourceFlowFile: {FLOW_ID}.yaml
    sourceFlowId: {FLOW_ID}
    sourceFlowName: 测试流程
""",
    )
    _write(
        project / "AI-自动化测试编排" / f"{FLOW_ID}.yaml",
        f"""name: 测试流程
priority: high
tags: [冒烟]
case_flows:
  - id: {FLOW_ID}
    title: 测试流程
    priority: high
    tags: [冒烟]
    tasks:
      - title: 获取登录账号
        type: dynamic-function
        source_id: {FUNCTION_CODE}
        input_datas: []
        output_datas:
          - name: 手机号
            value: phone_number
      - title: 正常登录
        type: web
        source_id: {CASE_ID}
        input_datas:
          - name: 手机号
            value: '{{{{手机号}}}}'
        output_datas: []
""",
    )
    _write(
        project / "AI-自动化测试用例" / "web" / "_index.yaml",
        f"""{CASE_ID}:
  case_id: {CASE_ID}
  case_title: 登录-正常登录
  case_path: 登录/{CASE_ID}.yaml
  case_type: web
  case_priority: P0
""",
    )
    _write(
        project / "AI-自动化测试用例" / "web" / "登录" / f"{CASE_ID}.yaml",
        f"""case_id: {CASE_ID}
case_type: web
case_title: 登录-正常登录
case_content:
  steps:
    - 打开网址 http://example.com/login
  expected:
    - 登录成功
""",
    )
    _write(
        project / "AI-环境变量" / "default" / "env_var.yaml",
        """TEST_PHONE_NUMBER:
  value: '13800138001'
TEST_PASSWORD:
  value: '123456'
""",
    )
    _write(
        project / "AI-测试设备中心" / "chrome001.yaml",
        """type: browser
cdp_port: 9222
""",
    )
    _write(
        project / "AI-动态函数管理" / "通用工具" / f"{FUNCTION_CODE}.py",
        f"""# AIQE_DYNAMIC_FUNCTION_META {{"function_code": "{FUNCTION_CODE}", "function_type": "通用工具", "function_name": "获取登录凭证", "description": "测试", "enabled": true, "params": [], "outputs": [{{"key": "phone_number", "name": "手机号"}}]}}

def execute(**kwargs):
    return {{"phone_number": "13800138001"}}
""",
    )
    return project.resolve()


def _make_argv(
    project_dir: str,
    plan_id: str = PLAN_ID,
    *,
    system_prompt: str = "",
    system_prompt_file: str | None = None,
    skills_dir: str | None = None,
    report_dir: str | None = None,
) -> list[str]:
    argv = ["--project-dir", project_dir, "--plan-id", plan_id]
    if system_prompt:
        argv += ["--system-prompt", system_prompt]
    if system_prompt_file:
        argv += ["--system-prompt-file", system_prompt_file]
    if skills_dir:
        argv += ["--skills-dir", skills_dir]
    if report_dir:
        argv += ["--report-dir", report_dir]
    return argv


# ---- 测试 ----

def test_main_returns_2_on_api_exception(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """agentscope 抛 Exception 时,main 返回 2 并打印 traceback。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.chdir(mini_project.parent)

    async def _fake_execute_plan(*args, **kwargs):
        raise RuntimeError("模拟的 agentscope API 异常")

    from bigbear_test_runner import cli

    monkeypatch.setattr(cli.executor, "execute_plan", _fake_execute_plan)

    rc = cli.main(_make_argv(str(mini_project)))

    assert rc == 2
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert "模拟的 agentscope API 异常" in err
    assert "Traceback" in err


def test_main_returns_2_on_missing_key(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """缺 AGENT_AI_API_KEY 时,_AgentMissingKeyError → 退出码 2 + stderr 友好提示。"""
    monkeypatch.delenv("AGENT_AI_API_KEY", raising=False)
    monkeypatch.chdir(mini_project.parent)

    from bigbear_test_runner import cli

    async def _fake_execute_plan(*args, **kwargs):
        raise cli.executor.ExecutionError(
            "缺少环境变量 AGENT_AI_API_KEY,请在 .env 中配置后重试。",
        )

    monkeypatch.setattr(cli.executor, "execute_plan", _fake_execute_plan)

    rc = cli.main(_make_argv(str(mini_project)))

    assert rc == 2
    err = capsys.readouterr().err
    assert "AGENT_AI_API_KEY" in err
    assert "Traceback" not in err


def test_main_returns_130_on_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """Ctrl-C 触发 KeyboardInterrupt → 退出码 130。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.chdir(mini_project.parent)

    async def _fake_execute_plan_kbi(*args, **kwargs):
        raise KeyboardInterrupt()

    from bigbear_test_runner import cli

    monkeypatch.setattr(cli.executor, "execute_plan", _fake_execute_plan_kbi)

    rc = cli.main(_make_argv(str(mini_project)))

    assert rc == 130
    err = capsys.readouterr().err
    assert "Interrupted" in err


def test_main_system_prompt_and_file_are_mutually_exclusive(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """--system-prompt 与 --system-prompt-file 同时传 → 退出码 2。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.chdir(mini_project.parent)

    extra_file = tmp_path / "extra.md"
    extra_file.write_text("用户追加内容", encoding="utf-8")

    from bigbear_test_runner import cli

    rc = cli.main(_make_argv(
        str(mini_project),
        system_prompt="直接传文本",
        system_prompt_file=str(extra_file),
    ))

    assert rc == 2
    err = capsys.readouterr().err
    assert "互斥" in err


def test_main_returns_2_when_project_dir_missing(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """--project-dir 指向不存在的目录 → argparse 校验失败 → 退出码 2。

    argparse 在 type 校验失败时调用 sys.exit(2),所以这里用 SystemExit 包。
    """
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)

    from bigbear_test_runner import cli

    with pytest.raises(SystemExit) as exc_info:
        cli.main(_make_argv(str(tmp_path / "not-exist")))

    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert "目录不存在" in err


def test_main_returns_2_when_plan_id_missing(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """--plan-id 找不到 meta.yaml → 退出码 2。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.chdir(mini_project.parent)

    from bigbear_test_runner import cli

    rc = cli.main(_make_argv(str(mini_project), plan_id="plan-not-exist"))

    assert rc == 2
    err = capsys.readouterr().err
    assert "meta.yaml 不存在" in err


def test_main_returns_0_on_success(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
) -> None:
    """成功路径:plan 加载 + executor.execute_plan 调用成功 → 退出码 0。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.chdir(mini_project.parent)

    captured: dict = {}

    async def _fake_execute_plan(plan, project, **kwargs):
        captured["plan"] = plan
        captured["project"] = project
        captured["kwargs"] = kwargs
        return 0

    from bigbear_test_runner import cli

    monkeypatch.setattr(cli.executor, "execute_plan", _fake_execute_plan)

    rc = cli.main(_make_argv(
        str(mini_project),
        system_prompt="请关注异常路径",
        report_dir=str(mini_project / "reports"),
    ))

    assert rc == 0
    assert captured["plan"].id == PLAN_ID
    assert captured["plan"].flows[0].id == FLOW_ID
    assert captured["kwargs"]["extra_system_prompt"] == "请关注异常路径"
    assert captured["project"] is not None
    assert captured["project"].dynamic_functions[0].abs_path.name == f"{FUNCTION_CODE}.py"
    assert captured["project"].env.values == {
        "TEST_PHONE_NUMBER": "13800138001",
        "TEST_PASSWORD": "123456",
    }
    assert captured["kwargs"]["skills_dirs"] == []
    assert captured["kwargs"]["report_dir"] == mini_project / "reports"


def test_main_returns_1_when_a_flow_fails(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
) -> None:
    """pytest 报告用例失败时,CLI 应保留标准退出码 1。"""
    monkeypatch.chdir(mini_project.parent)

    async def _fake_execute_plan(*args, **kwargs):
        return 1

    from bigbear_test_runner import cli

    monkeypatch.setattr(cli.executor, "execute_plan", _fake_execute_plan)

    assert cli.main(_make_argv(str(mini_project))) == 1


def test_main_system_prompt_file_reads_content(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
    tmp_path: Path,
) -> None:
    """--system-prompt-file 应读文件内容追加到 system_prompt。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.chdir(mini_project.parent)

    extra_file = tmp_path / "extra.md"
    extra_file.write_text("文件里的追加文本", encoding="utf-8")

    captured: dict = {}

    async def _fake_execute_plan(plan, project, **kwargs):
        captured["extra_system_prompt"] = kwargs.get("extra_system_prompt", "")
        return 0

    from bigbear_test_runner import cli

    monkeypatch.setattr(cli.executor, "execute_plan", _fake_execute_plan)

    rc = cli.main(_make_argv(
        str(mini_project),
        system_prompt_file=str(extra_file),
    ))

    assert rc == 0
    assert captured["extra_system_prompt"] == "文件里的追加文本"


def test_main_debug_prints_plan_summary(
    monkeypatch: pytest.MonkeyPatch,
    fake_agentscope_cli,
    mini_project: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """--debug 时,CLI 打印计划摘要并把 debug 交给 executor。"""
    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.chdir(mini_project.parent)

    captured: dict = {}

    async def _fake_execute_plan(*args, **kwargs):
        captured["debug"] = kwargs.get("debug")
        return 0

    from bigbear_test_runner import cli

    monkeypatch.setattr(cli.executor, "execute_plan", _fake_execute_plan)

    rc = cli.main(_make_argv(str(mini_project)) + ["--debug"])

    assert rc == 0
    err = capsys.readouterr().err
    assert "[cli] loaded plan" in err
    assert PLAN_ID in err
    assert captured["debug"] is True
