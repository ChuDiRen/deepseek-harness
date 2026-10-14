"""测试计划执行层:通过 pytest 调度 Flow,每个 Flow 是一条测试用例。"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime
from importlib import metadata as importlib_metadata
from pathlib import Path

from bigbear_test_runner.plan_loader import ExecStrategy, Plan, ProjectBundle


class ExecutionError(Exception):
    """pytest 启动、收集或报告生成前的执行错误。"""


async def _stream_subprocess_output(
    stream: asyncio.StreamReader,
    prefix: str,
) -> None:
    """逐行读取子进程输出,加上前缀后写到父进程 stderr。"""
    while True:
        line = await stream.readline()
        if not line:
            return
        try:
            text = line.decode("utf-8", errors="replace").rstrip("\r\n")
        except Exception:
            text = repr(line)
        print(f"{prefix} {text}", file=sys.stderr, flush=True)


def _make_empty_pytest_config() -> Path:
    """生成一个真实的空 pytest 配置文件。

    不能用 ``os.devnull``(在 Windows 上是 ``nul``,pytest 9.x 会把它
    当成 NUL 设备路径处理,导致 rootdir 解析为 ``\\\\.\\nul`` 并在
    collection 阶段访问奇怪的路径,最终报 FileNotFoundError)。
    用真实的临时空文件代替,既能不加载项目 pyproject.toml,也能让
    pytest 拿到一个合法的 configfile 路径。
    """
    fd, name = tempfile.mkstemp(prefix="aiqe-pytest-", suffix=".ini")
    try:
        os.close(fd)
    except OSError:
        print(f"[DEBUG executor] close file descriptor {fd} failed: {os.strerror(errno)}", file=sys.stderr, flush=True)
        pass
    return Path(name)


async def execute_plan(
    plan: Plan,
    project: ProjectBundle,
    *,
    extra_system_prompt: str = "",
    debug: bool = False,
    skills_dirs: list[str] | None = None,
    report_dir: Path | None = None,
) -> int:
    """启动 pytest;serial 单进程执行,parallel 按 Flow 数量启用 xdist。"""
    if not os.environ.get("AGENT_AI_API_KEY"):
        raise ExecutionError("缺少环境变量 AGENT_AI_API_KEY,请在 .env 中配置后重试。")

    if not plan.flows:
        print(f"[plan] {plan.id} → COMPLETED (flows=0)", flush=True)
        return 0

    run_id = uuid.uuid4().hex[:8]
    if report_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_dir = (
            project.project_dir
            / "AI-自动化测试报告"
            / plan.id
            / f"{timestamp}-{run_id}"
        )
    report_dir = report_dir.resolve()
    results_dir = report_dir / "allure-results"
    html_dir = report_dir / "allure-report"

    env = os.environ.copy()
    env.update(
        {
            "AIQE_PROJECT_DIR": str(project.project_dir),
            "AIQE_PLAN_ID": plan.id,
            "AIQE_EXTRA_SYSTEM_PROMPT": extra_system_prompt,
            "AIQE_SKILLS_DIRS": json.dumps(skills_dirs or [], ensure_ascii=False),
            "AIQE_DEBUG": "1" if debug else "0",
            "AIQE_RUN_ID": run_id,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        },
    )

    flow_case_file = Path(__file__).with_name("pytest_flow_case.py")
    if not flow_case_file.is_file():
        raise ExecutionError(f"flow_case 文件不存在: {flow_case_file}")

    # 用真实临时文件代替 os.devnull,避免 pytest 9.x 在 Windows 下
    # 把 ``nul`` 解析为 NUL 设备根路径导致 collection 报错。
    empty_cfg = _make_empty_pytest_config()

    command = [
        sys.executable,
        "-m",
        "pytest",
        # "-c",
        # str(empty_cfg),
        "-p",
        "allure_pytest.plugin",
        str(flow_case_file),
        "-s",
        "-q",
        "--alluredir",
        str(results_dir),
        "--clean-alluredir",
    ]
    if plan.strategy == ExecStrategy.PARALLEL:
        command.extend(["-p", "xdist.plugin", "-n", str(len(plan.flows))])

    cwd = Path.cwd()
    print(
        f"[executor] plan={plan.id!r} strategy={plan.strategy.value} "
        f"flows={len(plan.flows)} report={report_dir}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[executor] cwd={cwd}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[executor] sys.executable={sys.executable}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[executor] pytest version: "
        f"{__import__('pytest').__version__}",
        file=sys.stderr,
        flush=True,
    )
    try:
        xdist_ver = importlib_metadata.version("pytest-xdist")
    except importlib_metadata.PackageNotFoundError:
        xdist_ver = "(未安装)"
    print(
        f"[executor] xdist version: {xdist_ver}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[executor] flow_case_file={flow_case_file} (exists={flow_case_file.is_file()})",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[executor] empty_pytest_config={empty_cfg}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[executor] command: {' '.join(command)}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[executor] AIQE env: AIQE_PROJECT_DIR={env.get('AIQE_PROJECT_DIR')!r} "
        f"AIQE_PLAN_ID={env.get('AIQE_PLAN_ID')!r} "
        f"AIQE_RUN_ID={env.get('AIQE_RUN_ID')!r} "
        f"AIQE_DEBUG={env.get('AIQE_DEBUG')!r}",
        file=sys.stderr,
        flush=True,
    )

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            env=env,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as e:
        raise ExecutionError(
            f"pytest 子进程无法启动(找不到可执行文件): {e}\n"
            f"command: {' '.join(command)}\n"
            f"sys.executable={sys.executable}\n"
            f"PATH={os.environ.get('PATH', '')!r}",
        ) from e
    except OSError as e:
        raise ExecutionError(
            f"pytest 子进程启动失败: {type(e).__name__}: {e}\n"
            f"command: {' '.join(command)}",
        ) from e

    # 并发转发 stdout/stderr,避免死锁
    try:
        await asyncio.gather(
            _stream_subprocess_output(process.stdout, "[pytest-stdout]"),
            _stream_subprocess_output(process.stderr, "[pytest-stderr]"),
        )
    except Exception as e:
        print(
            f"[executor] 流式转发 pytest 输出时异常: {type(e).__name__}: {e}",
            file=sys.stderr,
            flush=True,
        )

    exit_code = await process.wait()
    print(
        f"[executor] pytest 退出码: {exit_code}",
        file=sys.stderr,
        flush=True,
    )

    # 清理临时空配置文件
    try:
        empty_cfg.unlink(missing_ok=True)
    except OSError as e:
        print(
            f"[executor] 清理临时 pytest 配置失败: {type(e).__name__}: {e}",
            file=sys.stderr,
            flush=True,
        )

    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "environment.properties").write_text(
        f"plan.id={plan.id}\n"
        f"plan.name={plan.name}\n"
        f"execution.strategy={plan.strategy.value}\n",
        encoding="utf-8",
    )

    allure_command = shutil.which("allure")
    if allure_command:
        report_process = await asyncio.create_subprocess_exec(
            allure_command,
            "generate",
            str(results_dir),
            "--clean",
            "-o",
            str(html_dir),
        )
        if await report_process.wait() != 0:
            print("[report] Allure HTML 生成失败,原始结果仍可用", file=sys.stderr)
    else:
        print(
            f"[report] 未检测到 Allure CLI,已保留原始结果: {results_dir}",
            file=sys.stderr,
        )

    print(f"[report] {report_dir}", flush=True)
    if exit_code in (0, 1):
        return exit_code
    raise ExecutionError(f"pytest 执行失败,退出码: {exit_code}")


__all__ = ["ExecutionError", "execute_plan"]
