---
name: bigbear-test-plan-generator
description: 对话式引导生成 AIQE 自动化测试计划（plan）。触发场景：用户说"生成测试计划"、"新建测试计划"、"做一个 plan"、"编排一个测试计划"、"把这些 flow 串成一个计划" 等。核心职责：扫描当前项目的 AI-自动化测试编排 目录，列出 ID+name 让用户挑选（或用户直接指定 ID/title），按用户选择的编排组合生成 plan-web-{时间戳}-{编排name} 计划目录及 meta.yaml，默认落盘到 AI-自动化测试计划，可一键调 bigbear-test-runner 执行。
enabled: true
---

重点：请使用中文沟通！！

# bigbear-test-plan-generator — 测试计划生成器

对话式引导生成 AIQE 测试计划 `meta.yaml`：扫描已有编排 → 选 flow → 选环境 → 选策略 → 落盘 → 可选执行。

---

## 🎯 我该怎么用这个技能？

### 一句话理解

你描述想跑哪些编排（或直接给 ID/title），AI 把它们**组合成一个测试计划**（plan），写到 `AI-自动化测试计划/plan-web-{时间戳}-{编排name}/meta.yaml`，然后问你"要不要立刻执行"。

### 典型使用场景

| 你说 | AI 行为 |
|------|---------|
| "生成测试计划" | 列出所有编排让你挑 |
| "把登录相关的编排做一个 plan" | 过滤名称包含"登录"的编排让你挑 |
| "用 c5e7f8a9、d6f8a9b0、4e2c4a40 这三个 flow 做个 plan" | 直接按 ID 选用，无需再次选择 |
| "做一个登录接口的 plan" | 过滤名称含"登录"+"接口"，并优先把 plan 类型推断为 `api` |
| "把 e7f8a9b0 这个编排做一个 plan" | 直接按 ID 选用，类型默认按编排的 task 类型推断 |

### 与其他 Skill 的关系

```
bigbear-test-plan-generator  ← 本 Skill（组合 plan）
        │
        │ 读 AI-自动化测试编排/*.yaml      (bigbear-test-flow-builder 的产物)
        │ 读 AI-环境变量/{env}/meta.yaml   (环境元信息)
        │ 读 AI-环境变量/{env}/env_var.yaml
        │ 写 AI-自动化测试计划/plan-web-{时间戳}-{编排name}/meta.yaml
        │
        └─→ 可选调用 bigbear-test-runner 执行 plan
```

| Skill | 职责 | 与本 Skill 关系 |
|-------|------|----------------|
| bigbear-test-flow-builder | 生成单个编排文件 | 本 Skill 的**输入生产者** |
| bigbear-test-runner | 执行测试计划 | 本 Skill 的**下游执行者**（可选） |
| 本 Skill | 把若干编排**组合**成一个可执行 plan | — |

---

## 📁 工作空间目录约定

```
{工作空间}/
├── AI-自动化测试编排/                 ← 扫描编排（只读）
│   └── {uuid 或 uuid-with-dashes}.yaml
│
├── AI-环境变量/                       ← 选择 environmentKey（只读）
│   └── {env_name}/
│       ├── meta.yaml
│       └── env_var.yaml
│
├── AI-自动化测试计划/                  ← 落盘目标（写入）
│   └── plan-web-{时间戳}-{编排name}/meta.yaml
│
└── AI-自动化测试执行/                  ← 执行后产生（runner 写入）
    └── 执行记录-YYYYMMDDHHMMSS/
```

> 🔍 **当前工作空间根** = 用户当前操作的目录，默认即 `{cwd}`。如用户切换项目，按用户当前所在项目目录处理。

---

## 🔄 核心流程（6 步）

### Step 1：意图识别 + 收集候选编排

#### 1.1 用户输入分类

| 用户说 | 处理方式 |
|--------|---------|
| 没说具体编排 / 只说"生成测试计划" | **列出全部编排**让用户选 |
| 说了标题关键字（如"登录接口"） | 先**过滤**名称匹配项，命中 1 个直接选用，命中多个再列 |
| 说了具体 ID（含横线/不含横线都可以） | **直接选用**，无需再次确认 |
| 说了多个 ID / 标题 | 全部**直接选用**为 flow |

#### 1.2 扫描编排目录

```
{工作空间}/AI-自动化测试编排/*.yaml
```

**读取方式**：用 `Glob` 列出所有 `.yaml`，逐个 `Read` 提取 `name` 字段（位于第 1 行）。

每个编排的关键信息：

| 字段 | 提取位置 | 示例 |
|------|---------|------|
| `sourceFlowId` | 文件名去后缀，**保留原始格式**（含横线/不含横线都保留） | `c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a` 或 `4e2c4a40-4ee3-45ea-bac4-aede9a44c90f` |
| `sourceFlowFile` | 文件名 | `c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml` |
| `name` | 第 1 行 `name:` 字段 | 登录接口用例编排 |
| `priority` | 第 2 行 | high |
| `tags` | 第 3+ 行数组 | 接口测试、登录、P0-P3 |

> ⚠️ **sourceFlowId 保留原始格式**：项目里既有 `c5e7f8a90b1c2d3e4f5a6b7c8d9e0f1a`（32 位无横线）也有 `4e2c4a40-4ee3-45ea-bac4-aede9a44c90f`（标准 UUID）。两种都合法，写 plan 时按文件名原样抄，不要自作主张加/去横线。

#### 1.3 展示给用户（让选 flow）

用 `AskUserQuestion` 让用户多选编排，header 用"选编排"，问题示例：

> **请选择要纳入测试计划的编排**（可多选）
>
> 选项（最多展示 4 个，超过则展示前 4 个 + "其他"自动收集）：
> 1. c5e7f8a9…0f1a — 登录接口用例编排
> 2. d6f8a9b0…1a2b — 登录→更新用户信息
> 3. e7f8a9b0…2a3b — 登录成功 - 修改用户信息
> 4. 4e2c4a40…c90f — 用户注册+登录完整流程

**多选模式（multiSelect: true）**：用户可以勾选 1 到 N 个。

#### 1.4 标题过滤示例

用户说"做一个登录接口的 plan" → AI 扫描后用标题过滤：
- "登录接口用例编排" ✅ 命中
- "登录→更新用户信息" ✅ 命中
- "登录成功 - 修改用户信息" ✅ 命中
- "用户注册+登录完整流程" ✅ 命中（包含"登录"）
- 如果只命中 1 个，**直接选用**并告知用户；
- 命中多个 → 列出来让用户确认全选/部分选。

---

### Step 2：决定 plan 类型（type，仅供内部参考）

> ⚠️ **本步骤仅用于内部记录 plan 类型，不影响目录命名**（目录命名见 Step 4，已硬编码为 `web`）。这里输出的 type 仍可作为 plan 性质的快速参考。

`type` 合法取值：

| 类型 | 含义 | 推断规则 |
|------|------|---------|
| `api` | 全是接口类 task | 所有 flow 的 task 全部 `type: api` |
| `app` | 全是移动端 UI（android/ios/harmonyos/miniapp） | 所有 task 都是 UI 移动端 |
| `web` | 全是 Web UI（含 pc） | 所有 task 都是 web/pc |
| `mixed` | 跨多种类型 | 不符合上面任一纯类型 |

**推断策略**：

1. 优先**自动推断**：扫描所选编排的所有 task.type，按上表归类。
2. 单一类型 → 用该类型；
3. 跨类型 → 用 `mixed`；
4. 推断结果只在预览阶段展示给用户，**不写入目录名**。

---

### Step 3：收集计划元信息

按顺序处理（**默认值直接采用，不询问**；只有 `priority` / `environmentKey` 必要时才问）：

#### 3.1 plan name（必填，**默认值，不询问**）

**默认值**：所选 flow 的 `name` 字段用 ` + ` 拼接。

| 选中 flow 数 | plan name 取值 | 示例 |
|--------------|--------------|------|
| 1 个 | 直接用该 flow 的 `name` 字段原值 | `登录接口用例编排` |
| 多个 | 用 ` + ` 拼接，**保留原始中文/符号** | `登录接口用例编排 + 登录→更新用户信息` |

> 💡 plan name 与目录名末尾的 `{编排name}` 段完全一致。**直接采用默认值，不发起反问**。如需自定义命名，由用户事后改 `meta.yaml` 的 `name` 字段。

#### 3.2 priority（必填，**默认值，不询问**）

**默认值**：`high`（与所选 flow 的 priority 一致；如有 flow 是 medium/low，则按所选 flow 中最高的）。

**优先级映射**：

| 所选 flow 的 priority | plan 默认 priority |
|---------------------|---------------------|
| 全部 high | `high` |
| 含 high + medium | `high` |
| 全部 medium | `medium` |
| 含 medium + low | `medium` |
| 全部 low | `low` |

> 💡 **直接采用默认值，不发起反问**。

#### 3.3 environmentKey（必填）

从 `{工作空间}/AI-环境变量/` 目录的**子目录名**读取（每个子目录 = 一套环境），用 `Glob` 列出。

**默认选中**当前已有 plan 引用最多的环境（一般是 `读书屋-测试`），或工作空间里**唯一**的环境。

> 💡 优先用 Glob + 简单计数自动选中，**不发起反问**。仅当工作空间存在多个环境目录、且用户引用次数打平时，才询问用户。

#### 3.4 executionStrategy（必填，**默认值，不询问**）

**固定默认值**：`serial`（按 `flows[]` 数组顺序串行执行）

**取值规则**：

| 用户场景 | executionStrategy 取值 |
|---------|------------------------|
| 用户未指定 | `serial`（**默认**） |
| 用户主动说"并行"/"parallel" | `parallel` |

> ⚠️ **直接采用默认值 `serial`，不发起反问**。仅在用户**主动**要求并行时才改为 `parallel`（属"修改现有 plan"的高级能力）。

#### 3.5 tags（可选）

询问用户是否要打标签。如果要，列出**所有所选 flow 的 tags 并集**作为候选（用户多选或自定义）。

**优先级规则**：
- 用户没指定 tags → 不写 `tags` 字段，或填 `[]`；
- 用户指定 → 用所选 flow 的 tags + 用户自定义 tags 的并集（去重）。

> ⚠️ **关键**：`meta.yaml` 的 plan-level `tags` 是可选的；当存在时它描述整个 plan，**不要**覆盖掉每个 flow 自己的 `tags`（flow-level tags 必须保留）。

---

### Step 4：决定保存位置（固定规则，不询问）

**保存位置固定**：`{工作空间}/AI-自动化测试计划/plan-web-{YYYYMMDD-HHMMSS}-{编排name}/meta.yaml`

> ⚠️ 本规则不询问用户、不接受覆盖。如需自定义命名，由用户事后再 `mv` 目录。

**目录命名规则（硬编码）**：

```
plan-web-{YYYYMMDD-HHMMSS}-{编排name}
```

| 段 | 取值 | 说明 |
|----|------|------|
| `plan-` | 固定前缀 | — |
| `web` | 固定 | 通用 Web 平台标识 |
| `YYYYMMDD-HHMMSS` | 当前时间戳 | 例：`20260910-101530` |
| `{编排name}` | 所选 flow 的 name 拼接 | 见下方拼接规则 |

**编排 name 拼接规则**：

| 选中 flow 数 | 编排name 取值 | 示例 |
|--------------|-------------|------|
| 1 个 | 直接用该 flow 的 `name` 字段原值 | `登录接口用例编排` |
| 多个 | 用 ` + ` 拼接，**保留原始中文/符号** | `登录接口用例编排 + 登录→更新用户信息` |

**实例**：

- 单 flow：`plan-web-20260910-101530-登录接口用例编排`
- 多 flow：`plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息`
- 单 flow 名字含特殊符号（→）：`plan-web-20260910-101530-登录→更新用户信息`

> 💡 **id 字段同名**：plan 的 `id` = 目录名（不带 `.yaml`）。例：`plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息`。

---

### Step 5：写入 meta.yaml（核心产物）

#### 5.1 目录结构

```
{工作空间}/AI-自动化测试计划/plan-web-{YYYYMMDD-HHMMSS}-{编排name}/
└── meta.yaml
```

#### 5.2 meta.yaml 模板（**严格按此结构**）

```yaml
id: plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息
name: 登录接口用例编排 + 登录→更新用户信息
priority: high
environmentKey: 读书屋-测试
executionStrategy: serial
flows:
  - sourceFlowId: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a
    sourceFlowFile: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml
    name: 登录接口用例编排
    priority: high
    tags:
      - 接口测试
      - 登录
      - P0-P3
  - sourceFlowId: d6f8a9b0-1c2d-3e4f-5a6b-7c8d9e0f1a2b
    sourceFlowFile: d6f8a9b0-1c2d-3e4f-5a6b-7c8d9e0f1a2b.yaml
    name: 登录→更新用户信息
    priority: high
    tags:
      - 接口测试
      - 主流程
      - Token 串联
created_at: '2026-09-10 10:15:30'
```

#### 5.3 字段详解

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `id` | string | ✅ | 计划唯一 ID，**等于目录名** | `plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息` |
| `name` | string | ✅ | 计划显示名 | `登录接口用例编排 + 登录→更新用户信息` |
| `priority` | string | ✅ | high/medium/low | `high` |
| `environmentKey` | string | ✅ | 环境目录名（`AI-环境变量/{env}`） | `读书屋-测试` |
| `executionStrategy` | string | ✅ | **固定 `serial`**（不询问用户） | `serial` |
| `flows` | array | ✅ | 编排列表，**顺序就是执行顺序** | 见下表 |
| `tags` | array | ❌ | 整个 plan 的标签（plan-level，可选） | `[冒烟, 主流程]` |
| `created_at` | string | ✅ | `YYYY-MM-DD HH:MM:SS`，**必须单引号包裹** | `'2026-09-10 10:15:30'` |

#### 5.4 flows[]. 字段详解

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sourceFlowId` | string | ✅ | 编排 ID（**保留原始格式**，含或不含横线都行） |
| `sourceFlowFile` | string | ✅ | 编排文件名（必须存在于 `AI-自动化测试编排/`） |
| `name` | string | ✅ | 从编排 YAML 第 1 行 `name` 字段照抄 |
| `priority` | string | ✅ | 从编排 YAML 第 2 行照抄 |
| `tags` | array | ✅ | 从编排 YAML `tags` 字段照抄 |

#### 5.5 tags 标签推荐

参考 `bigbear-test-flow-builder` 的常用标签：

| 标签 | 含义 |
|------|------|
| 冒烟 | 冒烟测试，快速验证核心功能 |
| 主流程 | 主要业务流程，核心链路 |
| P0 / P1 / P2 / P3 | 优先级（P0 最高，需立即处理） |
| 接口测试 / Web测试 / App测试 | 测试类型 |
| Token 串联 | 跨 task 数据依赖 |

---

### Step 6：预览 → 用户确认 → 落盘 → 询问执行

#### 6.1 输出预览

写文件**之前**先输出完整预览：

```
📋 测试计划预览

├─ 📂 保存位置
│   {工作空间}/AI-自动化测试计划/plan-web-20260910-101530-登录接口用例编排/
│
├─ 📄 meta.yaml 内容
│   id: plan-web-20260910-101530-登录接口用例编排
│   name: 登录接口用例编排
│   priority: high
│   environmentKey: 读书屋-测试
│   executionStrategy: serial
│   flows:
│     - sourceFlowId: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a
│       sourceFlowFile: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml
│       name: 登录接口用例编排
│       priority: high
│       tags: [接口测试, 登录, P0-P3]
│   created_at: '2026-09-10 10:15:30'
│
└─ 📊 摘要
    - 编排数: 1
    - 环境: 读书屋-测试
    - 执行策略: serial（默认）
    - 优先级: high

是否确认生成？（回复"确认"或"调整 XXX"）
```

**必须等待用户确认后才写入！**

#### 6.2 写入文件

确认后：
1. `mkdir -p` 计划目录
2. `Write` 写入 `meta.yaml`（含 BOM-free UTF-8 + LF 换行）
3. **YAML 验证**（必做）：
   ```bash
   python -c "import yaml; d=yaml.safe_load(open(r'<plan_dir>/meta.yaml', encoding='utf-8')); print('✅ meta.yaml 加载成功:', d.get('id'))"
   ```
4. 验证失败 → 立即报错并定位修复，不允许留坏文件。

#### 6.3 落盘报告

```
✅ 测试计划已生成

📂 {工作空间}/AI-自动化测试计划/plan-web-20260910-101530-登录接口用例编排/
└── meta.yaml  (✅ YAML 验证通过)

📋 摘要
├─ 编排: 1 个
│   └─ c5e7f8a9…0f1a — 登录接口用例编排
├─ 环境: 读书屋-测试
├─ 执行策略: serial
└─ 优先级: high
```

#### 6.4 询问是否执行

用 `AskUserQuestion`：

> **测试计划已生成，是否立即执行？**
>
> 选项：
> 1. ✅ 是，立即执行（推荐）→ 调 `bigbear-test-runner`
> 2. ❌ 否，先不执行

如果用户选"是"，调用 `bigbear-test-runner` Skill（按其规范传参）：

```bash
bigbear-test-runner run {root_dir} {plan_id}
```

其中：
- `{root_dir}` = 工作空间根目录（即 `{工作空间}/`，包含 AI-自动化测试/ 等子目录）
- `{plan_id}` = `plan-web-20260910-101530-登录接口用例编排`

> ⚠️ **执行细节**：用户确认执行后，**改用 `Skill("bigbear-test-runner")`** 让它接管（它会处理 skill 选择、env 加载等）。不要自己拼 CLI 命令。

---

## 🔧 高级能力

### 多 plan 批量生成

用户说"按登录、注册、首页分别生成 plan" → 依次为每个场景生成独立 plan 目录，**不在一个 plan 里塞多个不相关的场景**。

### 追加 / 修改现有 plan

| 用户说 | 行为 |
|--------|------|
| "往 plan-xxx 里加一个 flow" | 读现有 meta.yaml → 在 flows[] 追加 → 重写 |
| "从 plan-xxx 里删掉某个 flow" | 读现有 meta.yaml → 从 flows[] 删除 → 重写 |
| "改 plan-xxx 的环境" | 读现有 meta.yaml → 改 environmentKey → 重写 |
| "改 plan-xxx 的执行策略" | 读现有 meta.yaml → 改 executionStrategy → 重写（注意：本 Skill 默认 serial；用户主动要改才动） |

> 改之前必须先用 `Read` 读现有 meta.yaml，**不要凭记忆改**。

### 复用已有 flow 的 tags

生成 plan 时，**优先沿用 flow 自己的 tags**（从编排 YAML 第 3+ 行读）。除非用户明确说要重写 tags，否则不要覆盖 flow-level tags。

### 类型冲突处理

如果用户同时选了纯 API 的 flow 和 Web UI 的 flow → 自动推断为 `mixed`，并明确告知用户"这两个 flow 类型不同，目录命名为 mixed"。

---

## ⚠️ 关键注意事项

| # | 注意事项 |
|---|----------|
| 1 | **sourceFlowId 保留原始格式**。文件名是 `c5e7f8a9...yaml` 就抄 `c5e7f8a9...`；文件名是 `4e2c4a40-4ee3-45ea-...yaml` 就抄带横线的 UUID。**不要自作主张加/去横线**。 |
| 2 | **顺序敏感**。flows[] 数组顺序 = plan 执行顺序（serial 模式下）。务必按用户给的顺序写入。 |
| 3 | **environmentKey 必须真实存在**。写入前用 `Glob` 验证 `AI-环境变量/{environmentKey}/` 目录存在；不存在则提示用户修正，不要写死。 |
| 4 | **sourceFlowFile 必须真实存在**。写入前用 `Glob` 验证 `AI-自动化测试编排/{sourceFlowFile}` 文件存在；不存在则提示用户修正。 |
| 5 | **created_at 必须单引号包裹**。格式 `YYYY-MM-DD HH:MM:SS`，加单引号避免 YAML 把冒号当 mapping。 |
| 6 | **plan-level tags 可选**。flow-level tags 是必填的（每个 flow 都自带）。plan-level tags 只在用户明确要求时加。 |
| 7 | **执行细节交给 bigbear-test-runner**。用户确认执行后，调 `Skill("bigbear-test-runner")`，不要自己写 CLI 命令。它会处理 skill 选择等细节。 |
| 8 | **一次只问一条问题**。收集信息时分步问，不轰炸。 |
| 9 | **先预览再写入**。meta.yaml 写盘前必须输出预览并获得确认。 |
| 10 | **YAML 验证不可省**。写盘后必须 `yaml.safe_load()` 验证，失败立即修复。 |
| 11 | **落盘位置默认 `AI-自动化测试计划/`**。用户可指定其他位置，但默认不动。 |
| 12 | **id = 目录名**。`meta.yaml` 的 `id` 字段必须等于父目录名（去掉 `.yaml` 后缀的部分），不要给 ID 起别的名。 |

---

## 📚 参考示例

工作空间里已有的 plan，可参考其 `flows[]` 写法：

- `AI-自动化测试计划/plan-api-login-20260827-150820/meta.yaml` — 历史命名示例（**新生成不再使用**，统一按 `plan-web-{ts}-{name}` 走）
- `AI-自动化测试计划/plan-d6f8a9b0-only-20260908161943/meta.yaml` — 历史命名示例（**新生成不再使用**）
- `AI-自动化测试计划/plan-login-updateinfo-20260909-225754/meta.yaml` — 历史命名示例（**新生成不再使用**）
- `AI-自动化测试计划/4e2c4a404ee345eabac4aede9a44c90f/meta.yaml` — 历史命名示例（**新生成不再使用**）

> 📌 **新生成的 plan 统一命名规则**：`plan-web-{YYYYMMDD-HHMMSS}-{编排name}/`，不再使用 slug 或 type 段。
