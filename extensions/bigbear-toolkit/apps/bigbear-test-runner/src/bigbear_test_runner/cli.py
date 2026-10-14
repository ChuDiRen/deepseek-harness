"""bigbear-test-runner CLI 入口。

仅做参数解析、.env 加载、装配 plan/项目上下文、转发退出码。
Flow 调度交给 executor.py,agentscope 细节封装在 agent.py。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

from bigbear_test_runner import __version__
from bigbear_test_runner import executor
from bigbear_test_runner import plan_loader

# 2026-09-10 修复:PowerShell pipe / non-TTY 环境下,Python 默认 block-buffered
# stderr 会让异常 traceback 卡在 buffer 里直到进程退出,表现成'立刻回到 prompt
# 但什么都没发生'。强制 line buffering 让每次 print/write 后立刻 flush。
# Python 3.7+ 支持 TextIOWrapper.reconfigure(line_buffering=True)。
try:
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    # reconfigure 在某些环境(被重定向/无控制台)可能 raise ValueError,忽略即可
    pass


def _existing_dir(value: str) -> Path:
    """argparse type:必须是已存在的目录。"""
    p = Path(value)
    if not p.is_dir():
        raise argparse.ArgumentTypeError(f"目录不存在: {value}")
    return p


def _existing_file(value: str) -> Path:
    """argparse type:必须是已存在的文件。"""
    p = Path(value)
    if not p.is_file():
        raise argparse.ArgumentTypeError(f"文件不存在: {value}")
    return p


def _non_empty_string(value: str) -> str:
    """argparse type:非空字符串。空字符串会被拒绝,触发 SystemExit(2)。"""
    if not value or not value.strip():
        raise argparse.ArgumentTypeError("字符串不能为空")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bigbear-test-runner",
        description=(
            "华测 AIQE agent 调度版测试运行 CLI。"
            "读取测试计划 + 关联数据,组装成结构化 prompt,交给 agent 调度执行。"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启调试日志(agentscope 内部 + 应用层 + 打印组装后 prompt)。",
    )

    # 必需:测试计划定位
    parser.add_argument(
        "--project-dir",
        required=True,
        type=_existing_dir,
        metavar="DIR",
        help=(
            "项目工作目录(含 AI-自动化测试计划 / AI-自动化测试编排 / AI-自动化测试用例"
            " / AI-环境变量 / AI-测试设备中心 / AI-动态函数管理 等子目录)。"
        ),
    )
    parser.add_argument(
        "--plan-id",
        required=True,
        type=_non_empty_string,
        metavar="ID",
        help=(
            "测试计划 ID,对应 <project-dir>/AI-自动化测试计划/<ID>/meta.yaml。"
            "例: plan-20260610182912"
        ),
    )

    # 可选:agent system_prompt 追加(互斥)
    # 不对 --system-prompt 做非空 type 校验:argparse 会在解析 default 时跑一次 type,
    # 会让空字符串默认值被拒。空串 = 不追加是合法状态,在 main() 里做追加判断即可。
    parser.add_argument(
        "--system-prompt",
        default="",
        type=str,
        metavar="TEXT",
        help="追加在代码内固定 system prompt 后面的文本(直接传字符串)。",
    )
    parser.add_argument(
        "--system-prompt-file",
        default=None,
        type=_existing_file,
        metavar="PATH",
        help="从文件读取追加文本(与 --system-prompt 互斥)。",
    )

    # 原有:skill 目录
    parser.add_argument(
        "--skills-dir",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Skill 根目录(可重复,可散落在多个位置)。"
            "Agent 会扫描所有指定目录下注册的 skill。"
        ),
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        metavar="PATH",
        help=(
            "报告输出目录。默认写入 "
            "<project-dir>/AI-自动化测试报告/<plan-id>/<时间-运行ID>/。"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    loaded = _load_cwd_env()
    if loaded:
        print(f"[debug] .env loaded: {loaded}", file=sys.stderr) if args.debug else None

    # 互斥校验
    if args.system_prompt and args.system_prompt_file:
        print(
            "error: --system-prompt 与 --system-prompt-file 互斥,只能选一个",
            file=sys.stderr,
        )
        return 2

    # 读取追加 system_prompt(任一形式)
    extra_system_prompt = args.system_prompt
    if args.system_prompt_file:
        try:
            extra_system_prompt = Path(args.system_prompt_file).read_text(encoding="utf-8")
        except OSError as e:
            print(f"error: 读取 system-prompt-file 失败: {e}", file=sys.stderr)
            return 2

    # 加载 plan + 项目上下文
    project_dir = Path(args.project_dir).resolve()
    try:
        plan, project = plan_loader.load_plan(args.plan_id, project_dir)
    except plan_loader.PlanLoadError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.debug:
        print(
            f"[cli] loaded plan={plan.id!r} flows={len(plan.flows)} "
            f"tasks={sum(len(f.tasks) for f in plan.flows)} "
            f"env={'yes' if project.env else 'no'} "
            f"devices={len(project.devices)} "
            f"dynamic_functions={len(project.dynamic_functions)}",
            file=sys.stderr,
        )
        print(
            f"[cli] project_dir={project_dir} (exists={project_dir.is_dir()})",
            file=sys.stderr,
        )
        print(
            f"[cli] plan.name={plan.name!r} strategy={plan.strategy.value!r} "
            f"env_key={plan.environment_key!r}",
            file=sys.stderr,
        )
        for index, flow in enumerate(plan.flows):
            task_summary = ", ".join(
                f"{t.type.value}:{t.source_id}" for t in flow.tasks
            )
            print(
                f"[cli]   flow[{index}] id={flow.id!r} title={flow.title!r} "
                f"tasks=[{task_summary}]",
                file=sys.stderr,
            )
        print(
            f"[cli] extra_system_prompt={len(extra_system_prompt)} chars",
            file=sys.stderr,
        )
        print(
            f"[cli] skills_dirs={args.skills_dir}",
            file=sys.stderr,
        )
        final_report_dir = (
            Path(args.report_dir) if args.report_dir else None
        )
        print(
            f"[cli] report_dir={final_report_dir}",
            file=sys.stderr,
        )

    try:
        return asyncio.run(
            executor.execute_plan(
                plan,
                project,
                extra_system_prompt=extra_system_prompt,
                debug=args.debug,
                skills_dirs=args.skills_dir,
                report_dir=Path(args.report_dir) if args.report_dir else None,
            ),
        )
    except executor.ExecutionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as e:  # pylint: disable=broad-exception-caught
        # 2026-09-10 修复:之前未捕获的 Exception 让 CLI 静默退出,
        # 用户看不到任何错误信息。现在打印 traceback,保留退出码 2。
        print(
            f"error: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        return 2


def _load_cwd_env() -> Path | None:
    """仅加载执行命令时当前工作目录下的 .env,与 bigbear-test-runner 保持一致。"""
    env_path = Path.cwd() / ".env"
    if not env_path.is_file():
        return None
    load_dotenv(dotenv_path=env_path, override=False)
    return env_path


if __name__ == "__main__":
    raise SystemExit(main())
