# 环境选择规范

本文档说明如何从 `AI-环境变量/` 目录读取环境列表并让用户选择。

---

## 1. 目录约定

```
{工作空间}/AI-环境变量/
├── 读书屋-测试/                       ← 这是一个环境
│   ├── meta.yaml                     ← 环境元信息
│   └── env_var.yaml                  ← 环境变量
└── {其他环境}/
    ├── meta.yaml
    └── env_var.yaml
```

每个**子目录名** = 一个 environmentKey。

---

## 2. 扫描方式

### 2.1 列出所有环境

```python
# 用 Glob 工具（只看一层子目录）
Glob("{工作空间}/AI-环境变量/*/")
```

返回示例：

```
读书屋项目-WEB端/AI-环境变量/读书屋-测试/
读书屋项目-WEB端/AI-环境变量/默认/
```

### 2.2 读每个环境的 meta.yaml

```yaml
# AI-环境变量/读书屋-测试/meta.yaml
env_name: "读书屋-测试"
description: "华测教育小说平台（novel.hctestedu.com）测试环境"
created_at: "2026-08-25"
default_browser: "chromium"
notes: "注册/登录流程使用此环境"
```

**提取字段**：

| 字段 | 说明 | 示例 |
|------|------|------|
| `env_name` | 环境名（和目录名一致） | `读书屋-测试` |
| `description` | 环境描述（展示给用户） | `华测教育小说平台（novel.hctestedu.com）测试环境` |

### 2.3 env_var.yaml 是 runner 用的

```yaml
# AI-环境变量/读书屋-测试/env_var.yaml
web_project_url:
  value: "http://novel.hctestedu.com"
  description: "读书屋项目 WEB 端基地址"
default_password:
  value: "123456"
  description: "测试环境默认登录密码"
# ...
```

`env_var.yaml` 是 `bigbear-test-runner` 在执行时加载的，**本 Skill 不需要读它**，只要选对 `environmentKey` 即可。

---

## 3. 用户选择环境

### 3.1 询问格式

```yaml
question: "请选择执行环境"
header: "选环境"
multiSelect: false
options:
  - label: "读书屋-测试"
    description: "华测教育小说平台（novel.hctestedu.com）测试环境"
  - label: "默认"
    description: "默认环境描述"
```

### 3.2 默认值推断

按以下优先级选默认：

1. **当前工作空间已有 plan 中引用最多的环境**（用 Glob + Grep 统计）
2. **唯一存在**的环境（只有一个就直接选）
3. **让用户选**

> 💡 当前项目（读书屋项目-WEB端）只有一个环境 `读书屋-测试`，直接默认即可。

---

## 4. environmentKey 写入

### 4.1 写入 meta.yaml

```yaml
environmentKey: 读书屋-测试    # ← 子目录名原样写入
```

### 4.2 验证环境存在

写入前必须 `Glob("{工作空间}/AI-环境变量/{environmentKey}/")` 验证；写入后用户可立刻用 `bigbear-test-runner run {root_dir} {plan_id}` 跑起来。

---

## 5. 多环境场景

如果工作空间有多个环境（例如同时有 `读书屋-测试` / `读书屋-生产` / `读书屋-预发`）：

1. 必须让用户**显式确认** environmentKey（不能自动选）
2. 写入后明确告诉用户"该 plan 将在 **{environmentKey}** 环境下执行"
3. 强调："执行前请确认环境变量值是否正确"

---

## 6. 异常处理

### 6.1 环境目录不存在

```
❌ 找不到环境目录：{工作空间}/AI-环境变量/读书屋-测试/

请确认：
  1. 工作空间根目录是否正确
  2. 环境是否已创建（需要包含 meta.yaml + env_var.yaml）
```

### 6.2 meta.yaml 缺失

```
⚠️ 环境目录存在但缺少 meta.yaml：{工作空间}/AI-环境变量/读书屋-测试/

该环境将被跳过或视为不合法。
```

### 6.3 用户没指定环境 + 多个候选

```
当前工作空间有 3 个环境：
  1. 读书屋-测试
  2. 读书屋-预发
  3. 读书屋-生产

请明确指定要用哪个（出于安全考虑，不会自动选）。
```
