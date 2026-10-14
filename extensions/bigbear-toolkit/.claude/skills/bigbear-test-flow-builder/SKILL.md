---
name: bigbear-test-flow-builder
description: 对话式引导构建完整的自动化测试流程。触发场景：用户要求编排测试流程、生成完整测试链路、创建自动化测试 flow。手工用例优先转换为自动化用例 YAML，动态函数委托已有 Skill 生成，最终串联为 case_flow 编排文件。支持接口、Web UI、性能等全部测试类型，智能复用已有资源。
enabled: true
---
重点：请使用中文沟通！！

# bigbear-test-flow-builder — 测试流程构建器

对话式引导构建完整的自动化测试流程：精读源材料 → 手工用例转换自动化用例 → 编排串联，全程智能复用已有资源。动态函数委托已有 Skill，自动化用例优先从手工用例转换。

---

## 🎯 我该怎么用这个技能？

### 一句话理解

你描述一个测试场景，AI 分析你的需求，然后按需完成三件事：

1. 🔧 **动态函数** `.py` — 复用已有的，缺的委托 `bigbear-dynamic-function-generator` 生成
2. 📋 **自动化用例** `.yaml` — 优先从手工用例 MD 转换，只在没匹配时新建
3. 🧩 **编排文件** `.yaml` — 串联函数和用例的 `case_flow`（本 Skill 核心产物）

### 三种使用模式

| 模式 | 适用场景 | 引导程度 | 触发方式 |
|------|---------|---------|---------|
| **🚀 智能生成** | 你说清楚了业务、测试类型、测试点 | 0 个问题 | 信息足够时自动进入 |
| **🧭 向导模式** | 你只说了大概方向，还没想细 | 3-6 个问题 | 信息不足时自动进入 |
| **🔧 自由组合** | 你只要做某一步（比如只生成函数、只生成编排） | 0-1 个问题 | 你明确说"只做 XX" |

### 启发式判断规则

AI 收到请求后提取三个关键信号：

1. **业务场景是否明确** — 例："用户登录"、"小说搜索"
2. **测试类型是否明确** — 例："接口测试"、"Web UI 测试"
3. **测试点是否明确** — 例："正常登录、密码错误、Token 过期"

判定：

- ✅ **三个都给齐** → 智能生成模式，直接出方案
- ⚠️ **只缺 1-2 个** → 快速补全，只问缺失的项
- ❌ **三个都缺 / 描述模糊** → 向导模式，逐条追问
- 🔧 **用户说"只生成 XX"** → 自由组合模式

### 随时退出

在引导的任何一步，你都可以说：

- **"跳过"** — 立即按已有信息生成
- **"先这样"** — 用当前信息先生成，回头再改
- **"我自己来"** — 退出引导，你自己操作

---

## 🧭 向导模式：提问清单

用户描述模糊时，AI **一次只问一条问题**，不轰炸。

| 序号 | 问题 | 选项/示例 |
|------|------|-----------|
| 1 | 你想测什么业务？ | 用户自由描述，如"用户注册登录全流程" |
| 2 | 涉及哪些测试类型？ | `接口` / `Web UI`/ `APP UI` / `性能` / `多类型混合` |
| 3 | 针对哪个接口/页面？ | AI 根据第2步的类型精准追问。接口则问"具体接口？"；UI 则问"哪个页面/URL？" |
| 4 | 用哪个环境？ | 列出已有环境（从 `AI-环境变量/` ls 目录名）+ 可选"新建" |
| 5 | 测试数据从哪来？ | `复用已有动态函数` / `新建DB查询` / `新建API调用` / `固定写死` / `从环境变量取` |
| 6 | 有哪些关键测试场景？ | AI 给出建议 + 用户补充。如"正常登录、密码错误、账号锁定、Token 过期" |

---

## 🔧 自由组合模式：支持的操作

| 用户说 | AI 行为 |
|--------|---------|
| "帮我看看有哪些可复用的登录相关用例" | 精准扫描 → 展示结果 |
| "我只想生成编排 YAML，函数和用例都有了" | 跳过函数/用例 → 直接生成编排 |
| "帮我补充一个密码错误的自动化用例" | 读源材料 → 只生成这一个用例 YAML |
| "加一个 task 到已有编排" | 读取编排 → 追加 task → 更新编排 YAML |
| "执行这个编排" | 调 `bigbear-test-runner` |

---

## 📊 两层体系：源材料 vs 自动化产物

> ⚠️ **关键概念**：手工用例和自动化用例是两种完全不同的东西！

### 源材料层（只读，绝不修改）

AI 从这里理解业务、提取测试场景。

```
{工作空间}/
├── AI-WEB功能测试/
│   ├── AI-测试点分析/{模块}/{功能名}.md      ← Web 测试点分析
│   └── AI-测试用例/{模块}/*.md               ← Web 手工用例（Markdown，人读）
│
├── AI-接口API测试/
│   ├── AI-接口管理/{批次}/*.md               ← 接口文档（含请求/响应详情）
│   ├── AI-测试用例/{批次}/*.md               ← 接口手工用例（Markdown，人读）
│   └── AI-信息采集/{批次}/*.json             ← 录制数据（JSON）
│
├── AI-知识库/
│   ├── WEB自动化执行知识库/                   ← Web 自动化规则
│   ├── 接口用例相关知识库/                    ← 接口测试规则
│   └── OA系统操作基本规则说明/                ← 业务规则
│
└── AI-环境变量/
    └── {环境名}/
        ├── env_var.yaml                      ← 环境变量
        └── meta.yaml                         ← 环境元信息
```

### 自动化产物层（本 Skill 写入）

格式固定，可被 `bigbear-test-runner` 直接消费执行。

```
{工作空间}/
├── AI-动态函数管理/
│   └── {类型}/{function_code}.py             ← 动态函数（Python）
│                                              ← 第一行含 # AIQE_DYNAMIC_FUNCTION_META {...}
│
├── AI-自动化测试用例/
│   ├── api/{module}/{uuid}.yaml              ← 接口自动化用例（runner 已支持）
│   ├── web/{module}/{uuid}.yaml              ← WEB UI 自动化用例（runner 已支持）
│   ├── app/{module}/{uuid}.yaml              ← APP UI 自动化用例（runner 已支持）
│   ├── pc/{module}/{uuid}.yaml               ← PC 客户端自动化用例（runner 待扩展）
│   ├── mini-program/{module}/{uuid}.yaml     ← 小程序自动化用例（runner 待扩展）
│   └── performance/{module}/{uuid}.yaml      ← 性能测试用例（runner 待扩展）
│
└── AI-自动化测试编排/
    └── {uuid}.yaml                           ← 编排文件（核心产物）
                                              ← 含 case_flows → tasks 完整链路
```

### 手工用例 vs 自动化用例

| | 手工测试用例 | 自动化测试用例 |
|------|-------------|----------------|
| **格式** | Markdown | YAML |
| **内容** | 测试步骤 + 预期结果（自然语言） | input_datas + output_datas + source_id（结构化） |
| **存放** | `AI-WEB功能测试/AI-测试用例/`、`AI-接口API测试/AI-测试用例/` | `AI-自动化测试用例/{api/web/app/pc/mini-program/performance}/` |
| **读者** | 人 | 机器（bigbear-test-runner） |
| **本 Skill 角色** | **源材料，只读** | **产物，写入** |

---

## 🔄 核心流程（6 步）

### Step 1：意图识别 + 模式判断

- 提取：业务场景 / 测试类型 / 测试点
- 判断：智能生成 / 向导 / 自由组合
- 缺信息 → 逐条追问（每次一条）

### Step 2：精读源材料（只读不写）

按测试类型精准定位，只读相关目录，不遍历整个工程。

| 测试类型 | 优先精读哪些源 |
|----------|---------------|
| 接口 | `AI-接口API测试/AI-接口管理/`（接口文档）→ `AI-接口API测试/AI-测试用例/`（手工用例）→ `AI-知识库/接口用例相关知识库/` |
| Web UI | `AI-WEB功能测试/AI-测试点分析/` → `AI-WEB功能测试/AI-测试用例/` → `AI-知识库/WEB自动化执行知识库/` |
| 多类型混合 | 按上述规则分别读取 |
| 性能 | `AI-性能测试/` + 接口文档 |

精读策略：
- 用户说具体功能（如"登录"）→ AI 在对应目录下 `Grep` 搜索"login/登录"关键字
- 用户给具体文档路径 → 用 `Read` 直接读该文件
- 源材料**只读不写、不做任何修改**

### Step 3：精准扫描已有自动化资源

**核心原则：绝不主动全量遍历。** 只在用户指明测试类型和关键字后才扫描，限定在对应目录。

```
用户输入："用户登录的 Web UI 测试"

AI 提取：类型=Web UI、关键字=登录/login

扫描范围（用 Grep）：

  源材料（找可转换的手工用例）：
  ✅ AI-WEB功能测试/测试用例/**/*.md        → Grep "登录/login"
  ✅ AI-WEB功能测试/测试点分析/**/*.md       → Grep "登录/login"

  已有自动化资源（找可复用的）：
  ✅ AI-自动化测试用例/web/**/*.yaml          → Grep name 匹配"登录"
  ✅ AI-动态函数管理/**/*.py                 → Grep 元数据行，匹配"登录/用户"
  ✅ AI-自动化测试编排/*.yaml                 → Grep name

  不做：
  ❌ AI-自动化测试用例/api/                  → 不扫（类型不匹配）
  ❌ AI-自动化测试用例/performance/          → 不扫
```

扫描结果以清晰格式呈现，标注哪些可**复用**、AI **建议新建**什么。

### Step 4：生成预览（关键确认点）

扫描完成后，输出**完整链路预览**，明确标注 📄转换、♻️复用 和 🔨新建：

```
📋 编排预览：「用户登录完整流程」

┌──────────────────────────────────────────────────────┐
│  case_flow: 用户登录完整流程                           │
│  tags: [冒烟, 主流程]                                  │
│                                                      │
│  [Task 1] 获取用户登录信息                            │
│    类型: dynamic-function                             │
│    来源: ♻️ 复用 → get_login_info                      │
│    输出: username, password                           │
│                                                      │
│  [Task 2] 正常登录                                   │
│    类型: web                                          │
│    来源: 📄 转换 → 登录表单-正常登录                    │
│    手工用例: AI-WEB功能测试/测试用例/首页/会员登录_*.md │
│    输入: username, password (← Task 1)                │
│                                                      │
│  [Task 3] 密码错误登录                                │
│    类型: web                                          │
│    来源: 📄 转换 → 登录表单-密码错误                    │
│    输入: username (← Task 1), wrong_password           │
│                                                      │
│  [Task 4] Token 过期访问 ⚠️ 需新建                    │
│    类型: api                                          │
│    来源: 🔨 新建（手工用例无对应条目，需确认）          │
│    输入: expired_token                                │
│                                                      │
│  📄 将转换: 2 个手工用例 → 自动化用例 YAML            │
│  🔨 将新建: 1 个纯自动化用例（待确认）                 │
│  ♻️ 将复用: 1 个动态函数                              │
│  🧩 将生成: 1 个编排文件                              │
└──────────────────────────────────────────────────────┘

是否确认生成？（回复"确认"或"调整 XXX"）
```

**必须等待用户确认后才写入文件！**

### Step 5：依次写入文件

确认后，严格按依赖顺序执行：

```
① 新建动态函数（如果有）
   → 调用 Skill("bigbear-dynamic-function-generator")
   → 拿到 function_code 后继续

② 自动化用例 YAML（转换优先，新建兜底）
   → 有手工用例 → 转换格式写入 YAML，source_id 沿用原 UUID
   → 无手工用例 → ⚠️ 确认后新建（告知用户不一致风险）
   → 写入: AI-自动化测试用例/{类型}/{module}/{uuid}.yaml

   > **📁 {类型} 取值集合**：`api` / `web` / `app` / `pc` / `mini-program` / `performance`
   >
   > ⚠️ **runner 兼容性说明**：当前 `bigbear-test-runner` 仅实现 `api` / `web` / `dynamic-function` 三种 type 的执行路径。`app` / `pc` / `mini-program` / `performance` 是**约定先行的命名**，实际执行需要在 runner 代码（`plan_loader.py` 的 `CaseType` 枚举 + `prompt_builder.py` 路由）中扩展能力。在 runner 端未完成扩展前，新类型的编排 task 加载时会抛 `PlanLoadError: task.type 不支持`。本 Skill 当前只为这些新类型生成 YAML 用例文件，不保证编排能直接被 runner 执行。

③ 编排文件 .yaml（核心产物）
   → AI-自动化测试编排/{uuid}.yaml
   → 含 name / priority / tags / case_flows → tasks
   → 每个 task 引用前两步产物的 source_id

④ YAML 格式验证（⚠️ 必须执行，不可跳过）
   → 所有 .yaml 文件写入后，用 Python yaml.safe_load() 逐文件验证
   → 验证通过才继续，失败则定位修复后重新验证
   → 特别注意：含 {{ }} 占位符的步骤值必须加单引号包裹，否则 YAML 会把 { 解析为 flow mapping
   → 验证命令（从工作空间根目录执行）：
     python -c "
     import yaml
     files = ['待验证文件1.yaml', '待验证文件2.yaml', ...]
     for f in files:
         with open(f, 'r', encoding='utf-8') as fh:
             yaml.safe_load(fh)
         print(f'✅ {f}')
     print('全部 YAML 加载成功')
     "

⑤ 汇总报告
   → 列出所有转换/复用/新建的文件路径
   → 明确标注：转换了几个手工用例、新建了几个纯自动化用例
   → 附带 YAML 验证结果（全部通过 / 哪些失败已修复）
   → 提示："要执行这个 flow 吗？"
```

### Step 6：可选执行

询问用户是否立即执行。如果是，调用：

```bash
bigbear-test-runner run <root_dir> <plan_id>
```

---

## 🔧 产物一：动态函数 — 委托已有 Skill

**策略**：需要新建动态函数时，**不自己写代码**，而是调用已有的 `bigbear-dynamic-function-generator` Skill。

### 调用方式

使用 `Skill` 工具调用，将用户的需求传达给它：

```
Skill("bigbear-dynamic-function-generator")
```

bigbear-dynamic-function-generator 会按自己的交互流程（跳过/快速补全/场景向导）生成符合 AIQE 规范的 `.py` 文件。

### 本 Skill 的角色

- 分析用户场景，判断需要哪些动态函数（如"获取登录信息"、"查询用户 Token"）
- 先扫描 `AI-动态函数管理/` 下已有函数，能复用的直接引用 `function_code`
- 确认需要新建时，调用 bigbear-dynamic-function-generator 生成
- 拿到生成后的 `function_code`，用于后续编排的 `source_id` 引用

---

## 📋 产物二：自动化用例 — 手工用例优先转换

### ⭐ 核心策略：转换优先，新建仅兜底

```
手工用例 MD（源材料）
       │
       ▼
  检查是否有匹配的手工用例
       │
   ┌───┴───┐
   │ 有     │ 无
   ▼       ▼
 转换！   ⚠️ 跟用户确认后再新建
   │       │
   │       ▼
   │   新建自动化用例 YAML
   │   （且告知用户：手工侧缺少此用例，
   │    建议同步补充手工用例）
   │
   ▼
  自动化用例 YAML
```

### 转换规则

从手工用例 MD 的每个 `## <测试标题>` 段落中，提取信息映射为 YAML：

| 手工用例 MD 字段 | → | 自动化用例 YAML 字段 |
|---|---|---|
| `## <测试标题>` | → | `name` |
| `type`（接口/Web/性能） | → | `type` |
| `用例编号` | → | `source_id`（直接用已有 UUID） |
| 测试步骤中的 `{{占位符}}` | → | `input_datas[].name`（参数名）+ `input_datas[].value`（默认测试值） |
| 预期结果中的关键断言 | → | `output_datas[].value`（输出变量名） |

### 转换示例

**手工用例 MD**：
```markdown
## 登录表单-正常登录
### 用例信息
| 用例编号 | 244d5b6d8bc64535b9ef1ec72974e88c |
| 用例名称 | 登录表单-正常登录 |
### 测试步骤
1. "手机号码"输入框 输入 {{ 已注册手机号 }}
2. "密码"密码框 输入 {{ 正确登录密码 }}
3. 点击"登录"按钮
### 预期结果
- 登录接口返回成功
- 浏览器跳转至首页
- 顶部导航显示已登录态用户名
```

**转换为自动化用例 YAML**（以项目实际格式为准）：
```yaml
case_id: "244d5b6d8bc64535b9ef1ec72974e88c"
case_type: web
case_priority: P0
case_title: 登录表单-正常登录
case_precondition: 未登录态，登录表单区可见，已注册且账号状态正常的用户
case_content:
  steps:
  - 打开网址 http://novel.hctestedu.com/user/login.html
  # ⚠️ 含 {{ }} 占位符的步骤必须加单引号包裹，否则 YAML 将 { 解析为 flow mapping 导致加载失败
  - '"手机号码"输入框 输入 "{{已注册手机号}}"'
  - '"密码"密码框 输入 "{{正确登录密码}}"'
  - 点击"登录"按钮
  expected:
  - 登录接口返回成功
  - 浏览器跳转至首页
  - 顶部导航显示已登录态用户名
updated_at: '2026-07-10 15:36:00'
```

> ⚠️ **YAML 花括号陷阱**：`{{ }}` 中的 `{` 会被 YAML 解析为 flow mapping 起始符。含 `{{变量}}` 占位符的步骤值，**必须加单引号包裹**（如 `- '"输入 {{变量}}"'`）。否则 `python yaml.safe_load()` 会报 `expected <block end>, but found '<scalar>'`。

### 何时需要新建（须用户确认）

只有以下情况才**新建**自动化用例 YAML，且**必须先和用户确认**：

1. 手工用例 MD 中不存在对应的测试场景
2. 手工用例存在但内容不足以提取自动化参数

**确认话术**：
> "⚠️「密码错误登录」这个测试场景在手工用例中没有找到对应的条目。我需要新建一个纯自动化用例来覆盖它。但这会导致自动化用例和手工用例不一致。要继续吗？（建议同步在手工用例中也补上这个场景）"

### 理想状态目标

```
手工测试用例                         自动化测试用例
    │                                    │
    ├─ 登录-正常登录 ────────转换──────→ 登录-正常登录.yaml
    ├─ 登录-空手机号 ────────转换──────→ 登录-空手机号.yaml
    ├─ 登录-密码错误 ────────转换──────→ 登录-密码错误.yaml
    └─ 登录-Token过期 ──────转换──────→ 登录-Token过期.yaml
                                            │
                                    多个自动化用例组合
                                            │
                                            ▼
                                    case_flow: 用户登录完整流程
```

> 多条手工测试用例转换后，组合成一个自动化 `case_flow`，这才是最理想的状态。如果出现大量需要新建自动化用例的情况，说明手工测试用例的生成规则可能存在问题，应当优先完善手工侧。

---

## 🧩 产物三：编排文件生成规范

### YAML 结构

```yaml
name: "流程名称"
priority: "low | medium | high"
tags:
  - "标签1"
  - "标签2"
case_flows:
  - id: "uuid"
    title: "流程标题"
    priority: "medium"
    tags: ["冒烟", "主流程"]
    tasks:
      - title: "任务名称"
        type: "dynamic-function | api | web | app | pc | mini-program | performance"
        source_id: "function_code 或 case_uuid"
        input_datas:
          - name: "参数显示名"
            value: "参数值"     # ⚠️ 引用变量必须用 {{变量名}}（详见下方规范）
        output_datas:
          - name: "输出显示名"   # ⚠️ 下游引用的是这里的 name，不是 value
            value: "输出字段名"
```

### 🔁 变量引用规范（Jinja2 语法 — ⭐核心规则）

> ⛔ **铁律**：编排文件 `input_datas[].value` 凡是**需要引用变量**的（环境变量、上游 task 输出），**必须**用 `{{变量名}}` Jinja2 语法。**严禁**写死成字面量。runner 阶段（`bigbear-test-runner`）会用 `jinja2.Template(...).render(context)` 渲染，未用占位符的值就直接当字面量用，写死就再也换不了环境/换不了数据源。

> 📚 渲染机制实现参考：`bigbear-test-runner/src/bigbear_test_runner/executors/base.py` 的 `render_inputs()`（约 155-194 行）+ `context.py` 的 `ContextManager` + `batch.py:extract_flows()`（约 305-315 行，把 `env_var.yaml` 初始化进 `context.json`）。

#### 1. `{{变量名}}` 能引用哪些数据？

渲染上下文来自 flow 目录下的 `context.json`，其内容 = **环境变量初始值** + **之前所有 task 累积的 output_datas**：

| 数据来源 | 在 context.json 里的 key | 引用方式 |
|----------|------------------------|----------|
| **环境变量**（`AI-环境变量/{env}/env_var.yaml` 的每个 key） | 顶级 key，如 `api_project_url`、`web_project_url`、`TEST_PHONE_NUMBER` | `{{api_project_url}}`、`{{TEST_PHONE_NUMBER}}` |
| **上游 dynamic-function 的输出** | 上游 task 的 `output_datas[].name`（**中文显示名**） | `{{手机号}}`、`{{登录密码}}` |
| **上游 api/web 的输出**（AI 提取的字段） | 上游 task 的 `output_datas[].name`（**中文显示名**） | `{{用户ID}}`、`{{Token}}` |

#### 2. ⭐ 引用键名 = `output_datas[].name`，**不是** `.value`

runner 的实际写入规则（见 `bigbear-test-runner/src/bigbear_test_runner/executors/base.py:render_inputs` + `dynamic_function.py:90-95`）：

- dynamic-function：`ctx.update(output_values)` 的 key = 函数返回值 dict 里与 `output_datas[].value` 同名的字段对应的 **output_datas[].name**。
- api：AI 提取后 `ctx.update({o.name: o.value for o in outputs if o.value is not None})` —— **直接用 name 当 key**。

**举例**（来自工作区真实编排 `8b6030cb-cdc1-47cf-b9dd-96e9726dfddc.yaml`）：

```yaml
# Task 1: dynamic-function 输出 name=value 两列
- title: 获取登录账号信息
  type: dynamic-function
  source_id: get_login_credentials
  output_datas:
    - name: 手机号        # ← 这个 name 才是 context.json 里的 key
      value: phone_number # ← 函数返回值里叫 phone_number 的字段
    - name: 登录密码
      value: password

# Task 2: web 用例输入 value 引用 name（不是 value）
- title: 正常登录
  type: web
  source_id: 244d5b6d8bc64535b9ef1ec72974e88c
  input_datas:
    - name: 手机号
      value: '{{手机号}}'        # ✅ 引用 Task 1 的 name
    - name: 登录密码
      value: '{{登录密码}}'      # ✅ 引用 Task 1 的 name
```

**反例（必须避免）**：

```yaml
# ❌ 错误：直接写死字面量，跨环境不可移植
input_datas:
  - name: 手机号
    value: '13800138001'

# ❌ 错误：环境变量已存在但没用 {{}} 引用
input_datas:
  - name: URL
    value: http://novel.hctestedu.com     # 应改为 '{{api_project_url}}'

# ❌ 错误：引用错键名（用 value 而非 name）
input_datas:
  - name: 手机号
    value: '{{phone_number}}'             # 应改为 '{{手机号}}'（因为 name=手机号）
```

#### 3. `{{变量名}}` 用在哪些字段？

| 字段 | 支持 jinja2 | 说明 |
|------|------------|------|
| 编排 task `input_datas[].value` | ✅ **必须** | runner 渲染后注入函数/用例入参 |
| 自动化用例 `case_content.request.url` | ✅ | api/web 用例 body/url 里的 `{{}}` 也会被 runner 二次渲染 |
| 自动化用例 `case_content.request.urlParams[].value` | ✅ | 同上 |
| 自动化用例 `case_content.steps[].*`（web） | ✅ | web 执行器渲染 |
| 自动化用例 `case_precondition` | ✅ | 自然语言里引用变量，便于阅读 |
| 环境变量文件 `env_var.yaml` 的 key | ❌ | key 是固定的，不用 `{{}}` 包裹 |
| 编排 task `output_datas[].name` | ❌ | name 是键名定义，不是值 |

> 渲染优先级（runner 内部）：环境变量 → 渲染 task `input_datas[].value` → 合并进 local_context → 渲染 `case_content.request` → 发起请求 / 驱动浏览器。

#### 4. YAML 写入时的引号规则（花括号陷阱）

含 `{{变量名}}` 的字符串值，**必须用单引号包裹**，否则 YAML 会把 `{` 解析为 flow mapping 起始符，导致 `yaml.safe_load()` 报错 `expected <block end>, but found '<scalar>'`：

```yaml
input_datas:
  - name: URL
    value: '{{api_project_url}}'    # ✅ 单引号
  - name: 小说名称
    value: '{{小说名称}}'            # ✅ 单引号
  - name: 备注
    value: 用户名={{手机号}}&密码={{登录密码}}   # ✅ 整串加单引号
```

> 💡 即便是纯中文/纯变量、不会与 YAML 语法冲突的简单值，也**统一加单引号**，省去排查时间。

#### 5. 引用前的快速核对清单

写完编排准备落盘前，自检：

- [ ] 凡是**会因环境/账号/数据源变化**的值，都用了 `{{变量名}}`？（账号、密码、URL、token、user_id、手机号、邮箱…）
- [ ] 引用的 `{{变量名}}` 在环境变量文件或上游 task 的 `output_datas[].name` 里**真实存在**？（不一致 = 渲染后是空串或报错）
- [ ] 引用的键名是 **`output_datas[].name`**，不是 `value`？
- [ ] 含 `{{}}` 的 value 字符串**加了单引号**？
- [ ] 写完后跑过 `python -c "import yaml; yaml.safe_load(open('xxx.yaml'))"` 验证？

### 数据流转规则

编排的核心价值是**串联 tasks 之间的数据流转**：

- 上游 task 的 `output_datas[].name` → **就是 context.json 里新增的 key**，供下游 `{{变量名}}` 引用
- 下游 task 的 `input_datas[].value` → 必须写成 `{{上游 output_datas 的 name}}`（参见上方"🔁 变量引用规范"）
- dynamic-function 类型 task 的输出由函数返回值决定（返回值 dict 的 key 与 `output_datas[].value` 对应）
- api/web 类型 task 的输出由用例的 `output_datas[].value`（JSONPath 或自然语言）经 AI 提取后写入 context.json

> 📖 已有编排参考：
> - [登录到首页再到个人中心](../../AI-自动化测试编排/8b6030cb-cdc1-47cf-b9dd-96e9726dfddc.yaml)（✅ 正确引用示例）
> - [公开课演示流程](D:/work/course/test/ai_test/AIQE/apps/bigbear-test-runner/examples/AI-自动化测试编排/30e12d4e1be5438ea155139403729699.yaml)（✅ 正确引用示例）

---

## 🔄 回退与修改

生成后如果用户不满意，支持以下操作：

| 用户说 | AI 行为 |
|--------|---------|
| "换个函数" | 重新扫描候选函数，替换编排中的 source_id |
| "加一个 task" | 只补充新 task 到已有编排 YAML |
| "改执行顺序" | 调整编排中 tasks 顺序 |
| "删掉 XX 场景" | 从编排移除对应 task，不删除用例文件 |
| "改函数入参" | 更新 .py 文件的 params 元数据 + 同步编排 input_datas |
| "改用例预期" | 更新用例 YAML 的 output_datas |
| "直接执行这个编排" | 调用 bigbear-test-runner |

---

## 🤝 与其他 Skill 的关系

```
┌──────────────────────────────────────────────────────┐
│                 bigbear-test-flow-builder               │
│                    （本 Skill）                        │
│                                                      │
│   核心职责：编排 + 用例转换 + 流程串联                  │
│   ✅ 手工用例 → 自动化用例 YAML（格式转换）            │
│   ✅ 生成编排文件 .yaml（串联 case_flow）              │
│                                                      │
│   引用外部 Skill 时：                                  │
│   ├─ 需新建函数 → 调 Skill bigbear-dynamic-function-gen │
│   ├─ 执行计划 → 调 bigbear-test-runner                  │
│   └─ 浏览器操作 → 调 bigbear-web-cli                    │
└──────────────────────────────────────────────────────┘
```

职责边界：

| Skill | 职责 | 与本 Skill 关系 |
|-------|------|----------------|
| bigbear-web-case-generator | 生成"手工测试用例 MD" | 其产物是**本 Skill 转换的源材料** |
| bigbear-api-case-generator | 生成"手工测试用例 MD" | 其产物是**本 Skill 转换的源材料** |
| bigbear-dynamic-function-generator | 交互式生成单个动态函数 | **需要新建函数时调用它**，不自己写 |
| bigbear-test-runner | 执行测试计划 | 本 Skill 最后一步可选调用 |
| bigbear-web-cli | 浏览器自动化操控 | 需要浏览页面时调用 |

---

## ⚠️ 关键注意事项

| # | 注意事项 |
|---|----------|
| 1 | **自动化用例优先从手工用例转换**。手工用例 MD 是自动化用例的主要来源，转换其格式为 YAML。只有在手工用例不存在对应场景时，才和用户确认后新建纯自动化用例 |
| 2 | **手工用例和自动化用例理想状态下应保持一致**。如果大量场景需要新建自动化用例，说明手工用例生成规则可能有问题，应优先完善手工侧 |
| 3 | **动态函数委托已有 Skill**。需要新建函数时，调用 `bigbear-dynamic-function-generator`，不自己写代码 |
| 4 | **源材料只读不写**。`AI-WEB功能测试/`、`AI-接口API测试/`、`AI-知识库/` 下的文件绝不修改 |
| 5 | **绝不主动全量扫描**。只在用户明确测试类型和关键字后，在对应目录下精准 Grep |
| 6 | **一次只问一条问题**。信息不全时逐条追问，不轰炸 |
| 7 | **先预览再写入**。生成完整链路预览后必须等用户确认 |
| 8 | **写入顺序严格**。先函数（委托） → 再用例（转换/新建） → 最后编排（串联引用） |
| 9 | **编排 YAML 是核心产物**。它串联所有函数、用例、数据流转 |
| 10 | **复用优先**。已有可用的函数/自动化用例，引用而非重建 |
| 11 | **函数和用例支持独立生成**。用户可以只要某一步，不一定要走完整流程 |
| 12 | **YAML 写入后必须 Python 验证**。每个 .yaml 文件写入后，必须用 `python -c "import yaml; yaml.safe_load(open(...))"` 验证能正常加载。特别注意：`{{ }}` 花括号会被 YAML 解析为 flow mapping 语法，含占位符的步骤值必须加单引号包裹（如 `- '"输入 {{变量}}"'`），否则 yaml.safe_load 报错 |
| 13 | **⛔ input_datas / case_content 引用变量必须用 `{{变量名}}` Jinja2 语法**。凡是可能因环境/账号/数据源变化的值（URL、账号、密码、token、user_id、手机号…），都**禁止**写死成字面量。runner 渲染上下文 = `context.json` = 环境变量初始值 + 上游 task `output_datas[].name` 累积。**引用键名是 `output_datas[].name`（中文显示名）**，不是 `value`。详见"🧩 产物三 → 🔁 变量引用规范"章节 |
