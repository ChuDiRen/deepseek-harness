---
name: bigbear-test-runner
description: AIQE 测试计划 agent 调度版 CLI 的使用方式。当用户要在 AIQE 工作区里执行测试计划、提到 bigbear-test-runner、希望由 LLM agent 调度各 task、需要 playwright-cli 等 skill 介入,或编排型 / 多步工具调用型测试场景,必须使用本 Skill。
---

# bigbear-test-runner CLI 使用

通过 agentscope agent 调度 `playwright-cli` 等 skill 跑用例。

---

## 🚦 第 1 步 · 检查 `.env`

当前工作目录必须有 `.env` 且 `AGENT_AI_API_KEY` 非空:

```bash
test -f ".env" && grep -E '^AGENT_AI_API_KEY=.+$' ".env" && echo "✓ OK" || echo "✗ MISS"
```

未配置立即终止,提示用户:

```text
🚦 bigbear-test-runner 需要大模型 API key 才能执行,当前未配置,已终止流程。

请在当前工作目录下创建 .env 文件:

  {cwd}/.env

  内容示例:
    AGENT_AI_API_KEY=sk-你的key
    AGENT_AI_MODEL=qwen-plus        # 可选
    AGENT_AI_BASE_URL=              # 可选
    AGENT_AI_TIMEOUT=30             # 可选
    AGENT_AI_MAX_RETRIES=1          # 可选

填写完成后告诉我"已就绪",我会重新执行测试计划。
```

### 安装(如未安装)

输入`bigbear-test-runner -h` 如果没有显示对应的帮助信息

则：进行安装

```bash
cd apps/bigbear-test-runner
pip install -e ".[dev]"
```

---

## 🚦 第 2 步 · 检测系统

```bash
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
  OS="windows"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  OS="mac"
else
  OS="linux"
fi
echo "当前系统: $OS"
```

**Windows cmd 务必先设中文编码再执行:**

```bash
chcp 65001
```

---

## 🚦 第 3 步 · 执行测试计划

### 启动后做的事

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

### executionStrategy 选型建议

plan 的 `meta.yaml` 通过 `executionStrategy` 控制 Flow 维度的执行方式(单个 Flow 内的 Task 始终按定义顺序串行执行,与此字段无关):

| 取值 | 执行方式 | 适用场景 |
|---|---|---|
| `serial` | pytest 单进程逐条 Flow 执行 | 有状态依赖(token 传递、登录态串联)、调试期排查问题、Flow 数较少(<20)的场景 |
| `parallel` | pytest-xdist 多 worker 并发执行 | Flow 之间完全无依赖(各自独立登录 / 独立数据准备)、想压短总时长、或要做大规模回归 |

**选型判断流程:**

1. Flow 之间是否存在数据/上下文依赖(如后置 Flow 依赖前置 Flow 产出的 token / cookie / DB 数据)?
   - **是** → 选 `serial`(避免并发导致的数据竞争或前序未就绪)
   - **否** → 继续看 2
2. 是否处于调试期、需要按顺序看每条 Flow 的失败现象、便于打断点重试?
   - **是** → 选 `serial`
   - **否** → 继续看 3
3. Flow 总数与并发收益?
   - Flow 数 <20 → `serial` 与 `parallel` 差异不大,默认 `serial` 更简单可控
   - Flow 数 ≥20、且彼此独立 → `parallel` 收益明显(总时长 ≈ 最长单 Flow 时长)

### 执行命令

```bash
bigbear-test-runner \
  --project-dir "项目目录绝对路径" \
  --plan-id plan-xxx \
  --skills-dir "skills 目录绝对路径" \
  --system-prompt "系统提示词" \
  --debug
```

**Windows 示例:**

```bash
bigbear-test-runner --project-dir "D:\path\to\project_data" --plan-id plan-20260610182912 --skills-dir "D:\path\to\skills"  --system-prompt "通过playwright-cli进行执行，要显示浏览器页面。所有 web 任务的 playwright-cli open 命令都必须加 --headed，让浏览器窗口可见。" --debug
```

**Mac 示例:**

```bash
bigbear-test-runner --project-dir "/Users/xxx/project_data" --plan-id plan-20260610182912 --skills-dir "/Users/xxx/skills"  --system-prompt "通过playwright-cli进行执行，要显示浏览器页面。所有 web 任务的 playwright-cli open 命令都必须加 --headed，让浏览器窗口可见。" --debug
```

### 注入 system prompt(知识库 / 用例执行细节)

**触发条件:** 当用户在请求里**提到以下任何一类信息**时,**必须**主动用 `--system-prompt-file` 或 `--system-prompt` 传入:

- **"知识库" / "知识库引用"**:用户明确说出"知识库"或引用了知识库的使用方式、索引位置(如 `参考 /kb/api-glossary.md`、`用规范知识库 N3`、`按 X 知识库的 Y 条目执行` 等)。
- **"关于用例执行的具体信息"**:用户描述了用例的执行细节、上下文、特殊操作要求、特定业务约束、测试注意事项等,这些信息会影响 Agent 的执行判断。
- **任何明确希望"测试计划要参考"**的额外上下文(编码规范、token、特殊字段语义等)。

**核心原则:你只是传话,不是解析。**

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

### CLI 参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--project-dir DIR` | **是** | 项目工作目录(含 `AI-自动化测试计划` / `AI-自动化测试编排` / `AI-自动化测试用例` / `AI-环境变量` / `AI-测试设备中心` / `AI-动态函数管理` 等子目录) |
| `--plan-id ID` | **是** | 测试计划 ID,对应 `<project-dir>/AI-自动化测试计划/<ID>/meta.yaml`,例:`plan-20260610182912` |
| `--skills-dir PATH` | 否(可重复) | Skill 根目录;Agent 通过 `LocalSkillLoader(scan_subdir=True)` 扫描所有指定目录下注册的 skill。**可以多次传**,让 skill 散落在多个项目里各自指向 |
| `--system-prompt TEXT` | 否 | 直接追加在代码内固定 system prompt 后面的文本 |
| `--system-prompt-file PATH` | 否 | 从文件读追加文本(**与 `--system-prompt` 互斥**) |
| `--report-dir PATH` | 否 | 报告输出目录;默认写到 `<project-dir>/AI-自动化测试报告/<plan-id>/<时间-运行ID>/` |
| `--debug` | 否 | 打印 agentscope debug 日志 + 应用层日志 + 每条非 TEXT 事件摘要 + 组装后 prompt |

### Skill 与平台

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

### 项目目录约定

```
<project-dir>/
├── AI-自动化测试计划/<plan_id>/meta.yaml
├── AI-自动化测试编排/<flow_file>.yaml
├── AI-自动化测试用例/<type>/<module>/<case_id>.yaml
├── AI-环境变量/<env_name>/env_var.yaml
└── AI-动态函数管理/**/*.py
```



---

## 💡 执行要点

- 路径用绝对路径,Windows 用 `D:\xxx`,Mac 用 `/Users/xxx`。
- Windows cmd 必须先 `chcp 65001` 再执行,避免中文乱码。
- agent 调度版每次执行都会消耗 LLM token。
- 报告路径:默认 `<project-dir>/AI-自动化测试报告/<plan-id>/<时间-运行ID>/allure-results/`