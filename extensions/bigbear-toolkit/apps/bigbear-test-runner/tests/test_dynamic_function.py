"""动态函数确定性执行器测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from bigbear_test_runner.dynamic_function import (
    DynamicFunctionExecutionError,
    execute_dynamic_function,
)
from bigbear_test_runner.plan_loader import (
    DynamicFunction,
    EnvVars,
    ProjectBundle,
)


def _write_script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _project(
    script: Path,
    *,
    code: str = "demo",
    environment: dict[str, str] | None = None,
    enabled: bool = True,
) -> ProjectBundle:
    return ProjectBundle(
        project_dir=script.parent,
        env=(
            EnvVars(env_name="default", values=environment)
            if environment is not None
            else None
        ),
        dynamic_functions=[
            DynamicFunction(
                function_code=code,
                function_type="通用工具",
                abs_path=script,
                enabled=enabled,
            ),
        ],
    )


def test_executes_unicode_path_without_wrapper_and_merges_context(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path / "AI-动态函数管理" / "通用工具" / "demo.py",
        """import json
import sys

if __name__ == "__main__":
    assert "--_context-stdin" in sys.argv
    context = json.loads(sys.stdin.read())
    print(json.dumps({
        "env_value": context["ENV_VALUE"],
        "flow_value": context["flow_value"],
    }, ensure_ascii=False))
""",
    )

    result = execute_dynamic_function(
        "demo",
        {"flow_value": "流程输出"},
        project=_project(script, environment={"ENV_VALUE": "环境值"}),
    )

    assert result == {"env_value": "环境值", "flow_value": "流程输出"}
    assert list(tmp_path.rglob("*wrapper*")) == []
    assert list(tmp_path.rglob("context.json")) == []


def test_flow_context_overrides_environment(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path / "demo.py",
        """import json
import sys
print(json.dumps(json.loads(sys.stdin.read()), ensure_ascii=False))
""",
    )

    result = execute_dynamic_function(
        "demo",
        {"same_key": "flow"},
        project=_project(
            script,
            environment={"same_key": "env", "env_only": "kept"},
        ),
    )

    assert result == {"same_key": "flow", "env_only": "kept"}


def test_rejects_unregistered_function(tmp_path: Path) -> None:
    with pytest.raises(DynamicFunctionExecutionError, match="未注册或已禁用"):
        execute_dynamic_function(
            "unknown",
            {},
            project=_project(tmp_path / "known.py", code="known"),
        )


def test_rejects_disabled_function(tmp_path: Path) -> None:
    with pytest.raises(DynamicFunctionExecutionError, match="未注册或已禁用"):
        execute_dynamic_function(
            "disabled",
            {},
            project=_project(
                tmp_path / "disabled.py",
                code="disabled",
                enabled=False,
            ),
        )


def test_reports_nonzero_exit_without_creating_fallback(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path / "failed.py",
        """import sys
print("明确失败", file=sys.stderr)
raise SystemExit(7)
""",
    )

    with pytest.raises(DynamicFunctionExecutionError) as exc_info:
        execute_dynamic_function(
            "failed",
            {},
            project=_project(script, code="failed"),
        )

    message = str(exc_info.value)
    assert "exit=7" in message
    assert "明确失败" in message
    assert sorted(p.name for p in tmp_path.iterdir()) == ["failed.py"]


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("not-json", "不是合法 JSON"),
        (json.dumps([1, 2, 3]), "必须是 JSON object"),
    ],
)
def test_rejects_invalid_output(tmp_path: Path, stdout: str, expected: str) -> None:
    script = _write_script(
        tmp_path / "invalid.py",
        f"print({stdout!r})\n",
    )

    with pytest.raises(DynamicFunctionExecutionError, match=expected):
        execute_dynamic_function(
            "invalid",
            {},
            project=_project(script, code="invalid"),
        )
