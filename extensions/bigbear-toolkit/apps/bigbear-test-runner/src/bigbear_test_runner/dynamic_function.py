"""动态函数的确定性执行器与 AgentScope 工具适配。

动态函数不能经由 LLM 拼 shell 命令执行。Windows ``cmd.exe``、JSON 引号、
中文路径三者叠加后很容易产生不可复现的行为。这里始终使用参数数组启动当前
Python 解释器，并通过 stdin 传递 UTF-8 JSON；整个过程不创建任何辅助文件。
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, Mapping

from bigbear_test_runner.plan_loader import ProjectBundle


_DEFAULT_TIMEOUT_SECONDS = 120.0


class DynamicFunctionExecutionError(RuntimeError):
    """动态函数无法启动、执行失败或返回协议无效。"""


def execute_dynamic_function(
    function_code: str,
    context: Mapping[str, Any] | None,
    *,
    project: ProjectBundle,
    timeout_s: float = _DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """直接执行已注册动态函数，并返回其 JSON 对象结果。

    项目中的计划环境变量会作为基础上下文注入；``context`` 是当前 Flow
    已产生的 outputs，同名键覆盖环境变量。
    """
    code = (function_code or "").strip()
    if not code:
        raise DynamicFunctionExecutionError("function_code 不能为空")

    available_functions = [
        item
        for item in project.dynamic_functions
        if item.enabled and item.abs_path is not None
    ]
    function = next(
        (item for item in available_functions if item.function_code == code),
        None,
    )
    if function is None:
        available = ", ".join(
            sorted(item.function_code for item in available_functions),
        ) or "(无)"
        raise DynamicFunctionExecutionError(
            f"动态函数未注册或已禁用: {code}; 可用函数: {available}",
        )

    assert function.abs_path is not None
    script_path = function.abs_path.resolve()
    if not script_path.is_file():
        raise DynamicFunctionExecutionError(f"动态函数脚本不存在: {script_path}")
    if script_path.suffix.lower() != ".py":
        raise DynamicFunctionExecutionError(f"动态函数脚本必须是 .py 文件: {script_path}")

    if context is not None and not isinstance(context, Mapping):
        raise DynamicFunctionExecutionError("context 必须是 JSON object")

    merged_context: dict[str, Any] = (
        dict(project.env.values) if project.env is not None else {}
    )
    merged_context.update(dict(context or {}))
    try:
        stdin_json = json.dumps(
            merged_context,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise DynamicFunctionExecutionError(f"context 无法序列化为 JSON: {exc}") from exc

    argv = [
        sys.executable,
        "-X",
        "utf8",
        str(script_path),
        "--_context-stdin",
    ]
    try:
        completed = subprocess.run(
            argv,
            input=stdin_json,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise DynamicFunctionExecutionError(
            f"动态函数执行超时({timeout_s:g}s): {code}",
        ) from exc
    except OSError as exc:
        raise DynamicFunctionExecutionError(
            f"动态函数无法启动: {code}: {exc}",
        ) from exc

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        detail = stderr or stdout or "(无错误输出)"
        raise DynamicFunctionExecutionError(
            f"动态函数执行失败: {code} (exit={completed.returncode})\n{detail}",
        )
    if not stdout:
        raise DynamicFunctionExecutionError(f"动态函数未输出 JSON: {code}")

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise DynamicFunctionExecutionError(
            f"动态函数 stdout 不是合法 JSON: {code}: {exc}\n{stdout}",
        ) from exc
    if not isinstance(result, dict):
        raise DynamicFunctionExecutionError(
            f"动态函数返回值必须是 JSON object: {code}; 实际为 {type(result).__name__}",
        )
    return result


def build_dynamic_function_tool(project: ProjectBundle):
    """从已解析项目动态构造 ``run_dynamic_function`` 工具。"""
    from agentscope.tool import FunctionTool

    def run_dynamic_function(
        function_code: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """执行计划内已注册的动态函数。

        Args:
            function_code: Task 的 source_id。只能使用本计划已注册且启用的函数。
            context: 当前 Flow 已收集的 outputs。计划环境变量会由工具自动注入，
                不要在这里重复传环境变量，也不要创建 wrapper/context 临时文件。

        Returns:
            动态函数 stdout 中的 JSON object。
        """
        return execute_dynamic_function(
            function_code,
            context,
            project=project,
        )

    return FunctionTool(
        run_dynamic_function,
        name="run_dynamic_function",
        description=(
            "确定性执行测试计划内的动态函数。工具自动注入计划环境变量，通过 "
            "stdin 传递 UTF-8 JSON，禁止使用 Bash 或临时 wrapper 替代。"
        ),
        is_concurrency_safe=True,
        is_read_only=False,
    )
