"""project_data 目录加载层。

职责:把 project_dir 下的 yaml / python 全部解析为结构化 Python 对象。
所有 IO + 解析在这里,agent.py / cli.py 不直接读 yaml。

公开接口:
  - PlanLoadError:加载/解析异常,cli 统一捕获 → 退出码 2
  - CaseType / ExecStrategy:枚举
  - TaskIO / Task / Flow / Plan / DynamicFunction / Device / EnvVars / ProjectBundle:数据类
  - load_plan(plan_id, project_dir) -> (Plan, ProjectBundle):主入口
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PlanLoadError(Exception):
    """加载/解析失败。cli 捕获后 → 退出码 2。"""


class CaseType(Enum):
    WEB = "web"
    API = "api"
    DYNAMIC_FUNCTION = "dynamic-function"


class ExecStrategy(Enum):
    SERIAL = "serial"
    PARALLEL = "parallel"


# 2026-09-10:project_data 下 8 个一级目录的约定名称,与 examples/project_data/ 一一对应。
# 硬编码在这里,集中管理便于以后重命名/重定向。
PLAN_DIR_NAME = "AI-自动化测试计划"
CASE_DIR_NAME = "AI-自动化测试用例"
FLOW_DIR_NAME = "AI-自动化测试编排"
ENV_DIR_NAME = "AI-环境变量"
DEVICE_DIR_NAME = "AI-测试设备中心"
FUNCTION_DIR_NAME = "AI-动态函数管理"


@dataclass(frozen=True)
class TaskIO:
    """编排 task 的 input/output 绑定。value 含 {{变量名}} 占位。"""

    name: str
    value: str


@dataclass
class Task:
    """编排里的单个执行单元。"""

    title: str
    type: CaseType
    source_id: str
    inputs: list[TaskIO] = field(default_factory=list)
    outputs: list[TaskIO] = field(default_factory=list)
    # type=web/api 时:完整 case yaml dict
    # type=dynamic-function 时:None
    case: dict[str, Any] | None = None
    # type=web/api:case yaml 的绝对路径
    # type=dynamic-function:对应 .py 文件的绝对路径
    abs_path: Path | None = None


@dataclass
class Flow:
    id: str
    title: str
    priority: str = ""
    tags: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)


@dataclass
class Plan:
    id: str
    name: str = ""
    environment_key: str | None = None
    strategy: ExecStrategy = ExecStrategy.SERIAL
    flows: list[Flow] = field(default_factory=list)
    # 编排文件所在目录(用于 prompt 里告诉 agent 拼绝对路径)
    flows_dir: Path | None = None
    # 测试用例根目录(用于 prompt 里告诉 agent 拼绝对路径)
    cases_root: Path | None = None


@dataclass
class DynamicFunction:
    function_code: str
    function_type: str
    function_name: str = ""
    description: str = ""
    params: list[dict[str, Any]] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    abs_path: Path | None = None
    enabled: bool = True


@dataclass
class Device:
    device_id: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvVars:
    env_name: str
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class ProjectBundle:
    project_dir: Path
    env: EnvVars | None = None
    devices: list[Device] = field(default_factory=list)
    dynamic_functions: list[DynamicFunction] = field(default_factory=list)


# ---- 私有 IO/解析工具 ----

def _read_yaml(path: Path) -> dict[str, Any]:
    """读 yaml,失败统一抛 PlanLoadError(带文件路径便于排查)。"""
    if not path.is_file():
        raise PlanLoadError(f"YAML 文件不存在: {path}")
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as e:
        raise PlanLoadError(
            f"缺少 PyYAML 依赖,请 pip install PyYAML: {e}",
        ) from e
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise PlanLoadError(f"YAML 解析失败 {path}: {e}") from e
    if not isinstance(data, dict):
        raise PlanLoadError(f"YAML 根节点必须是 dict,实际 {type(data).__name__}: {path}")
    return data


def _load_dynamic_function_meta(py_path: Path) -> DynamicFunction | None:
    """从 .py 第一行匹配 `# AIQE_DYNAMIC_FUNCTION_META {...}`。

    匹配失败返回 None(不是抛错,允许目录里混入无关 .py,如 __init__.py / 工具脚本)。
    """
    try:
        first_line = py_path.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return None
    prefix = "# AIQE_DYNAMIC_FUNCTION_META "
    if not first_line.startswith(prefix):
        return None
    try:
        meta = json.loads(first_line[len(prefix):])
    except json.JSONDecodeError:
        return None
    if not isinstance(meta, dict):
        return None
    return DynamicFunction(
        function_code=str(meta.get("function_code", "")).strip(),
        function_type=str(meta.get("function_type", "")).strip(),
        function_name=str(meta.get("function_name", "")).strip(),
        description=str(meta.get("description", "")).strip(),
        params=list(meta.get("params") or []),
        outputs=list(meta.get("outputs") or []),
        abs_path=py_path,
        enabled=bool(meta.get("enabled", True)),
    )


def _load_dynamic_functions(project_dir: Path) -> list[DynamicFunction]:
    """递归扫 AI-动态函数管理/**/*.py,提取所有有效 meta 的函数。"""
    root = project_dir / FUNCTION_DIR_NAME
    if not root.is_dir():
        return []
    funcs: list[DynamicFunction] = []
    for py in root.rglob("*.py"):
        if py.name == "__init__.py":
            continue
        f = _load_dynamic_function_meta(py)
        if f and f.function_code:
            funcs.append(f)
    # 按 function_code 排序,便于 prompt 输出稳定
    return sorted(funcs, key=lambda x: x.function_code)


def _load_devices(project_dir: Path) -> list[Device]:
    """加载 AI-测试设备中心/*.yaml(全量)。"""
    root = project_dir / DEVICE_DIR_NAME
    if not root.is_dir():
        return []
    devs: list[Device] = []
    for yml in sorted(root.glob("*.yaml")):
        raw = _read_yaml(yml)
        devs.append(Device(device_id=yml.stem, raw=raw))
    return devs


def _load_env(project_dir: Path, env_name: str) -> EnvVars:
    env_dir = project_dir / ENV_DIR_NAME / env_name
    env_file = env_dir / "env_var.yaml"
    if not env_file.is_file():
        raise PlanLoadError(f"环境变量文件不存在: {env_file}")
    raw = _read_yaml(env_file)
    values: dict[str, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            # env_var.yaml 形如 `KEY: {description: ..., value: ...}`,扁平化为 KEY -> value
            if isinstance(v, dict) and "value" in v:
                values[str(k)] = str(v.get("value", ""))
            else:
                values[str(k)] = str(v) if v is not None else ""
    return EnvVars(env_name=env_name, values=values)


def _load_case_yaml(project_dir: Path, case_type: str, case_path_rel: str) -> dict[str, Any]:
    rel = case_path_rel.replace("\\", "/")
    p = project_dir / CASE_DIR_NAME / case_type / rel
    if not p.is_file():
        raise PlanLoadError(f"用例文件不存在: {p}")
    return _read_yaml(p)


def _resolve_case(
    project_dir: Path,
    case_type: str,
    source_id: str,
) -> tuple[dict[str, Any], Path]:
    """通过 _index.yaml 找到 source_id 对应的 case_path,再读 yaml。返回 (case, abs_path)。"""
    idx_path = project_dir / CASE_DIR_NAME / case_type / "_index.yaml"
    if not idx_path.is_file():
        raise PlanLoadError(f"{case_type} 用例 _index.yaml 不存在: {idx_path}")
    idx = _read_yaml(idx_path)
    if not isinstance(idx, dict) or source_id not in idx:
        raise PlanLoadError(f"{case_type} 用例索引找不到 source_id={source_id!r}")
    entry = idx[source_id]
    if not isinstance(entry, dict):
        raise PlanLoadError(f"{case_type} 用例索引条目不是 dict: {source_id}")
    rel_path = entry.get("case_path")
    if not rel_path:
        raise PlanLoadError(f"{case_type} 用例索引缺 case_path: {source_id}")
    case = _load_case_yaml(project_dir, case_type, str(rel_path))
    abs_case = project_dir / CASE_DIR_NAME / case_type / str(rel_path).replace("\\", "/")
    return case, abs_case


def _find_dynamic_function(
    project_dir: Path,
    function_code: str,
) -> DynamicFunction:
    for f in _load_dynamic_functions(project_dir):
        if f.function_code == function_code:
            return f
    raise PlanLoadError(
        f"动态函数 function_code={function_code!r} 在 {FUNCTION_DIR_NAME} 下未找到",
    )


def _parse_task(project_dir: Path, raw: dict[str, Any]) -> Task:
    title = str(raw.get("title", "")).strip()
    type_str = str(raw.get("type", "")).strip()
    source_id = str(raw.get("source_id", "")).strip()
    if not type_str or not source_id:
        raise PlanLoadError(f"task 缺 type/source_id: {raw}")
    try:
        case_type = CaseType(type_str)
    except ValueError as e:
        raise PlanLoadError(f"task.type 不支持: {type_str!r}") from e
    inputs = [
        TaskIO(name=str(x.get("name", "")).strip(), value=str(x.get("value", "")))
        for x in (raw.get("input_datas") or [])
        if isinstance(x, dict)
    ]
    outputs = [
        TaskIO(name=str(x.get("name", "")).strip(), value=str(x.get("value", "")))
        for x in (raw.get("output_datas") or [])
        if isinstance(x, dict)
    ]
    case: dict[str, Any] | None = None
    abs_path: Path | None = None
    if case_type in (CaseType.WEB, CaseType.API):
        case, abs_path = _resolve_case(project_dir, case_type.value, source_id)
    elif case_type == CaseType.DYNAMIC_FUNCTION:
        func = _find_dynamic_function(project_dir, source_id)
        abs_path = func.abs_path
    return Task(
        title=title,
        type=case_type,
        source_id=source_id,
        inputs=inputs,
        outputs=outputs,
        case=case,
        abs_path=abs_path,
    )


def _parse_flow(project_dir: Path, raw: dict[str, Any]) -> Flow:
    """解析 AI-自动化测试编排/{flow_id}.yaml。

    真实数据(2026-09-10 看 examples):
      - 根节点:`{name, priority, tags, case_flows: [{id, title, priority, tags, tasks}]}`
      - id 在 case_flows[0],不在根节点
    兼容写法:case_flows[0] 有 id/title/priority/tags 时优先用,fallback 到根节点字段。
    """
    case_flows = raw.get("case_flows") or []
    if not case_flows:
        raise PlanLoadError(f"flow 缺 case_flows: {raw}")
    cf = case_flows[0]
    if not isinstance(cf, dict):
        raise PlanLoadError(f"flow 的 case_flows[0] 不是 dict: {raw}")
    flow_id = str(cf.get("id", "")).strip()
    if not flow_id:
        raise PlanLoadError(f"flow 缺 id(case_flows[0].id): {raw}")
    # title 优先 case_flows[0].title,fallback 根节点 name,最后兜底为 flow_id
    flow_title = (
        str(cf.get("title", "")).strip()
        or str(raw.get("name", "")).strip()
        or flow_id
    )
    flow_priority = (
        str(cf.get("priority", "")).strip()
        or str(raw.get("priority", "")).strip()
    )
    flow_tags_raw = cf.get("tags") if cf.get("tags") is not None else raw.get("tags")
    flow_tags = [str(t).strip() for t in (flow_tags_raw or []) if str(t).strip()]
    tasks = [_parse_task(project_dir, t) for t in (cf.get("tasks") or []) if isinstance(t, dict)]
    return Flow(
        id=flow_id,
        title=flow_title,
        priority=flow_priority,
        tags=flow_tags,
        tasks=tasks,
    )


def load_plan(plan_id: str, project_dir: str | Path) -> tuple[Plan, ProjectBundle]:
    """主入口:解析测试计划 + 项目上下文,返回 (Plan, ProjectBundle)。

    Args:
        plan_id:测试计划 ID(对应 AI-自动化测试计划/{plan_id}/meta.yaml)
        project_dir:项目工作根目录(含 AI-* 8 个子目录)

    Raises:
        PlanLoadError:任一文件缺失 / yaml 解析失败 / 引用不一致
    """
    project_dir = Path(project_dir).resolve()
    if not project_dir.is_dir():
        raise PlanLoadError(f"项目工作目录不存在: {project_dir}")

    # 1) 加载 plan meta
    plan_meta_path = project_dir / PLAN_DIR_NAME / plan_id / "meta.yaml"
    if not plan_meta_path.is_file():
        raise PlanLoadError(f"测试计划 meta.yaml 不存在: {plan_meta_path}")
    raw = _read_yaml(plan_meta_path)
    plan_id_actual = str(raw.get("id") or plan_id).strip()
    name = str(raw.get("name", "")).strip()
    env_key_raw = raw.get("environmentKey")
    env_key = str(env_key_raw).strip() if env_key_raw else None
    strategy_str = str(raw.get("executionStrategy") or "serial").strip().lower()
    try:
        strategy = ExecStrategy(strategy_str)
    except ValueError as e:
        raise PlanLoadError(
            f"plan.executionStrategy 不支持: {strategy_str!r}(仅 serial/parallel)",
        ) from e

    # 2) 加载 flows
    flows_dir = project_dir / FLOW_DIR_NAME
    flows: list[Flow] = []
    for entry in raw.get("flows") or []:
        if not isinstance(entry, dict):
            continue
        flow_file_name = entry.get("sourceFlowFile")
        if not flow_file_name:
            raise PlanLoadError(f"plan.flows 条目缺 sourceFlowFile: {entry}")
        flow_path = flows_dir / str(flow_file_name)
        if not flow_path.is_file():
            raise PlanLoadError(f"编排文件不存在: {flow_path}")
        flow_raw = _read_yaml(flow_path)
        flows.append(_parse_flow(project_dir, flow_raw))

    if not flows:
        raise PlanLoadError(f"plan {plan_id} 没有 flows")

    plan = Plan(
        id=plan_id_actual,
        name=name,
        environment_key=env_key,
        strategy=strategy,
        flows=flows,
        flows_dir=flows_dir,
        cases_root=project_dir / CASE_DIR_NAME,
    )

    # 3) 加载 bundle(环境变量/设备/动态函数)
    env = _load_env(project_dir, env_key) if env_key else None
    devices = _load_devices(project_dir)
    funcs = _load_dynamic_functions(project_dir)
    bundle = ProjectBundle(
        project_dir=project_dir,
        env=env,
        devices=devices,
        dynamic_functions=funcs,
    )
    return plan, bundle


__all__ = [
    "PlanLoadError",
    "CaseType",
    "ExecStrategy",
    "TaskIO",
    "Task",
    "Flow",
    "Plan",
    "DynamicFunction",
    "Device",
    "EnvVars",
    "ProjectBundle",
    "load_plan",
]
