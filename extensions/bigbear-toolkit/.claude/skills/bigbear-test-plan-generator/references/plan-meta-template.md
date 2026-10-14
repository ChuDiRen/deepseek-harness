# plan meta.yaml 模板与字段规范

本文档定义 `AI-自动化测试计划/{plan_id}/meta.yaml` 的字段结构和写入规则。

---

## 1. 完整模板

```yaml
id: plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息
name: 登录接口用例编排 + 登录→更新用户信息
priority: high
environmentKey: 读书屋-测试
executionStrategy: sequential
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

---

## 2. 字段详解

### 2.1 顶层字段

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `id` | string | ✅ | 计划唯一标识，**等于父目录名**（去掉 `.yaml`） | `plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息` |
| `name` | string | ✅ | 计划显示名，可含中文、+、空格等 | `登录接口用例编排 + 登录→更新用户信息` |
| `priority` | string | ✅ | `high` / `medium` / `low` | `high` |
| `environmentKey` | string | ✅ | 环境目录名（对应 `AI-环境变量/{env_key}/`） | `读书屋-测试` |
| `executionStrategy` | string | ✅ | **固定 `sequential`**（本 Skill 不询问） | `sequential` |
| `flows` | array | ✅ | 编排列表，**数组顺序 = 执行顺序** | 见 §2.2 |
| `tags` | array | ❌ | plan-level 标签（可选） | `[冒烟, 主流程, P0]` |
| `created_at` | string | ✅ | `YYYY-MM-DD HH:MM:SS`，**必须单引号包裹** | `'2026-09-10 10:15:30'` |

### 2.2 flows[]. 子字段

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `sourceFlowId` | string | ✅ | 编排 ID，**保留原始格式**（含或不含横线都行） | `c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a` |
| `sourceFlowFile` | string | ✅ | 编排文件名（含 `.yaml`），runner 据此查找 | `c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml` |
| `name` | string | ✅ | 编排的 name（从编排 YAML 第 1 行照抄） | 登录接口用例编排 |
| `priority` | string | ✅ | 编排的 priority（从编排 YAML 第 2 行照抄） | high |
| `tags` | array | ✅ | 编排的 tags（从编排 YAML 第 3+ 行照抄） | `[接口测试, 登录, P0-P3]` |

> 💡 **flow-level tags 是必填的**。每个编排都自带 tags，**照抄**即可，不要省略。

---

## 3. ID 命名规则（硬编码）

### 3.1 目录命名

```
plan-web-{YYYYMMDD-HHMMSS}-{编排name}
```

> ⚠️ **本规则为硬编码，不询问用户、不接受覆盖**。如需自定义，由用户事后 `mv` 目录。

| 段 | 取值 | 说明 |
|----|------|------|
| `plan-` | 固定前缀 | — |
| `web` | 固定 | 通用 Web 平台标识 |
| `YYYYMMDD-HHMMSS` | 当前时间戳 | 例：`20260910-101530` |
| `{编排name}` | 所选 flow 的 name 拼接 | 见下方 3.2 |

### 3.2 编排 name 拼接规则

| 选中 flow 数 | 编排name 取值 | 示例 |
|--------------|-------------|------|
| 1 个 | 直接用该 flow 的 `name` 字段原值 | `登录接口用例编排` |
| 多个 | 用 ` + ` 拼接，**保留原始中文/符号** | `登录接口用例编排 + 登录→更新用户信息` |

### 3.3 id 字段 = 目录名

```python
plan_id = os.path.basename(plan_dir_path)
# 例如 "plan-web-20260910-101530-登录接口用例编排"
# 例如 "plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息"
```

`meta.yaml` 的 `id` 字段**必须等于** `plan_id`，不一致会导致 runner 找不到计划。

### 3.4 实例参考

| 目录名 | 解释 |
|--------|------|
| `plan-web-20260910-101530-登录接口用例编排` | 单 flow，name 直接用 |
| `plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息` | 多 flow，用 ` + ` 拼接 |
| `plan-web-20260910-101530-登录→更新用户信息` | name 含特殊符号（→），原样保留 |
| `plan-api-login-20260827-150820` | **历史命名示例**，新生成不再使用 |
| `plan-d6f8a9b0-only-20260908161943` | **历史命名示例**，新生成不再使用 |
| `plan-login-updateinfo-20260909-225754` | **历史命名示例**，新生成不再使用 |
| `4e2c4a404ee345eabac4aede9a44c90f` | **历史遗留**（用 flow id 哈希当目录名） |

---

## 4. 落盘步骤

### 4.1 目录创建

```bash
# 时间戳取当前时间 YYYYMMDD-HHMMSS
TS=$(date +%Y%m%d-%H%M%S)

# 单 flow：编排 name 直接拼接
mkdir -p "{工作空间}/AI-自动化测试计划/plan-web-${TS}-登录接口用例编排/"

# 多 flow：编排 name 用 " + " 拼接
mkdir -p "{工作空间}/AI-自动化测试计划/plan-web-${TS}-登录接口用例编排 + 登录→更新用户信息/"
```

> 💡 Windows cmd 没有 `date +%Y%m%d-%H%M%S`，AI 直接用 Python `datetime.now().strftime('%Y%m%d-%H%M%S')` 生成。

### 4.2 文件写入

用 `Write` 工具，文件路径：

```
{工作空间}/AI-自动化测试计划/plan-web-{ts}-{编排name}/meta.yaml
```

### 4.3 YAML 验证（必做）

```bash
python -c "import yaml; d=yaml.safe_load(open(r'<plan_dir>/meta.yaml', encoding='utf-8')); print('✅ meta.yaml OK, id=', d.get('id'))"
```

期望输出：

```
✅ meta.yaml OK, id= plan-web-20260910-101530-登录接口用例编排
```

### 4.4 字段验证（必做）

```python
# 验证必填字段都存在
required = ['id', 'name', 'priority', 'environmentKey', 'executionStrategy', 'flows', 'created_at']
for k in required:
    assert k in d, f'缺少必填字段: {k}'

# 验证 flows[] 格式
for i, flow in enumerate(d['flows']):
    flow_required = ['sourceFlowId', 'sourceFlowFile', 'name', 'priority', 'tags']
    for k in flow_required:
        assert k in flow, f'flows[{i}] 缺少必填字段: {k}'

# 验证 sourceFlowFile 真实存在
import os
for flow in d['flows']:
    p = os.path.join('{工作空间}', 'AI-自动化测试编排', flow['sourceFlowFile'])
    assert os.path.exists(p), f'sourceFlowFile 不存在: {p}'

# 验证 environmentKey 真实存在
env_dir = os.path.join('{工作空间}', 'AI-环境变量', d['environmentKey'])
assert os.path.isdir(env_dir), f'environmentKey 目录不存在: {env_dir}'

print('✅ 字段验证全部通过')
```

---

## 5. 写入陷阱

### 5.1 created_at 单引号

```yaml
# ✅ 正确
created_at: '2026-08-27 15:08:20'

# ❌ 错误（冒号会让 YAML 解析报错或拆成 mapping）
created_at: 2026-08-27 15:08:20

# ❌ 错误（数字会被解析成 int）
created_at: "2026-08-27 15:08:20"   # 这个其实也可以，但单引号更稳
```

### 5.2 缩进严格用 2 空格

```yaml
# ✅ 正确
flows:
  - sourceFlowId: xxx
    name: yyy

# ❌ 错误（4 空格）
flows:
    - sourceFlowId: xxx
      name: yyy
```

### 5.3 tags 数组写法

```yaml
# ✅ 正确（推荐，每个 tag 一行）
tags:
  - 接口测试
  - 登录
  - P0-P3

# ✅ 也行（行内数组）
tags: [接口测试, 登录, P0-P3]

# ❌ 错误
tags:
- 接口测试
- 登录
```

### 5.4 sourceFlowId 格式严格保留

```yaml
# 文件名是 c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml（含横线）
# ✅ 正确
- sourceFlowId: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a
  sourceFlowFile: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml

# 文件名是 c5e7f8a90b1c2d3e4f5a6b7c8d9e0f1a.yaml（无横线）
# ✅ 正确
- sourceFlowId: c5e7f8a90b1c2d3e4f5a6b7c8d9e0f1a
  sourceFlowFile: c5e7f8a90b1c2d3e4f5a6b7c8d9e0f1a.yaml

# ❌ 错误（去横线或加横线）
- sourceFlowId: c5e7f8a90b1c2d3e4f5a6b7c8d9e0f1a   # 但文件名实际有横线
  sourceFlowFile: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml
```

---

## 6. 示例

### 示例 1：新格式 — 多 flow 完整版（推荐写法）

```yaml
# 目录: plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息/meta.yaml
id: plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息
name: 登录接口用例编排 + 登录→更新用户信息
priority: high
environmentKey: 读书屋-测试
executionStrategy: sequential
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

### 示例 2：新格式 — 单 flow 简化版（推荐写法）

```yaml
# 目录: plan-web-20260910-101530-登录接口用例编排/meta.yaml
id: plan-web-20260910-101530-登录接口用例编排
name: 登录接口用例编排
priority: high
environmentKey: 读书屋-测试
executionStrategy: sequential
flows:
  - sourceFlowId: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a
    sourceFlowFile: c5e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a.yaml
    name: 登录接口用例编排
    priority: high
    tags:
      - 接口测试
      - 登录
      - P0-P3
created_at: '2026-09-10 10:15:30'
```

### 示例 3：历史命名（仅供参考，新生成不再使用）

```yaml
# 来自 AI-自动化测试计划/plan-api-login-20260827-150820/meta.yaml（历史）
# 新生成请用示例 1 / 示例 2 的命名规则
id: plan-api-login-20260827-150820
name: 登录接口用例编排 + 登录→更新用户信息
priority: high
environmentKey: 读书屋-测试
executionStrategy: sequential
flows: [...]
created_at: '2026-08-27 15:08:20'
```

---

## 7. 与 runner 的交互

### 7.1 runner 读取流程

`bigbear-test-runner run <root_dir> <plan_id>` 时：

1. 读 `<root_dir>/AI-自动化测试计划/<plan_id>/meta.yaml`
2. 解析 `flows[]`，按 `executionStrategy` 串行执行（本 Skill 生成的 plan 固定 sequential）
3. 每个 flow 读 `<root_dir>/AI-自动化测试编排/<sourceFlowFile>` 拿 `case_flows → tasks`
4. `environmentKey` 决定读 `<root_dir>/AI-环境变量/<environmentKey>/env_var.yaml`

**调用示例**（多 flow，name 含中文 + 特殊符号）：

```bash
bigbear-test-runner run {工作空间} \
  "plan-web-20260910-101530-登录接口用例编排 + 登录→更新用户信息"
```

> 💡 plan_id 含中文或特殊符号（`+`、`→`、`空格`）时，**必须加双引号**包裹。

### 7.2 必须保证的契约

- ✅ `meta.yaml` 路径 = `<root_dir>/AI-自动化测试计划/{id}/meta.yaml`
- ✅ `id` == 目录名
- ✅ `flows[].sourceFlowFile` 存在于 `<root_dir>/AI-自动化测试编排/`
- ✅ `environmentKey` 目录存在于 `<root_dir>/AI-环境变量/`

任一不满足 → runner 报错。
