"""把单个 Task 组装为 Agent prompt。"""
from __future__ import annotations

import json
import platform
import shutil
import sys
from typing import Any, Mapping

from bigbear_test_runner import plan_loader


DEFAULT_SYSTEM_PROMPT = (
    "你构是华测 AIQE 自动化测试执行助手。"
    "每次只执行一个 Task,不得执行当前消息之外的工作。"
    "执行结束必须严格按消息约定输出结化结果。"
)


def build_system_prompt(extra: str = "") -> str:
    extra = (extra or "").strip()
    parts = [DEFAULT_SYSTEM_PROMPT, _build_env_info()]
    if extra:
        parts.append(f"【用户补充】\n{extra}")
    return "\n\n".join(parts)


def _build_env_info() -> str:
    system = platform.system()
    lines = ["## 当前运行环境(必须按此选择命令语法)"]
    lines.append(f"- 操作系统: {system} ({platform.platform()})")
    lines.append(f"- Python 解释器: {sys.executable}")
    lines.append(f"- Python 版本: {platform.python_version()}")

    if system == "Windows":
        bash_path = shutil.which("bash") or shutil.which("bash.exe")
        lines.append("- Shell(Bash 工具实际底层): cmd.exe(/c 方式调用)")
        lines.append(f"- Git Bash: {bash_path}" if bash_path else "- 未检测到 Git Bash")
        lines.append("- 路径分隔符: 反斜杠")
        lines.append("- 引号:只用双引号;单引号不会作为 quote")
        lines.append("- 环境变量:`set NAME=value`")
    else:
        shell_path = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        lines.append(f"- Shell(Bash 工具实际底层): /bin/sh(-c,执行器:{shell_path})")
        lines.append("- 环境变量:`NAME=value cmd` 或 `export NAME=value`")
    return "\n".join(lines)


def _render_devices(devices: list[plan_loader.Device]) -> str:
    if not devices:
        return "(无测试设备)"
    lines = []
    for device in devices:
        values = ", ".join(
            f"{key}={device.raw[key]!r}" for key in sorted(device.raw)
        )
        lines.append(f"- `{device.device_id}`: {values}")
    return "\n".join(lines)


def _render_case(task: plan_loader.Task) -> str:
    if task.case is None:
        return "(无详情)"
    case = task.case
    content = case.get("case_content")
    if not isinstance(content, dict):
        return json.dumps(case, ensure_ascii=False, indent=2)

    lines = []
    if case.get("case_precondition"):
        lines.append(f"前置条件: {case['case_precondition']}")
    if task.type == plan_loader.CaseType.WEB:
        lines.append("执行步骤:")
        for index, step in enumerate(content.get("steps") or [], 1):
            lines.append(f"{index}. {step}")
        lines.append("预期结果:")
        for expected in content.get("expected") or []:
            lines.append(f"- {expected}")
    else:
        request = content.get("request") or {}
        lines.append("请求信息:")
        lines.append(json.dumps(request, ensure_ascii=False, indent=2))
        lines.append("预期结果:")
        for expected in content.get("expected") or []:
            lines.append(f"- {expected}")
    return "\n".join(lines)


def _render_detail(task: plan_loader.Task) -> str:
    lines = [
        f"- type: `{task.type.value}`",
        f"- source_id: `{task.source_id}`",
    ]
    if task.abs_path is not None:
        lines.append(f"- source_path: `{task.abs_path}`")
    if task.type == plan_loader.CaseType.DYNAMIC_FUNCTION:
        lines.extend(
            [
                "- 调用 `run_dynamic_function` 工具。",
                f"- function_code 固定为 `{task.source_id}`。",
                "- context 传入本消息的 input JSON。",
                "- 禁止通过 Bash、Python 命令或临时文件执行动态函数。",
            ],
        )
    else:
        lines.append("")
        lines.append(_render_case(task))
    return "\n".join(lines)


def build_task_message(
    plan: plan_loader.Plan,
    flow: plan_loader.Flow,
    task: plan_loader.Task,
    task_index: int,
    project: plan_loader.ProjectBundle,
    inputs: Mapping[str, Any],
    *,
    browser_session: str,
) -> str:
    """构造只包含当前 Task 的 input/detail/output 消息。"""
    output_keys = [item.value for item in task.outputs]
    output_example = {key: f"<{key}>" for key in output_keys}

    sections = [
        "# 自动化测试 Task",
        "",
        f"- plan: `{plan.id}`",
        f"- flow: `{flow.id}` / {flow.title}",
        f"- task: `{task_index}` / {task.title}",
        "",
        "## Input",
        "以下 JSON 已由执行器完成 Jinja2 渲染,直接使用,不要再次解析模板:",
        "```json",
        json.dumps(dict(inputs), ensure_ascii=False, indent=2),
        "```",
        "",
        "## Detail",
        _render_detail(task),
        "",
        "## Output",
    ]

    if task.outputs:
        sections.append("必须在 outputs 中返回以下键:")
        sections.extend(
            f"- `{item.value}`:写入 Flow context 的变量 `{item.name}`"
            for item in task.outputs
        )
    else:
        sections.append("该 Task 没有输出变量,outputs 必须是空对象。")

    sections.extend(
        [
            "",
            "最后一行必须是以下格式的单行 JSON,不要放进 Markdown 代码块:",
            "`[task-result] {json}`",
            "其中 status 只能是 PASS 或 FAIL,outputs 必须是 JSON object。",
            "示例:",
            "[task-result] "
            + json.dumps(
                {
                    "status": "PASS",
                    "reason": "执行成功",
                    "outputs": output_example,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        ],
    )

    if task.type in (plan_loader.CaseType.WEB, plan_loader.CaseType.API):
        sections.extend(
            [
                "",
                "## Browser Session",
                f"每条 playwright-cli 命令必须带 `-s={browser_session}`。",
                "当前 Task 完成后不要关闭浏览器,后续 Task 会继续使用该会话。",
                "",
                "## 测试设备",
                _render_devices(project.devices),
            ],
        )

    return "\n".join(sections)


__all__ = ["DEFAULT_SYSTEM_PROMPT", "build_system_prompt", "build_task_message"]
