---
name: bigbear-test-runner
description: AIQE 测试计划 agent 调度版 CLI 的使用方式。当用户要在 AIQE 工作区里执行测试计划、提到 bigbear-test-runner、希望由 LLM agent 调度各 task、需要 playwright-cli 等 skill 介入,或编排型 / 多步工具调用型测试场景,必须使用本 Skill。需要给计划增加动态函数上下文 / 知识库引用 / 用例执行细节时也都适用。
---

# bigbear-test-runner CLI 使用

`bigbear-test-runner` 是华测 AIQE 测试计划的 **agent 调度版 CLI**。读入测试计划 + 项目数据,组装成结构化 prompt,交给 agentscope agent 调度 `playwright-cli` 等 skill 跑用例;每个 Flow 是 pytest / Allure 一条用例,每个 Task 是一个 Allure step,Task 内会单独调一次 agent。

它和 [`bigbear-test-runner`](../bigbear-test-runner/) **并行存在、各自适用**:

| 项目 | 调度方式 | 消耗 LLM token | 适用场景 |
|---|---|---|---|
| `bigbear-test-runner` | 单进程直跑,无 agent | 不消耗 | CI / 定时任务 / 不希望每次跑都烧 token |
| **bigbear-test-runner**(本项目) | agentscope agent 调度 | 每次执行都烧 token | LLM 决策 / 多步工具调用 / 编排型测试 |

适合 agent 版的关键场景:

- task 内部需要 LLM 决定下一步动作(看截图、调工具、写断言)
- 计划里同时混 web / api / 动态函数,需要 agent 跨工具编排
- 想要 Allure HTML 报告、按 Flow 分用例、按 Task 分 step 的可读执行轨迹
- 想给 agent 注入知识库引用、编码规范、用例执行注意事项等额外上下文

---

## 🚦 第 0 步:大模型 .env 检查(必须先做,否则直接终止)

> ⛔ **铁律 — 这是调用本 Skill 的第 0 步,在做任何其他事之前执行**。
>
> Agent(也就是你)在调用本 Skill 准备执行测试计划前,**必须**先检查当前工作目录下是否存在 `.env`、且其中是否包含非空的 `AGENT_AI_API_KEY`。
>
> 如果检测到**未配置**,**立即终止**流程,**不要**继续往下走(包括不要调 `bigbear-test-runner` CLI、不要加载 plan、不要装包、不要扫目录、不要生成任何 shell / 工具调用),直接用下面的"未配置时的终止话术"输出引导,等待用户填写完成后重试。

### 检查步骤(Agent 必须执行)

按以下顺序检查,**任意一项命中即视为已配置**,全部未命中才视为未配置:

1. **读取**当前工作目录下的 `.env` 文件(`Path.cwd()/.env`),逐行解析 `KEY=VALUE`,看是否有非空 `AGENT_AI_API_KEY`。
2. 若文件不存在 / `AGENT_AI_API_KEY` 为空 / 被注释 → 检查 `os.environ.get("AGENT_AI_API_KEY")` 是否有非空值。
3. 两者都没有 → **未配置**。

### 未配置时的终止话术(原文照搬,不要改写)

直接输出以下内容(**不要执行任何 shell / 工具调用**,停在这里等用户回复):

```text
🚦 bigbear-test-runner(agent 调度版)需要大模型 API key 才能执行,当前未配置,已终止流程。

原因: agent 调度版每个 Task 都会调一次 LLM 来决策下一步动作,所以必须配置 AGENT_AI_API_KEY。

请二选一填写:

【方式 1】在当前工作目录下创建 .env 文件(推荐)

  {cwd}/.env

  内容示例:
    AGENT_AI_API_KEY=sk-你的key
    AGENT_AI_MODEL=qwen-plus        # 可选
    AGENT_AI_BASE_URL=              # 可选
    AGENT_AI_TIMEOUT=30             # 可选
    AGENT_AI_MAX_RETRIES=1          # 可选

【方式 2】直接设系统环境变量(只对当前 shell 生效)

  Windows:  set AGENT_AI_API_KEY=sk-你的key
  Bash:     export AGENT_AI_API_KEY=sk-你的key

填写完成后告诉我"已就绪",我会重新执行测试计划。

—— 如果不想消耗 token,可以改用直跑版(SKILL全流程及工具/所有工具/bigbear-test-runner/,无需 LLM)。
```

### 反例(❌ 不要这样做)

- ❌ 不要在没配 key 的情况下继续调 `bigbear-test-runner` CLI 等它自己报"缺少 AGENT_AI_API_KEY"——浪费 token / 时间。
- ❌ 不要尝试用占位 key(如 `AGENT_AI_API_KEY=dummy`)绕过检查。
- ❌ 不要擅自读取系统里其他工具的 key(如 `OPENAI_API_KEY`、`DASHSCOPE_API_KEY`)作为替代。
- ❌ 不要帮用户瞎猜 / 编造 key,必须等用户提供真实 key。
- ❌ 不要直接跳过这条检查去执行——即使 plan 里只有 dynamic-function 类型的 task(动态函数不调 LLM),CLI 启动时仍会校验 key,不配会直接退出码 2。

---

## 安装

```bash
cd apps/bigbear-test-runner
pip install -e ".[dev]"
```

需要 Python 3.9+。`pip` 会安装 `agentscope`、`pytest`、`pytest-xdist`、`allure-pytest`、`Jinja2`、`python-dotenv`、`PyYAML`。

**生成 HTML 报告需要系统装 Allure CLI**(未装不影响跑用例,仍会产出 `allure-results/`,事后装上 CLI 再渲染即可)。

## 配置 .env

在执行命令的**当前工作目录**下放 `.env`(CLI 用 `Path.cwd()/.env` 加载,`override=False`,系统环境变量优先,与 `bigbear-test-runner` 保持一致):

```dotenv
# 必填
AGENT_AI_API_KEY=sk-xxxxxxxxxxxx

# 可选
AGENT_AI_MODEL=qwen-plus              # 默认 qwen-plus
AGENT_AI_BASE_URL=                    # 默认走 DashScope 官方 gateway
AGENT_AI_TIMEOUT=30                   # 单次 API 调用超时(秒),默认 30
AGENT_AI_MAX_RETRIES=1                # agentscope max_retries,默认 1
```

**严格不读 `DASHSCOPE_API_KEY`** —— 复用本项目自己定义的 `AGENT_AI_*` 系列,避免和 `bigbear-test-runner` 之外的工具冲突。

## 执行测试计划

```bash
bigbear-test-runner \
  --project-dir "D:\path\to\project_data" \
  --plan-id plan-20260610182912 \
  --skills-dir "D:\path\to\skills" \
  --debug
```

启动后做的事:

1. `plan_loader.load_plan(plan_id, project_dir)` 解析:
   - `AI-自动化测试计划/<plan_id>/meta.yaml` → Plan 元信息
   - `AI-自动化测试编排/<flow_file>.yaml` → Flow + Task 列表
   - `AI-自动化测试用例/<type>/_index.yaml` + `AI-自动化测试用例/<type>/<module>/<case_id>.yaml` → 用例内容
   - `AI-环境变量/<env_name>/env_var.yaml` → 环境变量拍平
   - `AI-测试设备中心/*.yaml` → 设备(浏览器 cdp_port 等)
   - `AI-动态函数管理/**/*.py` → 解析 `# AIQE_DYNAMIC_FUNCTION_META {...}` 头部,提取 `function_code` / `type` / `outputs` 等
2. CLI 把 Plan 和项目上下文交给 `executor.execute_plan()`
3. executor 启动 pytest,参数化收集后**一个 Flow 对应一条 pytest / Allure 用例**
4. `serial` 用 pytest 单进程逐条执行;`parallel` 用 pytest-xdist 并发
5. Flow 内按 Task 顺序执行;**每个 Task 是一个 Allure step,并单独调一次 Agent**
6. Task input 由代码用 Jinja2 + Flow context 渲染,Agent 输出按 output 定义写回 context
7. 执行记录写入 `allure-results/`;检测到 Allure CLI 时同时生成 `allure-report/` HTML

## CLI 参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--project-dir DIR` | **是** | 项目工作目录(含 `AI-自动化测试计划` / `AI-自动化测试编排` / `AI-自动化测试用例` / `AI-环境变量` / `AI-测试设备中心` / `AI-动态函数管理` 等子目录) |
| `--plan-id ID` | **是** | 测试计划 ID,对应 `<project-dir>/AI-自动化测试计划/<ID>/meta.yaml`,例:`plan-20260610182912` |
| `--skills-dir PATH` | 否(可重复) | Skill 根目录;Agent 通过 `LocalSkillLoader(scan_subdir=True)` 扫描所有指定目录下注册的 skill。**可以多次传**,让 skill 散落在多个项目里各自指向 |
| `--system-prompt TEXT` | 否 | 直接追加在代码内固定 system prompt 后面的文本 |
| `--system-prompt-file PATH` | 否 | 从文件读追加文本(**与 `--system-prompt` 互斥**) |
| `--report-dir PATH` | 否 | 报告输出目录;默认写到 `<project-dir>/AI-自动化测试报告/<plan-id>/<时间-运行ID>/` |
| `--debug` | 否 | 打印 agentscope debug 日志 + 应用层日志 + 每条非 TEXT 事件摘要 + 组装后 prompt |

**已移除** `--message / -m`:CLI 不再支持直接对话模式,只用于执行测试计划。

## 注入 system prompt(知识库 / 用例执行细节)

**触发条件:** 当用户在请求里**提到以下任何一类信息**时,**必须**主动用 `--system-prompt-file` 或 `--system-prompt` 传入:

- **"知识库" / "知识库引用"**:用户明确说出"知识库"或引用了知识库的使用方式、索引位置(如 `参考 /kb/api-glossary.md`、`用规范知识库 N3`、`按 X 知识库的 Y 条目执行` 等)。
- **"关于用例执行的具体信息"**:用户描述了用例的执行细节、上下文、特殊操作要求、特定业务约束、测试注意事项等,这些信息会影响 Agent 的执行判断。
- **任何明确希望"测试计划要参考"**的额外上下文(编码规范、token、特殊字段语义等)。

**核心原则:你只是传话,不是解析。**

- ❌ **不要**自己读知识库文件、解析索引、把用户的话"翻译"成更详细的提示词、或者添加用户没说的内容。
- ❌ **不要**对用户的语言再"添油加醋"(改写措辞、补全上下文、猜测意图)。
- ✅ **原原本本**把用户给的内容(无论是一段说明,还是一个引用路径 / 索引标识 / 知识库条目编号)传给 CLI,字面照传。
- ✅ 如果用户给的是"使用方式"或"索引位置"(如 `参考 /kb/api-glossary.md`、`调用知识库 X`),把这段**原话**作为 prompt 文本传入;**让 Agent 自己根据这段引用去决定怎么用**(例如自己用工具去读那个文件)。你不替它做。

**用法(短串用 `--system-prompt`,长串 / 多行 / 引用路径用 `--system-prompt-file`):**

```bash
# 短串:直接传
bigbear-test-runner --project-dir D:\proj --plan-id plan-xxx \
  --system-prompt "我们这个 plan 里所有接口都要带 token xyz"

# 长串 / 多行 / 引用路径:写文件再传
bigbear-test-runner --project-dir D:\proj --plan-id plan-xxx \
  --system-prompt-file /tmp/bigbear-test-runner-prompt-$(date +%s).md
```

文件路径**放在工作区外**(如 `/tmp/...`、`%TEMP%\...`),避免污染仓库;文件内容**等于**用户给的原文(或其直接拼接),不重写、不补全。

**典型场景示例:**

- 用户说"按我们的编码规范,接口 `x=1` 表示启用":
  → **原文照传**:`按我们的编码规范,接口 x=1 表示启用`。
  → ❌ 不要扩展成"参考以下企业编码规范:1. 接口字段 x 表示启用状态;2. ..."。
- 用户说"参考 `/kb/api-glossary.md` 这个知识库":
  → **原文照传**:`参考 /kb/api-glossary.md 这个知识库`。
  → ❌ 不要自己用 `Read` 工具去读 `/kb/api-glossary.md` 的内容塞进 prompt,也不要把文件内容塞进去。Agent 自己会处理。
- 用户说"我们这个 plan 里所有接口都要带 token `xyz`":
  → **原文照传**: `我们这个 plan 里所有接口都要带 token xyz`。

**不要触发的场景:**

- 用户没有提到知识库 / 用例执行细节,只是单纯要跑计划 → 不要主动加 `--system-prompt` / `--system-prompt-file`。
- 用户只关心 `dynamic-function` 类型(不调 LLM)→ 该参数不会影响纯 .py 脚本任务,但可以照传。

**原理:** 传入的 prompt 会被拼接到每个 Agent 的 system prompt 末尾,在整轮测试计划中作为统一上下文。Agent 拿到后按自己的方式决定怎么用(包括:直接参考 / 调用工具去读引用文件 / 调用知识库 API 等)。你的工作只是把用户的话送到那里。

## 4 个核心子目录

按 `AI-自动化测试{计划,编排,用例,执行}` 的默认布局走,**不需要**额外指定。除非用户明确要求自定义路径,不要主动加 `--plans-dir` / `--orchestration-dir` / `--cases-dir` / `--exec-dir` 之类的参数(本 CLI 不暴露这些 flag)。

项目目录约定(由 `plan_loader` 在 `--project-dir` 下扫描):

```
<project-dir>/
├── AI-自动化测试计划/<plan_id>/meta.yaml
├── AI-自动化测试编排/<flow_file>.yaml
├── AI-自动化测试用例/<type>/_index.yaml
│                       └─ <module>/<case_id>.yaml
├── AI-环境变量/<env_name>/env_var.yaml
├── AI-测试设备中心/*.yaml
└── AI-动态函数管理/**/*.py    # 解析 # AIQE_DYNAMIC_FUNCTION_META 头部
```

环境变量由 `python-dotenv` 自动加载,只读取执行命令时**当前工作目录**下的 `.env`,**不覆盖同名系统环境变量**。`--project-dir` 不参与 `.env` 查找;AI 相关的 key 直接配置在 `.env` 里,runner 会按计划展开。

## Task 执行模型

```
Flow = 一条 pytest / Allure 用例
└── Task = 一个 Allure step
    ├── Input   = Jinja2 渲染后的参数
    ├── Detail  = 只交给 Agent 当前 Task 的工作内容
    └── Output  = Agent 的结构化执行结果
```

每个 Flow 创建独立 context,初始包含计划环境变量。Task input 渲染完成后写入 context;Agent 最后一行**必须**输出:

```text
[task-result] {"status":"PASS","reason":"执行成功","outputs":{"phone_number":"13800138001"}}
```

`output_datas.value` 是 Agent outputs 的取值路径,支持 `response.token` 形式的点路径;取到的值写入 `context[output_datas.name]`,供后续 Task 使用。

## 执行策略

flow 之间串行还是并发,优先级:**计划 `meta.yaml` 的 `executionStrategy` > 默认值**:

- `serial`(默认):flow 逐个跑,同 flow 内 task 按顺序串行。
- `parallel`:flow 用 pytest-xdist 并发执行。

## agent 默认能力

每次启动 `bigbear-test-runner`,agent 自动获得以下 agentscope 内置工具 + 项目级工具:

| 工具 | 用途 |
|---|---|
| `Bash` | web / api 所需的 shell 命令;Windows 下实际由 `cmd.exe /c` 执行,Unix 使用 `/bin/sh -c` |
| `run_dynamic_function` | 确定性执行本计划已注册的动态函数;自动注入环境变量并合并 Flow outputs |

**沙箱策略:** 骨架阶段**不加 sandbox**,使用 agentscope 默认的 `LocalBackend`。agent 能读/写 cwd 下任意文件、跑任意 shell 命令。

**Permission mode = BYPASS(默认):** 默认构造 `AgentState(permission_context=PermissionContext(mode=PermissionMode.BYPASS))`,让所有工具调用自动 ALLOW。CLI 没有用户确认 UI,默认 `PermissionMode.DEFAULT` 会让 agent 在 `RequireUserConfirmEvent` 卡住 park 等用户;BYPASS 模式让"命令行启动 = 用户授权",流程跑通。

### dynamic-function 执行契约

动态函数**不再**由 agent 生成 `echo ... | python ...` 命令。CLI 只负责加载计划并把解析后的 `ProjectBundle` 交给执行层;`run_dynamic_function` 工具在构造时**自行**从项目数据中解析已启用的 `function_code -> abs_path` 和计划环境。

调用参数:

```json
{"function_code":"get_login_credentials","context":{}}
```

- `context` 只放当前 Flow 已产生的 outputs;首个任务传空对象。
- 计划选择的环境变量由工具自动注入,Flow outputs 的同名键优先。
- 工具固定使用当前 `sys.executable -X utf8 <script> --_context-stdin` 参数数组执行。
- stdout 必须是一个 JSON object;非零退出码、空输出、非法 JSON 都作为工具错误返回。
- 执行过程不读取 `run_creds.py`、`context.json` 等辅助文件,也不会创建临时 wrapper。

**Task 工具未装:** `TaskCreate` / `TaskGet` / `TaskList` / `TaskUpdate` 本期暂未挂入,留给后续 spec。

## 设备上下文

agent 调度版**不在 runner 阶段把设备列表注入 prompt**(这点和 `bigbear-test-runner` 不一样)。设备信息(`AI-测试设备中心/*.yaml`)会被 `plan_loader` 解析进 `ProjectBundle.devices`,由各 Agent 工具自行决定是否读取 —— 例如 web 用例会通过 Bash 调用 `playwright-cli`,由 `playwright-cli` 自行读设备中心。

> ✅ 这条和参考版 `bigbear-test-runner` 的"自动复制到 `batch_dir/devices/` + 拼到 `ai_prompt` 头部"行为**不同**,不要照搬。

## Skill 与平台

agent 调度版**没有 `--skill TYPE=NAME` 路由**(参考版那一套是给直跑版的)。本版只暴露 `--skills-dir PATH`,Agent 通过 `LocalSkillLoader(scan_subdir=True)` 扫描所有指定根目录,根据各 skill 自己的 `description` 自动决定用哪个。

典型用法(web 测试 plan):

```bash
bigbear-test-runner \
  --project-dir D:\proj \
  --plan-id plan-xxx \
  --skills-dir D:\work\skills-a \
  --skills-dir D:\work\bigbear-playwright-cli \
  --debug
```

多项目混用:把多个 skill 根目录**各自传一次** `--skills-dir`,Agent 在执行 Task 时按需加载。

## LLM 接口约定

| 环境变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `AGENT_AI_API_KEY` | **是** | — | Agent 自身 LLM key |
| `AGENT_AI_MODEL` | 否 | `qwen-plus` | 模型名 |
| `AGENT_AI_BASE_URL` | 否 | DashScope 官方 OpenAI 兼容端点 | 自定义 gateway |
| `AGENT_AI_TIMEOUT` | 否 | `30` | API 调用超时(秒),透传给 `openai.AsyncClient` |
| `AGENT_AI_MAX_RETRIES` | 否 | `1` | agentscope `max_retries`,失败重试次数 |

**base_url 透传路径(2026-09-10 修复 #a6f3322):**
agentscope 2.0.8 的 `DashScopeChatModel` 内部用 OpenAI 兼容协议(`openai.AsyncClient`),`base_url` 由 `DashScopeCredential.base_url` 字段持有,**不是模型参数**。所以 `AGENT_AI_BASE_URL` 透传到 `DashScopeCredential(api_key=..., base_url=...)`,再被模型读出来。

**超时 / 重试(2026-09-10 修复 hang):**
agentscope 默认 `max_retries=3` × `openai.AsyncClient` 默认 `timeout=600 秒`,单次失败最多 hang 30 分钟。骨架阶段压短到默认 `AGENT_AI_TIMEOUT=30` / `AGENT_AI_MAX_RETRIES=1`,可通过环境变量覆盖。

## 产物

报告路径:默认 `<project-dir>/AI-自动化测试报告/<plan-id>/<时间-运行ID>/`,可用 `--report-dir` 覆盖。

```
<report-dir>/
├── allure-results/                   # pytest 收集到的原始结果(JSON + 附件)
│   ├── <flow_id>-result.json
│   └── ...
└── allure-report/                    # 检测到 Allure CLI 时生成;否则不产生
    └── index.html
```

未装 Allure CLI 时**仍会完整保留 `allure-results/`**,事后装上 CLI 再 `allure generate` 即可出 HTML。

每个 Flow 一条 pytest 用例,每个 Task 一个 Allure step;Task 输出、Agent 流式响应、Bash 命令等会落到对应 step 的附件里。`--debug` 时还会额外把每条非 TEXT 事件摘要、组装后的 prompt 写到 stderr。

## 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 所有 Flow 通过 |
| `1` | 至少一个 Flow 失败;**Allure 报告仍会生成** |
| `2` | 参数 / 解析 / API 错误(缺 `AGENT_AI_API_KEY`、目录不存在、plan 加载失败、`--system-prompt` 与 `--system-prompt-file` 互斥、未捕获异常) |
| `130` | 用户中断(Ctrl-C) |

## 失败定位顺序

1. **看退出码**:`2` → 参数 / 环境(`AGENT_AI_API_KEY` 没配、目录不存在、plan 加载失败);`1` → 有 Flow 失败;`130` → Ctrl-C。
2. **加 `--debug` 重跑**:stderr 会打印 agentscope 阶段日志(`building` / `ready` / `sending` / `entering reply_stream` / `reply received` / `loop ended`)、每条非 TEXT 事件摘要、组装后的 prompt、以及 `flow[i] id=... title=... tasks=[...]` 的派发明细。
3. **看 Allure 报告**:打开 `allure-report/index.html`(需 Allure CLI 生成),失败 Flow / Task 会标红;点进 Task step 能看到 Agent 完整回复和 Bash 调用记录。
4. **看 `allure-results/`**:JSON + 附件里有 Task input、Agent 输出、`[task-result]` 行原文,可以直接定位是 input 渲染错、Agent 决策错、还是工具调用失败。
5. **Agent 卡死?** 长时间没看到 `reply received` 日志 → 大概率是 `AGENT_AI_TIMEOUT` × `AGENT_AI_MAX_RETRIES` 撑太久,Ctrl-C 后调小这两个值重跑。

## 已知限制 / 后续 TODO

- HTML 报告依赖系统装 Allure CLI;未装时仍完整保留 `allure-results/`,事后可手动生成。
- `Task*` 系列工具未挂入。
- 未实现跨 plan 调度、并发执行 plan(单 plan 内 Flow 并发已支持)。
- 不接 web 后端 / 不上报结果到 AIQE 平台。
- 骨架阶段不加 sandbox,Agent 能读 / 写 cwd 下任意文件、跑任意 shell 命令。
- 默认 PermissionMode = BYPASS,所有工具调用自动 ALLOW,无用户确认 UI。