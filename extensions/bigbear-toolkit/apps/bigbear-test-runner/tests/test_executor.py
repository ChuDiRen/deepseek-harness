"""executor 的 pytest 串行/并发调度测试。"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from bigbear_test_runner import executor, plan_loader


def _plan(strategy: plan_loader.ExecStrategy) -> plan_loader.Plan:
    return plan_loader.Plan(
        id="plan-001",
        name="调度测试",
        strategy=strategy,
        flows=[
            plan_loader.Flow(id="flow-001", title="流程一"),
            plan_loader.Flow(id="flow-002", title="流程二"),
        ],
    )


class _Process:
    def __init__(self, exit_code: int = 0):
        self.exit_code = exit_code

    async def wait(self) -> int:
        return self.exit_code


def test_serial_starts_pytest_without_xdist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict = {}

    async def _fake_subprocess(*command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return _Process()

    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.setattr(executor.asyncio, "create_subprocess_exec", _fake_subprocess)
    monkeypatch.setattr(executor.shutil, "which", lambda name: None)

    exit_code = asyncio.run(
        executor.execute_plan(
            _plan(plan_loader.ExecStrategy.SERIAL),
            plan_loader.ProjectBundle(project_dir=tmp_path),
            skills_dirs=["D:/skills"],
            report_dir=tmp_path / "report",
        ),
    )

    assert exit_code == 0
    assert captured["command"][:3] == (
        executor.sys.executable,
        "-m",
        "pytest",
    )
    assert "--alluredir" in captured["command"]
    assert "-n" not in captured["command"]
    assert captured["env"]["AIQE_PLAN_ID"] == "plan-001"
    assert captured["env"]["AIQE_SKILLS_DIRS"] == '["D:/skills"]'
    assert (tmp_path / "report/allure-results/environment.properties").is_file()


def test_parallel_uses_one_xdist_worker_per_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict = {}

    async def _fake_subprocess(*command, **kwargs):
        captured["command"] = command
        return _Process()

    monkeypatch.setenv("AGENT_AI_API_KEY", "test-key")
    monkeypatch.setattr(executor.asyncio, "create_subprocess_exec", _fake_subprocess)
    monkeypatch.setattr(executor.shutil, "which", lambda name: None)

    asyncio.run(
        executor.execute_plan(
            _plan(plan_loader.ExecStrategy.PARALLEL),
            plan_loader.ProjectBundle(project_dir=tmp_path),
            report_dir=tmp_path / "report",
        ),
    )

    worker_arg = captured["command"].index("-n")
    assert captured["command"][worker_arg + 1] == "2"


def test_missing_key_is_exposed_as_execution_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("AGENT_AI_API_KEY", raising=False)

    with pytest.raises(executor.ExecutionError, match="AGENT_AI_API_KEY"):
        asyncio.run(
            executor.execute_plan(
                _plan(plan_loader.ExecStrategy.SERIAL),
                plan_loader.ProjectBundle(project_dir=tmp_path),
            ),
        )
