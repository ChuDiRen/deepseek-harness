# 编排扫描与展示规范

本文档说明**如何扫描 `AI-自动化测试编排/` 目录**并把编排清单展示给用户。

---

## 1. 扫描方式

### 1.1 列出全部编排文件

```python
# 用 Glob 工具
Glob("{工作空间}/AI-自动化测试编排/*.yaml")
```

返回示例：

```
读书屋项目-WEB端/AI-自动化测试编排/c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml
读书屋项目-WEB端/AI-自动化测试编排/d6f8a9b0-1c2d-3e4f-5a6b-7c8d9e0f1a2b.yaml
读书屋项目-WEB端/AI-自动化测试编排/4e2c4a404ee345eabac4aede9a44c90f.yaml
读书屋项目-WEB端/AI-自动化测试编排/e7f8a9b02c3d4e5f6a7b8c9d0e1f2a3b.yaml
```

### 1.2 逐文件 Read 提取元信息

每个编排 YAML 的前 5 行结构：

```yaml
name: 登录接口用例编排       ← 第 1 行：name
priority: high              ← 第 2 行：priority
tags:                       ← 第 3+ 行：tags 数组
  - 接口测试
  - 登录
  - P0-P3
case_flows:
  - id: <uuid>
    title: <title>
    ...
```

**提取规则**：

| 字段 | 提取方式 | 示例 |
|------|---------|------|
| `sourceFlowId` | 文件名去掉 `.yaml` 后缀，**保留原始字符**（含横线/不含横线都行） | `c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a` |
| `sourceFlowFile` | 文件名 | `c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml` |
| `name` | 第 1 行 `name:` 后的字符串 | 登录接口用例编排 |
| `priority` | 第 2 行 `priority:` 后的字符串 | high |
| `tags` | 第 3+ 行的数组元素列表 | [接口测试, 登录, P0-P3] |

---

## 2. 用户输入处理

### 2.1 输入类型识别

| 用户输入样例 | 类型 | 处理 |
|------------|------|------|
| "生成测试计划" | 模糊 | 列出全部 |
| "做一个登录接口的 plan" | 标题关键字 | Grep 名称过滤 |
| "用 c5e7f8a9、d6f8a9b0 这两个" | 多个 ID | 直接选用 |
| "用 4e2c4a40-4ee3-45ea-bac4-aede9a44c90f" | 标准 UUID | 直接选用 |
| "把登录相关的编排做个 plan" | 标题关键字 | Grep 名称过滤 |

### 2.2 ID 格式归一化（**识别时宽松，写入时严格**）

用户给的 ID 可能多种格式：

- `c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a`（标准 UUID，含横线）
- `c5e7f8a90b1c2d3e4f5a6b7c8d9e0f1a`（32 位无横线）
- `c5e7f8a9`（前缀）
- 完整文件名 `c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml`

**识别策略**：

1. 把用户输入去掉可能的横线，转成 32 位无横线字符串
2. 把目录里所有文件名也转成 32 位无横线
3. 匹配上 → 选用；匹配不上 → 报错让用户修正

**写入策略**：用文件名**原始内容**作为 `sourceFlowId` 和 `sourceFlowFile`，不要自作主张加/去横线。

### 2.3 标题过滤示例

用户说"做一个登录接口的 plan"：

```
扫描结果：
  c5e7f8a9…0f1a — 登录接口用例编排   ← ✅ 命中
  d6f8a9b0…1a2b — 登录→更新用户信息  ← ✅ 命中（包含"登录"）
  e7f8a9b0…2a3b — 登录成功 - 修改用户信息  ← ✅ 命中
  4e2c4a40…c90f — 用户注册+登录完整流程  ← ✅ 命中

行为：
  命中 ≥ 2 → 列出来用 AskUserQuestion 让用户确认/缩范围
  命中 = 1 → 直接选用，告诉用户"已为你选中 XXX"
  命中 = 0 → 告诉用户"没找到匹配项，列出全部让你选"
```

---

## 3. AskUserQuestion 展示格式

### 3.1 单选场景

```yaml
question: "请选择要纳入测试计划的编排"
header: "选编排"   # 必须在 12 字符内
multiSelect: true
options:
  - label: "c5e7f8a9…0f1a — 登录接口用例编排"
    description: "tags: 接口测试, 登录, P0-P3（priority: high）"
  - label: "d6f8a9b0…1a2b — 登录→更新用户信息"
    description: "tags: 接口测试, 主流程, Token 串联（priority: high）"
  - label: "e7f8a9b0…2a3b — 登录成功 - 修改用户信息"
    description: "tags: 接口, 主流程, 冒烟（priority: high）"
  - label: "4e2c4a40…c90f — 用户注册+登录完整流程"
    description: "tags: 冒烟, 主流程, P0（priority: high）"
```

### 3.2 选项数限制

`AskUserQuestion` 最多 4 个选项。超过 4 个时：
- 展示前 4 个
- "Other" 选项由工具自动添加，用户可手动填入

> 💡 **技巧**：如果编排数 > 4，先用文字列表全展示，然后 `AskUserQuestion` 只问 "你想用哪个？或者直接告诉我全部 ID/title"。

### 3.3 标签截断

label 太长会被截断，所以用 ID 前 8 位 + `…` + ID 后 4 位 + ` — ` + name 形式。

---

## 4. type 推断规则（仅供内部参考）

> ⚠️ **自 2026-09 起**：plan 目录命名规则已硬编码为 `plan-web-{ts}-{name}`，**不再使用 plan type 段**（`plan-api-...` / `plan-app-...` / `plan-mixed-...` 等历史命名已废弃）。
>
> 但 plan 的"性质"仍有参考价值，所以本节保留 type 推断逻辑，**仅用于预览展示**，不写入目录名。

### 4.1 任务类型清单

参考 `bigbear-test-runner` 的合法 type：

| Type | 含义 |
|------|------|
| `api` | 接口测试 |
| `web` | Web UI（含 pc） |
| `pc` | PC 客户端 UI |
| `android` | Android UI |
| `ios` | iOS UI |
| `harmonyos` | 鸿蒙 UI |
| `miniapp` | 小程序 UI |
| `dynamic-function` | 动态函数（旧别名，等价 .py 文件） |

### 4.2 plan type 推断（仅预览展示）

| 所有所选 flow 的 task.type 集合 | plan type（预览用） |
|-------------------------------|-------------------|
| 全部 `api` | `api` |
| 全部 `web` 或 `pc` | `web` |
| 全部 `android` / `ios` / `harmonyos` / `miniapp` | `app` |
| 多种类型混合（含 api + UI） | `mixed` |
| 含 `dynamic-function` + 其他 | `mixed`（视为混合） |

### 4.3 预览展示

```yaml
📊 预览中可包含（不影响目录名）:
  - 类型: api    # 推断结果，仅供用户理解 plan 性质
  - 类型: web
  - 类型: mixed
```

> 💡 即使是 `api` 类型的 plan，目录名也固定是 `plan-web-...`（不再带 `api` 段）。runner 通过 `flows[].tasks[].type` 自己识别实际执行类型，与目录名无关。

---

## 5. 数据来源参考

### 5.1 真实编排示例（来自 `读书屋项目-WEB端/AI-自动化测试编排/`）

**`c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml`**：

```yaml
name: 登录接口用例编排
priority: high
tags:
  - 接口测试
  - 登录
  - P0-P3
case_flows:
  - id: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a
    title: 登录接口用例编排
    priority: high
    tags:
      - 接口测试
      - 登录
      - P0-P3
    tasks: [...]
```

**`4e2c4a404ee345eabac4aede9a44c90f.yaml`**（无横线 32 位）：

```yaml
name: 用户注册+登录完整流程
priority: high
tags:
  - 冒烟
  - 主流程
  - P0
case_flows:
  - id: 4e2c4a40-4ee3-45ea-bac4-aede9a44c90f  # ⚠️ 文件名无横线，case_flows[].id 含横线
    title: 用户注册+登录完整流程
    priority: high
    tags: [...]
    tasks: [...]
```

> ⚠️ **sourceFlowId 始终用文件名原值**（不含横线），不要用 `case_flows[0].id`（含横线）作为 sourceFlowId，否则会和文件名不一致。

---

## 6. 异常处理

### 6.1 编排目录不存在

```
❌ 未找到编排目录：{工作空间}/AI-自动化测试编排/

可能原因：
  1. 工作空间根目录不对（请确认当前所在项目）
  2. 还没生成任何编排（先用 bigbear-test-flow-builder 生成编排）

是否：
  a) 让我猜一个工作空间根目录
  b) 退出，你自己处理
```

### 6.2 编排文件格式异常

```
⚠️ 编排文件 {file} 缺少必要字段（name / priority / tags）

已跳过该文件。
```

### 6.3 用户给的 ID 全都找不到

```
❌ 你给的 ID 在 AI-自动化测试编排/ 里都找不到：

  ❌ xxx-yyyy  ← 文件名不存在
  ❌ zzz-wwww  ← 文件名不存在

当前可用的编排（共 4 个）：
  1. c5e7f8a9…0f1a — 登录接口用例编排
  2. d6f8a9b0…1a2b — 登录→更新用户信息
  3. e7f8a9b0…2a3b — 登录成功 - 修改用户信息
  4. 4e2c4a40…c90f — 用户注册+登录完整流程

请重新指定，或直接告诉我用哪个。
```
