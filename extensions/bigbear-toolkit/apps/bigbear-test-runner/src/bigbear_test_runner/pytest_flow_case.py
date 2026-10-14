"""pytest 运行入口:一个 Flow 是一条用例,一个 Task 是一个 Allure 步骤。"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import traceback
from collections.abc import Mapping
from typing import Any

import allure
import pytest
from jinja2 import Environment, StrictUndefined, TemplateError

from bigbear_test_runner import agent, plan_loader, prompt_builder


_PLAN = None
_PROJECT = None


def _load_context():
    global _PLAN, _PROJECT
    if _PLAN is None:
        _PLAN, _PROJECT = plan_loader.load_plan(
            os.environ["AIQE_PLAN_ID"],
            os.environ["AIQE_PROJECT_DIR"],
        )
    return _PLAN, _PROJECT


def pytest_generate_tests(metafunc) -> None:
    if "flow_index" not in metafunc.fixturenames:
        return
    plan, _ = _load_context()
    metafunc.parametrize(
        "flow_index",
        range(len(plan.flows)),
        ids=[flow.id for flow in plan.flows],
    )


def _render_inputs(
    task: plan_loader.Task,
    context: Mapping[str, Any],
) -> dict[str, str]:
    jinja = Environment(undefined=StrictUndefined, autoescape=False)
    rendered = {}
    for item in task.inputs:
        try:
            rendered[item.name] = jinja.from_string(item.value).render(context)
        except TemplateError as e:
            raise ValueError(
                f"输入参数 {item.name!r} 渲染失败: {item.value!r}: {e}",
            ) from e
    return rendered


def _parse_task_result(text: str) -> dict[str, Any]:
    for line in reversed(text.splitlines()):
        if line.strip().startswith("[task-result]"):
            payload = line.strip()[len("[task-result]"):].strip()
            try:
                result = json.loads(payload)
            except json.JSONDecodeError as e:
                raise ValueError(f"task-result 不是合法 JSON: {e}") from e
            if not isinstance(result, dict):
                raise ValueError("task-result 必须是 JSON object")
            status = str(result.get("status", "")).upper()
            if status not in {"PASS", "FAIL"}:
                raise ValueError("task-result.status 只能是 PASS 或 FAIL")
            outputs = result.get("outputs")
            if not isinstance(outputs, dict):
                raise ValueError("task-result.outputs 必须是 JSON object")
            result["status"] = status
            return result
    raise ValueError("Agent 未输出 [task-result] 最终结果")


def _read_output(outputs: Mapping[str, Any], path: str) -> Any:
    value: Any = outputs
    for key in path.split("."):
        if not isinstance(value, Mapping) or key not in value:
            raise ValueError(f"Agent outputs 缺少取值路径: {path}")
        value = value[key]
    return value


async def _run_agent(
    user_message: str,
    flow_id: str,
    project: plan_loader.ProjectBundle,
    *,
    extra_system_prompt: str,
    debug: bool,
    skills_dirs: list[str],
) -> str:
    return await agent.run_streaming(
        user_message,
        flow_id=flow_id,
        system_prompt=prompt_builder.build_system_prompt(extra_system_prompt),
        debug=debug,
        skills_dirs=skills_dirs,
        project=project,
    )


def _close_browser(browser_session: str) -> None:
    playwright_cli = shutil.which("playwright-cli")
    if playwright_cli:
        subprocess.run(
            [playwright_cli, f"-s={browser_session}", "close"],
            capture_output=True,
            check=False,
        )


def test_flow(flow_index: int) -> None:
    plan, project = _load_context()
    flow = plan.flows[flow_index]
    browser_session = f"aiqe-{os.environ['AIQE_RUN_ID']}-{flow_index}"
    extra_system_prompt = os.environ.get("AIQE_EXTRA_SYSTEM_PROMPT", "")
    skills_dirs = json.loads(os.environ.get("AIQE_SKILLS_DIRS", "[]"))
    debug = os.environ.get("AIQE_DEBUG") == "1"
    context: dict[str, Any] = dict(project.env.values) if project.env else {}

    allure.dynamic.title(flow.title or flow.id)
    allure.dynamic.parent_suite(plan.name or plan.id)
    allure.dynamic.suite(plan.id)
    allure.dynamic.parameter("flow_id", flow.id)
    for tag in flow.tags:
        allure.dynamic.tag(tag)

    try:
        for task_index, task in enumerate(flow.tasks):
            with allure.step(f"{task_index + 1}. {task.title}"):
                try:
                    inputs = _render_inputs(task, context)
                    context.update(inputs)
                    allure.attach(
                        json.dumps(inputs, ensure_ascii=False, indent=2),
                        "Input",
                        allure.attachment_type.JSON,
                    )

                    detail = prompt_builder.build_task_message(
                        plan,
                        flow,
                        task,
                        task_index,
                        project,
                        inputs,
                        browser_session=browser_session,
                    )
                    allure.attach(detail, "Detail", allure.attachment_type.TEXT)

                    raw_result = asyncio.run(
                        _run_agent(
                            detail,
                            flow.id,
                            project,
                            extra_system_prompt=extra_system_prompt,
                            debug=debug,
                            skills_dirs=skills_dirs,
                        ),
                    )
                    allure.attach(
                        raw_result,
                        "Agent 原始输出",
                        allure.attachment_type.TEXT,
                    )
                    result = _parse_task_result(raw_result)
                    allure.attach(
                        json.dumps(result, ensure_ascii=False, indent=2),
                        "Output",
                        allure.attachment_type.JSON,
                    )

                    if result["status"] == "FAIL":
                        pytest.fail(str(result.get("reason") or "Agent 执行失败"))

                    for output in task.outputs:
                        context[output.name] = _read_output(
                            result["outputs"],
                            output.value,
                        )
                except pytest.fail.Exception:
                    raise
                except Exception as e:
                    allure.attach(
                        traceback.format_exc(),
                        "Output",
                        allure.attachment_type.TEXT,
                    )
                    pytest.fail(f"Task {task_index} 执行失败: {e}")
    finally:
        allure.attach(
            json.dumps(context, ensure_ascii=False, indent=2),
            "Flow Context",
            allure.attachment_type.JSON,
        )
        if any(
            task.type in (plan_loader.CaseType.WEB, plan_loader.CaseType.API)
            for task in flow.tasks
        ):
            _close_browser(browser_session)
