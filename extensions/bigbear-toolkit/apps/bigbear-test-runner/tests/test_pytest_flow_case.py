"""Flow context、Jinja2 输入和 Task 结果协议测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from bigbear_test_runner import plan_loader, pytest_flow_case


def test_render_inputs_uses_flow_context() -> None:
    task = plan_loader.Task(
        title="登录",
        type=plan_loader.CaseType.WEB,
        source_id="case-1",
        inputs=[
            plan_loader.TaskIO(name="手机号", value="{{ 手机号 }}"),
            plan_loader.TaskIO(name="URL", value="https://example.com"),
        ],
    )

    inputs = pytest_flow_case._render_inputs(task, {"手机号": "13800138001"})

    assert inputs == {
        "手机号": "13800138001",
        "URL": "https://example.com",
    }


def test_render_inputs_rejects_missing_context_variable() -> None:
    task = plan_loader.Task(
        title="登录",
        type=plan_loader.CaseType.WEB,
        source_id="case-1",
        inputs=[plan_loader.TaskIO(name="手机号", value="{{ 手机号 }}")],
    )

    with pytest.raises(ValueError, match="手机号.*渲染失败"):
        pytest_flow_case._render_inputs(task, {})


def test_parse_task_result() -> None:
    result = pytest_flow_case._parse_task_result(
        '过程说明\n[task-result] {"status":"pass","reason":"ok",'
        '"outputs":{"response":{"token":"abc"}}}',
    )

    assert result["status"] == "PASS"
    assert result["outputs"]["response"]["token"] == "abc"
    assert pytest_flow_case._read_output(result["outputs"], "response.token") == "abc"


@pytest.mark.parametrize(
    "text,error",
    [
        ("没有最终结果", "未输出"),
        ('[task-result] {"status":"UNKNOWN","outputs":{}}', "PASS 或 FAIL"),
        ('[task-result] {"status":"PASS","outputs":[]}', "JSON object"),
        ('[task-result] not-json', "合法 JSON"),
    ],
)
def test_parse_task_result_rejects_invalid_protocol(text: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        pytest_flow_case._parse_task_result(text)


def test_flow_runs_each_task_as_step_and_updates_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first = plan_loader.Task(
        title="获取账号",
        type=plan_loader.CaseType.DYNAMIC_FUNCTION,
        source_id="get_account",
        outputs=[plan_loader.TaskIO(name="手机号", value="phone_number")],
    )
    second = plan_loader.Task(
        title="登录",
        type=plan_loader.CaseType.WEB,
        source_id="login",
        inputs=[plan_loader.TaskIO(name="登录账号", value="{{ 手机号 }}")],
        case={"case_content": {"steps": ["输入账号"], "expected": ["成功"]}},
    )
    flow = plan_loader.Flow(
        id="flow-001",
        title="登录流程",
        tasks=[first, second],
    )
    pytest_flow_case._PLAN = plan_loader.Plan(
        id="plan-001",
        name="核心回归",
        flows=[flow],
    )
    pytest_flow_case._PROJECT = plan_loader.ProjectBundle(project_dir=tmp_path)
    monkeypatch.setenv("AIQE_RUN_ID", "test-run")
    monkeypatch.setenv("AIQE_SKILLS_DIRS", "[]")
    monkeypatch.setattr(pytest_flow_case, "_close_browser", lambda session: None)
    messages = []

    async def _fake_run_agent(message: str, *args, **kwargs) -> str:
        messages.append(message)
        if len(messages) == 1:
            return (
                '[task-result] {"status":"PASS","reason":"ok",'
                '"outputs":{"phone_number":"13800138001"}}'
            )
        return '[task-result] {"status":"PASS","reason":"ok","outputs":{}}'

    monkeypatch.setattr(pytest_flow_case, "_run_agent", _fake_run_agent)
    try:
        pytest_flow_case.test_flow(0)
    finally:
        pytest_flow_case._PLAN = None
        pytest_flow_case._PROJECT = None

    assert len(messages) == 2
    assert "获取账号" in messages[0]
    assert "输入账号" not in messages[0]
    assert "输入账号" in messages[1]
    assert '"登录账号": "13800138001"' in messages[1]


def test_flow_fails_when_agent_output_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    task = plan_loader.Task(
        title="输出 Token",
        type=plan_loader.CaseType.DYNAMIC_FUNCTION,
        source_id="token",
        outputs=[plan_loader.TaskIO(name="Token", value="token")],
    )
    pytest_flow_case._PLAN = plan_loader.Plan(
        id="plan-001",
        flows=[plan_loader.Flow(id="flow-001", title="流程", tasks=[task])],
    )
    pytest_flow_case._PROJECT = plan_loader.ProjectBundle(project_dir=tmp_path)
    monkeypatch.setenv("AIQE_RUN_ID", "test-run")
    monkeypatch.setenv("AIQE_SKILLS_DIRS", "[]")
    monkeypatch.setattr(pytest_flow_case, "_close_browser", lambda session: None)

    async def _fake_run_agent(*args, **kwargs) -> str:
        return '[task-result] {"status":"PASS","reason":"ok","outputs":{}}'

    monkeypatch.setattr(pytest_flow_case, "_run_agent", _fake_run_agent)
    try:
        with pytest.raises(pytest.fail.Exception, match="缺少取值路径: token"):
            pytest_flow_case.test_flow(0)
    finally:
        pytest_flow_case._PLAN = None
        pytest_flow_case._PROJECT = None
