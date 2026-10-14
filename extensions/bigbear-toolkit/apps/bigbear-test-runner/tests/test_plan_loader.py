"""plan_loader 单元测试。

不依赖真实 project_data;用 tmp_path 构造最小目录结构,验证:
- load_plan 完整成功路径
- 缺关键文件 / yaml 解析失败 / 引用不一致 全部抛 PlanLoadError
"""
from __future__ import annotations

from pathlib import Path

import pytest

from bigbear_test_runner import plan_loader


# ---- 最小 project_data 构造辅助 ----

PLAN_ID = "plan-test-001"
FLOW_ID = "flow-test-001"
CASE_ID = "case-test-001"
FUNCTION_CODE = "fn_test"


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _make_mini_project(
    project: Path,
    *,
    plan_id: str = PLAN_ID,
    flow_id: str = FLOW_ID,
    case_id: str = CASE_ID,
    function_code: str = FUNCTION_CODE,
    with_env: bool = True,
    with_device: bool = True,
    strategy: str = "serial",
) -> None:
    _write(
        project / "AI-自动化测试计划" / plan_id / "meta.yaml",
        f"""id: {plan_id}
name: 测试计划
environmentKey: default
executionStrategy: {strategy}
flows:
  - sourceFlowFile: {flow_id}.yaml
    sourceFlowId: {flow_id}
""",
    )
    _write(
        project / "AI-自动化测试编排" / f"{flow_id}.yaml",
        f"""name: 测试流程
priority: high
tags: [冒烟]
case_flows:
  - id: {flow_id}
    title: 测试流程
    priority: high
    tags: [冒烟]
    tasks:
      - title: 调函数
        type: dynamic-function
        source_id: {function_code}
        output_datas:
          - name: 手机号
            value: phone_number
      - title: 登录
        type: web
        source_id: {case_id}
        input_datas:
          - name: 手机号
            value: '{{{{手机号}}}}'
        output_datas: []
""",
    )
    _write(
        project / "AI-自动化测试用例" / "web" / "_index.yaml",
        f"""{case_id}:
  case_id: {case_id}
  case_title: 登录
  case_path: 登录/{case_id}.yaml
  case_type: web
""",
    )
    _write(
        project / "AI-自动化测试用例" / "web" / "登录" / f"{case_id}.yaml",
        f"""case_id: {case_id}
case_type: web
case_title: 登录
case_content:
  steps:
    - 打开网址 http://example.com
  expected:
    - 成功
""",
    )
    if with_env:
        _write(
            project / "AI-环境变量" / "default" / "env_var.yaml",
            """TEST_PHONE_NUMBER:
  value: '13800138001'
TEST_PASSWORD:
  value: '123456'
""",
        )
    if with_device:
        _write(
            project / "AI-测试设备中心" / "chrome001.yaml",
            """type: browser
cdp_port: 9222
""",
        )
    _write(
        project / "AI-动态函数管理" / "通用工具" / f"{function_code}.py",
        f"""# AIQE_DYNAMIC_FUNCTION_META {{"function_code": "{function_code}", "function_type": "通用工具", "function_name": "测试函数", "description": "desc", "enabled": true, "params": [], "outputs": [{{"key": "phone_number", "name": "手机号"}}]}}

def execute(**kwargs):
    return {{"phone_number": "13800138001"}}
""",
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    p = tmp_path / "project"
    _make_mini_project(p)
    return p.resolve()


# ---- 成功路径 ----

def test_load_plan_success(project: Path) -> None:
    plan, bundle = plan_loader.load_plan(PLAN_ID, project)

    assert plan.id == PLAN_ID
    assert plan.name == "测试计划"
    assert plan.environment_key == "default"
    assert plan.strategy == plan_loader.ExecStrategy.SERIAL
    assert len(plan.flows) == 1

    flow = plan.flows[0]
    assert flow.id == FLOW_ID
    assert flow.title == "测试流程"
    assert flow.priority == "high"
    assert flow.tags == ["冒烟"]
    assert len(flow.tasks) == 2

    t0 = flow.tasks[0]
    assert t0.title == "调函数"
    assert t0.type == plan_loader.CaseType.DYNAMIC_FUNCTION
    assert t0.source_id == FUNCTION_CODE
    assert t0.outputs == [plan_loader.TaskIO(name="手机号", value="phone_number")]
    assert t0.case is None
    assert t0.abs_path is not None
    assert t0.abs_path.name == f"{FUNCTION_CODE}.py"

    t1 = flow.tasks[1]
    assert t1.title == "登录"
    assert t1.type == plan_loader.CaseType.WEB
    assert t1.source_id == CASE_ID
    assert t1.inputs == [plan_loader.TaskIO(name="手机号", value="{{手机号}}")]
    assert t1.case is not None
    assert t1.case["case_id"] == CASE_ID
    assert t1.abs_path is not None
    assert t1.abs_path.name == f"{CASE_ID}.yaml"

    assert bundle.env is not None
    assert bundle.env.env_name == "default"
    assert bundle.env.values["TEST_PHONE_NUMBER"] == "13800138001"
    assert bundle.env.values["TEST_PASSWORD"] == "123456"

    assert len(bundle.devices) == 1
    assert bundle.devices[0].device_id == "chrome001"
    assert bundle.devices[0].raw["cdp_port"] == 9222

    assert len(bundle.dynamic_functions) == 1
    fn = bundle.dynamic_functions[0]
    assert fn.function_code == FUNCTION_CODE
    assert fn.function_type == "通用工具"
    assert fn.function_name == "测试函数"


def test_load_plan_parallel_strategy(project: Path) -> None:
    _write(
        project / "AI-自动化测试计划" / PLAN_ID / "meta.yaml",
        f"""id: {PLAN_ID}
environmentKey: default
executionStrategy: parallel
flows:
  - sourceFlowFile: {FLOW_ID}.yaml
    sourceFlowId: {FLOW_ID}
""",
    )
    plan, _ = plan_loader.load_plan(PLAN_ID, project)
    assert plan.strategy == plan_loader.ExecStrategy.PARALLEL


def test_load_plan_default_strategy_is_serial(project: Path) -> None:
    """plan.meta.yaml 缺 executionStrategy 时,默认 serial。"""
    _write(
        project / "AI-自动化测试计划" / PLAN_ID / "meta.yaml",
        f"""id: {PLAN_ID}
environmentKey: default
flows:
  - sourceFlowFile: {FLOW_ID}.yaml
""",
    )
    plan, _ = plan_loader.load_plan(PLAN_ID, project)
    assert plan.strategy == plan_loader.ExecStrategy.SERIAL


# ---- 失败路径 ----

def test_load_plan_project_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(plan_loader.PlanLoadError, match="项目工作目录不存在"):
        plan_loader.load_plan(PLAN_ID, tmp_path / "not-exist")


def test_load_plan_meta_missing(project: Path) -> None:
    (project / "AI-自动化测试计划" / PLAN_ID / "meta.yaml").unlink()
    with pytest.raises(plan_loader.PlanLoadError, match="meta.yaml 不存在"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_flow_file_missing(project: Path) -> None:
    (project / "AI-自动化测试编排" / f"{FLOW_ID}.yaml").unlink()
    with pytest.raises(plan_loader.PlanLoadError, match="编排文件不存在"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_case_index_missing(project: Path) -> None:
    (project / "AI-自动化测试用例" / "web" / "_index.yaml").unlink()
    with pytest.raises(plan_loader.PlanLoadError, match="_index.yaml 不存在"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_case_source_id_not_in_index(project: Path) -> None:
    _write(
        project / "AI-自动化测试编排" / f"{FLOW_ID}.yaml",
        f"""name: 测试流程
case_flows:
  - id: {FLOW_ID}
    title: 测试流程
    tasks:
      - title: 登录
        type: web
        source_id: not-exist-case-id
""",
    )
    with pytest.raises(plan_loader.PlanLoadError, match="找不到 source_id"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_case_yaml_missing(project: Path) -> None:
    _write(
        project / "AI-自动化测试用例" / "web" / "_index.yaml",
        f"""{CASE_ID}:
  case_id: {CASE_ID}
  case_title: 登录
  case_path: 登录/{CASE_ID}.yaml
""",
    )
    # 删掉 case yaml 但保留 _index.yaml 引用
    (project / "AI-自动化测试用例" / "web" / "登录" / f"{CASE_ID}.yaml").unlink()
    with pytest.raises(plan_loader.PlanLoadError, match="用例文件不存在"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_dynamic_function_missing(project: Path) -> None:
    # 删掉动态函数 .py
    (project / "AI-动态函数管理" / "通用工具" / f"{FUNCTION_CODE}.py").unlink()
    with pytest.raises(plan_loader.PlanLoadError, match="动态函数 function_code"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_env_missing(project: Path) -> None:
    (project / "AI-环境变量" / "default" / "env_var.yaml").unlink()
    with pytest.raises(plan_loader.PlanLoadError, match="环境变量文件不存在"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_unsupported_strategy(project: Path) -> None:
    _write(
        project / "AI-自动化测试计划" / PLAN_ID / "meta.yaml",
        f"""id: {PLAN_ID}
executionStrategy: chaos
flows:
  - sourceFlowFile: {FLOW_ID}.yaml
""",
    )
    with pytest.raises(plan_loader.PlanLoadError, match="executionStrategy 不支持"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_unsupported_task_type(project: Path) -> None:
    _write(
        project / "AI-自动化测试编排" / f"{FLOW_ID}.yaml",
        f"""name: 测试流程
case_flows:
  - id: {FLOW_ID}
    title: 测试流程
    tasks:
      - title: 瞎写的 type
        type: ios
        source_id: xxx
""",
    )
    with pytest.raises(plan_loader.PlanLoadError, match="task.type 不支持"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_yaml_invalid(project: Path) -> None:
    _write(
        project / "AI-自动化测试计划" / PLAN_ID / "meta.yaml",
        "id: 'abc\nenvironmentKey: default\nflows: : : invalid",
    )
    with pytest.raises(plan_loader.PlanLoadError, match="YAML 解析失败"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_no_flows(project: Path) -> None:
    _write(
        project / "AI-自动化测试计划" / PLAN_ID / "meta.yaml",
        """id: plan-test-001
environmentKey: default
flows: []
""",
    )
    with pytest.raises(plan_loader.PlanLoadError, match="没有 flows"):
        plan_loader.load_plan(PLAN_ID, project)


def test_load_plan_no_environment_key(tmp_path: Path) -> None:
    """plan 不指定 environmentKey 时,bundle.env 为 None 且不要求 env_var.yaml 存在。"""
    project = tmp_path / "p"
    _make_mini_project(project, with_env=False, with_device=False)
    # 把 meta.yaml 的 environmentKey 删掉
    _write(
        project / "AI-自动化测试计划" / PLAN_ID / "meta.yaml",
        f"""id: {PLAN_ID}
executionStrategy: serial
flows:
  - sourceFlowFile: {FLOW_ID}.yaml
""",
    )
    plan, bundle = plan_loader.load_plan(PLAN_ID, project)
    assert plan.environment_key is None
    assert bundle.env is None
    assert bundle.devices == []


def test_dynamic_function_skips_files_without_meta(project: Path) -> None:
    """AI-动态函数管理 下无关 .py(__init__.py / 工具脚本)应被忽略,不抛错。"""
    _write(
        project / "AI-动态函数管理" / "通用工具" / "__init__.py",
        "# 这是 __init__,不是动态函数\n",
    )
    _write(
        project / "AI-动态函数管理" / "通用工具" / "broken.py",
        "def execute(**kwargs):\n    return {}\n",  # 缺 META 行
    )
    plan, bundle = plan_loader.load_plan(PLAN_ID, project)
    # 仅 1 个有效动态函数(broken 被忽略)
    assert len(bundle.dynamic_functions) == 1
    assert bundle.dynamic_functions[0].function_code == FUNCTION_CODE


def test_api_case_resolves_correctly(tmp_path: Path) -> None:
    """api 类型的 task 也走 _index.yaml + case yaml 解析。"""
    project = tmp_path / "p"
    _make_mini_project(project)

    api_case_id = "api-case-001"
    _write(
        project / "AI-自动化测试用例" / "api" / "_index.yaml",
        f"""{api_case_id}:
  case_id: {api_case_id}
  case_title: 登录API
  case_path: 20260610/{api_case_id}.yaml
""",
    )
    _write(
        project / "AI-自动化测试用例" / "api" / "20260610" / f"{api_case_id}.yaml",
        f"""case_id: {api_case_id}
case_type: api
case_title: 登录API
case_content:
  request:
    url: http://example.com/login
    method: POST
  expected:
    - code = 200
""",
    )
    _write(
        project / "AI-自动化测试编排" / f"{FLOW_ID}.yaml",
        f"""name: API流程
case_flows:
  - id: {FLOW_ID}
    title: API流程
    tasks:
      - title: API登录
        type: api
        source_id: {api_case_id}
        output_datas: []
""",
    )

    plan, _ = plan_loader.load_plan(PLAN_ID, project)
    task = plan.flows[0].tasks[0]
    assert task.type == plan_loader.CaseType.API
    assert task.source_id == api_case_id
    assert task.case is not None
    assert task.case["case_content"]["request"]["method"] == "POST"
