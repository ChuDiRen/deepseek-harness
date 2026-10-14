# bigbear-test-runner

华测 AIQE **agent 调度版**测试运行 CLI。读取测试计划 + 项目数据,组装成结构化 prompt 交给 agentscope agent,由 agent 调度 `playwright-cli` skill 执行测试。

## 与 bigbear-test-runner 的关系

| 项目 | 调度方式 | 适用 |
|---|---|---|
| [`bigbear-test-runner`](../bigbear-test-runner/) | 单进程直跑,无 agent | CI / 定时任务 / 不消耗 LLM token |
| **bigbear-test-runner**(本项目) | agentscope agent 调度 | LLM 决策 / 多步工具调用 / 编排型测试 |

两者**并行存在**,不互相替代。本项目从骨架起步,逐步承接需要 agent 编排能力的测试场景。

## 安装

```bash
cd apps/bigbear-test-runner
pip install -e ".[dev]"
```

需要 Python 3.9+。pip 会安装 agentscope、pytest、pytest-xdist、allure-pytest 和 PyYAML。
生成 HTML 还需要系统安装 Allure CLI;未安装时不影响测试,仍会产出可供后续生成报告的 `allure-results`。

## 用法

### 1. 配置 .env

在执行目录下创建 `.env`:

```dotenv
# 必填
AGENT_AI_API_KEY=sk-xxxxxxxxxxxx

# 可选
AGENT_AI_MODEL=qwen-plus              # 默认 qwen-plus
AGENT_AI_BASE_URL=                    # 默认走 DashScope 官方 gateway
```

`.env` 加载规则与 `bigbear-test-runner` 一致 —— **只读 `Path.cwd()/.env`,`override=False`**,系统环境变量优先。

### 2. 执行测试计划

```bash
bigbear-test-runner \
  --project-dir "D:\path\to\project_data" \
  --plan-id plan-20260610182912 \
  --skills-dir "D:\path\to\skills" \
  --debug
```

启动后会:
1. `plan_loader.load_plan(plan_id, project_dir)` 解析:
   - `AI-自动化测试计划/{plan_id}/meta.yaml` → Plan 元信息(id / name / executionStrategy / environmentKey)
   - `AI-自动化测试编排/{flow_file}.yaml` → Flow + Task 列表
   - `AI-自动化测试用例/{type}/_index.yaml` + `AI-自动化测试用例/{type}/{module}/{case_id}.yaml` → web/api 用例内容
   - `AI-环境变量/{env_name}/env_var.yaml` → 环境变量拍平
   - `AI-测试设备中心/*.yaml` → 设备(浏览器 cdp_port 等)
   - `AI-动态函数管理/**/*.py` → 解析 `# AIQE_DYNAMIC_FUNCTION_META {...}` 头部,提取 function_code/type/outputs 等
2. CLI 把 Plan 和项目上下文交给 `executor.execute_plan()`
3. executor 启动 pytest,参数化收集后一个 Flow 对应一条 pytest / Allure 用例
4. `serial` 使用 pytest 单进程逐条执行,`parallel` 使用 pytest-xdist 并发执行
5. Flow 内按 Task 顺序执行;每个 Task 是一个 Allure step,并单独调用一次 Agent
6. Task input 由代码使用 Jinja2 + Flow context 渲染,Agent 输出再按 output 定义写回 context
7. 执行记录写入 `allure-results`;检测到 Allure CLI 时同时生成 `allure-report` HTML

### 3. CLI 参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--project-dir DIR` | 是 | 项目工作目录(含 AI-* 子目录) |
| `--plan-id ID` | 是 | 测试计划 ID,对应 `<project-dir>/AI-自动化测试计划/<ID>/meta.yaml` |
| `--skills-dir PATH` | 否(可重复) | Skill 根目录;agent 加载目录下注册的 skill |
| `--system-prompt TEXT` | 否 | 直接追加在代码内固定 system prompt 后面的文本 |
| `--system-prompt-file PATH` | 否 | 从文件读追加文本(与 `--system-prompt` 互斥) |
| `--report-dir PATH` | 否 | 报告输出目录;默认写入项目的 `AI-自动化测试报告/<plan-id>/<时间-运行ID>/` |
| `--debug` | 否 | 打印 agentscope debug 日志 + 应用层日志 + 打印组装后的 prompt |

**已移除** `--message/-m`:CLI 不再支持直接对话模式,只用于执行测试计划。

### 4. Task 执行模型

```
Flow = 一条 pytest / Allure 用例
└── Task = 一个 Allure step
    ├── Input  = Jinja2 渲染后的参数
    ├── Detail = 只交给 Agent 当前 Task 的工作内容
    └── Output = Agent 的结构化执行结果
```

每个 Flow 创建独立 context,初始包含计划环境变量。Task input 渲染完成后写入 context；Agent 最后一行必须输出:

```text
[task-result] {"status":"PASS","reason":"执行成功","outputs":{"phone_number":"13800138001"}}
```

`output_datas.value` 是 Agent outputs 的取值路径，支持 `response.token` 形式的点路径；取到的值写入 `context[output_datas.name]`，供后续 Task 使用。

### 5. 验证

```bash
bigbear-test-runner --version   # → bigbear-test-runner 0.1.0
python -m bigbear_test_runner   # 等价于 bigbear-test-runner
```

## 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 所有 Flow 通过 |
| 1 | 至少一个 Flow 失败,Allure 报告仍会生成 |
| 2 | 参数 / 解析 / API 错误(缺 `AGENT_AI_API_KEY`、目录不存在、plan 加载失败、`--system-prompt` 与 `--system-prompt-file` 互斥) |
| 130 | 用户中断(Ctrl-C) |

## LLM 接口约定

环境变量复用 `bigbear-test-runner` 的 `AGENT_AI_*` 系列,**严格不读 `DASHSCOPE_API_KEY`**。

| 环境变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `AGENT_AI_API_KEY` | 是 | — | agent 自身 LLM key |
| `AGENT_AI_MODEL` | 否 | `qwen-plus` | 模型名 |
| `AGENT_AI_BASE_URL` | 否 | DashScope 官方 OpenAI 兼容端点 | 自定义 gateway |
| `AGENT_AI_TIMEOUT` | 否 | `30` | API 调用超时(秒),透传给 openai.AsyncClient |
| `AGENT_AI_MAX_RETRIES` | 否 | `1` | agentscope `max_retries`,失败重试次数 |

**base_url 透传路径(2026-09-10 修复 #a6f3322):**
agentscope 2.0.8 的 `DashScopeChatModel` 内部用 OpenAI 兼容协议(`openai.AsyncClient`),`base_url` 由 `DashScopeCredential.base_url` 字段持有,**不是模型参数**。所以 `AGENT_AI_BASE_URL` 透传到 `DashScopeCredential(api_key=..., base_url=...)`,再被模型读出来。

**超时/重试(2026-09-10 修复 hang):**
agentscope 默认 `max_retries=3` × `openai.AsyncClient` 默认 `timeout=600 秒`,单次失败最多 hang 30 分钟。骨架阶段压短到默认 `AGENT_AI_TIMEOUT=30` / `AGENT_AI_MAX_RETRIES=1`,可通过环境变量覆盖。

## 测试

```bash
cd apps/bigbear-test-runner
PYTHONPATH=src python -m pytest tests/ -v
```

测试**不依赖真实 agentscope 包** —— 通过 `sys.modules` 注入假 `agentscope` 模块,验证:
- `plan_loader.load_plan()` 完整成功路径 + 各种 PlanLoadError 失败路径
- `prompt_builder.build_task_message()` / `build_system_prompt()` 只生成当前 Task 的 input/detail/output prompt
- `executor.execute_plan()` 只负责启动 pytest、选择串行/并发模式和生成报告
- `pytest_flow_case.py` 负责 Jinja2 输入渲染、Task Allure step、Agent 调用、context 更新和结果判定
- pytest 参数化后一个 Flow 对应一条测试用例,失败结果映射为 pytest failure
- `build_agent()` 把 `AGENT_AI_*` 正确映射到 agentscope 入参;`system_prompt` 透传给 Agent
- `run_streaming()` 把 `TEXT_BLOCK_DELTA` 事件内容写到 stdout
- cli.main() 在不同错误路径下返回正确退出码

## agent 默认能力

每次启动 `bigbear-test-runner`,agent 自动获得以下 agentscope 内置工具:

| 工具 | 用途 |
|---|---|
| `Bash` | web/api 所需的 shell 命令；Windows 下实际由 `cmd.exe /c` 执行 |
| `run_dynamic_function` | 确定性执行本计划已注册的动态函数;自动注入环境变量并合并 Flow outputs |

AgentScope 的工具名称虽然是 `Bash`,但会按宿主系统选择 shell：Windows 使用 `cmd.exe /c`,Unix 使用 `/bin/sh -c`。

**沙箱策略(2026-09-10 决策):** 骨架阶段**不加 sandbox**,使用 agentscope 默认的 `LocalBackend`。agent 能读/写 cwd 下任意文件、跑任意 shell 命令。

**Permission mode = BYPASS(2026-09-10):** 默认构造 `AgentState(permission_context=PermissionContext(mode=PermissionMode.BYPASS))`,让所有工具调用自动 ALLOW。CLI 没有用户确认 UI,默认 PermissionMode.DEFAULT 会让 agent 在 `RequireUserConfirmEvent` 卡住 park 等用户,BYPASS 模式让命令行启动 = 用户授权,流程跑通。

### dynamic-function 执行契约

动态函数不再由 agent 生成 `echo ... | python ...` 命令。CLI 只负责加载计划并把解析后的 `ProjectBundle` 交给执行层；`run_dynamic_function` 在构造时自行从项目数据中解析已启用的 `function_code -> abs_path` 和计划环境。调用参数为:

```json
{"function_code":"get_login_credentials","context":{}}
```

- `context` 只放当前 Flow 已产生的 outputs;首个任务传空对象。
- 计划选择的环境变量由工具自动注入,Flow outputs 的同名键优先。
- 工具固定使用当前 `sys.executable -X utf8 <script> --_context-stdin` 参数数组执行。
- stdout 必须是一个 JSON object;非零退出码、空输出、非法 JSON 都作为工具错误返回。
- 执行过程不读取 `run_creds.py`、`context.json` 等辅助文件,也不会创建临时 wrapper。

**Task 工具未装:** `TaskCreate` / `TaskGet` / `TaskList` / `TaskUpdate` 本期暂未挂入,留给后续 spec。

## 项目结构

```
apps/bigbear-test-runner/
├── pyproject.toml
├── README.md
├── src/
│   └── bigbear_test_runner/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py            # argparse + plan 加载 + 退出码
│       ├── executor.py       # Flow 级 serial / parallel 调度
│       ├── dynamic_function.py # 动态函数 argv + stdin 确定性执行器及 AgentScope 工具
│       ├── agent.py          # agentscope 封装(build_agent / run_streaming)
│       ├── events.py         # 事件摘要工具
│       ├── plan_loader.py    # 解析 project_data/*.yaml + *.py → 结构化对象
│       ├── pytest_flow_case.py # pytest 参数化运行入口(一个 Flow 一条用例)
│       └── prompt_builder.py # 单 Task input/detail/output → markdown prompt
└── tests/
    ├── __init__.py
    ├── test_agent.py         # build_agent / run_streaming smoke
    ├── test_dynamic_function.py # 动态函数执行协议、中文路径及失败路径
    ├── test_executor.py      # Flow 级串行/并发调度
    ├── test_cli.py           # cli.main 各种边界 + 最小 project_data fixture
    ├── test_plan_loader.py   # load_plan 成功/失败路径
    ├── test_prompt_builder.py # build_task_message / build_system_prompt 章节渲染
    └── test_pytest_flow_case.py # context、Jinja2 和 Task 输出协议
```

设计文档:见 `docs/superpowers/specs/`(本改造的 spec 由用户决策跳过文档阶段,直接编码)。

## 已知限制 / 后续 TODO

- HTML 报告依赖系统安装 Allure CLI;未安装时仍会完整保留 `allure-results`
- `Task*` 系列工具未挂入
- 未实现跨 plan 调度、并发执行 plan(单 plan 内已支持 Flow 并发)
- 不接 web 后端 / 不上报结果到 AIQE 平台
