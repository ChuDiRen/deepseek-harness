"""单 Task prompt 组装测试。"""
from __future__ import annotations

import platform
from pathlib import Path

from bigbear_test_runner import plan_loader, prompt_builder


def _context(task: plan_loader.Task):
    plan = plan_loader.Plan(id="plan-001", name="核心回归")
    flow = plan_loader.Flow(id="flow-001", title="登录流程", tasks=[task])
    project = plan_loader.ProjectBundle(
        project_dir=Path("D:/project"),
        devices=[
            plan_loader.Device(
                device_id="chrome001",
                raw={"type": "browser", "cdp_port": 9222},
            ),
        ],
    )
    return plan, flow, project


def test_system_prompt_contains_runtime_and_extra() -> None:
    result = prompt_builder.build_system_prompt("关注异常路径")

    assert "华测 AIQE" in result
    assert "每次只执行一个 Task" in result
    assert "当前运行环境" in result
    assert "关注异常路径" in result
    if platform.system() == "Windows":
        assert "cmd.exe" in result
    else:
        assert "/bin/sh" in result


def test_web_task_message_has_input_detail_and_output_contract() -> None:
    task = plan_loader.Task(
        title="正常登录",
        type=plan_loader.CaseType.WEB,
        source_id="case-web-001",
        inputs=[plan_loader.TaskIO(name="手机号", value="{{手机号}}")],
        outputs=[plan_loader.TaskIO(name="Token", value="response.token")],
        case={
            "case_precondition": "未登录态",
            "case_content": {
                "steps": ["打开登录页", "输入手机号"],
                "expected": ["登录成功"],
            },
        },
        abs_path=Path("D:/project/case-web-001.yaml"),
    )
    plan, flow, project = _context(task)

    message = prompt_builder.build_task_message(
        plan,
        flow,
        task,
        0,
        project,
        {"手机号": "13800138001"},
        browser_session="aiqe-test-0",
    )

    assert "## Input" in message
    assert '"手机号": "13800138001"' in message
    assert "## Detail" in message
    assert "打开登录页" in message
    assert "登录成功" in message
    assert "## Output" in message
    assert "`response.token`" in message
    assert "`Token`" in message
    assert "[task-result]" in message
    assert "-s=aiqe-test-0" in message
    assert "不要关闭浏览器" in message
    assert "chrome001" in message


def test_dynamic_function_message_uses_structured_tool() -> None:
    task = plan_loader.Task(
        title="获取登录账号",
        type=plan_loader.CaseType.DYNAMIC_FUNCTION,
        source_id="get_login_credentials",
        outputs=[
            plan_loader.TaskIO(name="手机号", value="phone_number"),
            plan_loader.TaskIO(name="密码", value="password"),
        ],
        abs_path=Path("D:/project/get_login_credentials.py"),
    )
    plan, flow, project = _context(task)

    message = prompt_builder.build_task_message(
        plan,
        flow,
        task,
        0,
        project,
        {},
        browser_session="unused",
    )

    assert "run_dynamic_function" in message
    assert "get_login_credentials" in message
    assert "context 传入本消息的 input JSON" in message
    assert "禁止通过 Bash" in message
    assert '"phone_number":"<phone_number>"' in message
    assert '"password":"<password>"' in message
    assert "Browser Session" not in message


def test_task_without_outputs_requires_empty_object() -> None:
    task = plan_loader.Task(
        title="检查首页",
        type=plan_loader.CaseType.WEB,
        source_id="case-web-002",
        case={"case_content": {"steps": [], "expected": []}},
    )
    plan, flow, project = _context(task)

    message = prompt_builder.build_task_message(
        plan,
        flow,
        task,
        1,
        project,
        {},
        browser_session="aiqe-test-0",
    )

    assert "outputs 必须是空对象" in message
    assert '"outputs":{}' in message


def test_api_task_renders_request_detail() -> None:
    task = plan_loader.Task(
        title="API 登录",
        type=plan_loader.CaseType.API,
        source_id="case-api-001",
        case={
            "case_content": {
                "request": {
                    "url": "https://example.com/login",
                    "method": "POST",
                },
                "expected": ["code = 200"],
            },
        },
    )
    plan, flow, project = _context(task)

    message = prompt_builder.build_task_message(
        plan,
        flow,
        task,
        0,
        project,
        {},
        browser_session="aiqe-test-0",
    )

    assert "https://example.com/login" in message
    assert '"method": "POST"' in message
    assert "code = 200" in message
