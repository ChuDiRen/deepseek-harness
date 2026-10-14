---
name: bigbear-api-case-generator
description: 基于接口 MD 文档生成 API 测试用例，每个接口一个独立的新文件（文件名带 YYYYMMDDHHMMSS 时间戳）。用户可指定单个接口 MD 直接生成；未指定时按现有流程扫描全部 MD 询问。触发条件：用户说"生成接口测试用例"、"生成 XXX 接口的用例"、"补充 XXX 接口的用例"。
---

# bigbear-api-case-generator — 接口测试用例生成器

## 核心能力

- **输入**：单个接口 MD 路径（可由用户直接指定；未指定时扫描后询问）
- **输出**：一个测试用例 MD 文件，文件名 = `<interface_name>_测试用例_<YYYYMMDDHHMMSS>.md`
- **每次独立**：每次生成都是全新的文件，**不读、不改、不合并**任何已有用例文件
- **本技能无 subagent**——main flow（AI 本身）直接读 MD、读 references/、渲染 case MD、写入文件

## 工作目录约定

```
{工作空间}/
├── AI-信息采集/{batch}/raw*.json          ← 录制数据（不读）
├── AI-接口管理/**/*.md                    ← 接口文档（输入）
│   ├── {module_a}/001_POST_user_login.md
│   ├── {module_b}/...
│   └── {batch}/004_GET_friendLink_*.md
└── AI-测试用例/                          ← 测试用例（输出）
    └── {module}/
        ├── 用户登录_测试用例_20260610150000.md
        ├── 用户登录_测试用例_20260610160000.md
        └── ...
```

**模块推断规则**：从接口 MD 的**父目录名**直接当作 module 名。

## 触发条件

满足其一：
- 用户说"生成接口测试用例"
- 用户说"生成 XXX 接口的用例"（指定接口）
- 用户提供具体 MD 路径
- 用户说"补充 XXX 接口的用例"（指定接口）

## 执行流程

### Step 1：判断用户是否指定了具体接口

检查用户输入是否包含：
- 具体接口名（如 "登录提交接口"、"001_POST_user_login"）
- 具体 MD 路径（如 `AI-接口管理/用户模块/001.md`）

如果**指定了** → 直接进入 Step 3，定位那个 MD，跳过扫描。
如果**未指定** → 进入 Step 2 扫描询问。

### Step 2：扫描 + 询问（仅在未指定接口时）

Main flow 扫描 `AI-接口管理/**/*.md`，按 module 分组输出清单。

询问用户：
- 单一模块 / 多个模块 / 单个接口 / 全部

**默认**：每次只处理一个模块。

### Step 3：生成时间戳

Main flow 在派发前生成一个**整批共用**的 14 位时间戳 `YYYYMMDDHHMMSS`（例：`20260610150000`）。

如果一次只处理 1 个接口，**也生成时间戳**——保证文件不撞名。

### Step 4：main flow 直接处理每个接口

Main flow（AI 本身）对每个接口执行以下动作——**不派发 subagent**：

1. **读取接口 MD**（`Read` 工具）
2. **读取参考规范**：
   - `references/testcase-spec.md`（场景设计、断言、占位符规范）
   - `references/apicase-template.md`（Markdown 结构、frontmatter 字段）
3. **设计测试用例**：
   - 正常场景（必填参数齐全 / 所有参数合法 / 列表分页）
   - 异常场景（参数缺失 / 类型错误 / 鉴权失败 / 资源不存在 / 越权）
   - 边界场景（空值 / 长度边界 / 分页 0、负数、超大 / 重复提交）
4. **渲染完整 Markdown**（参考 `apicase-template.md`）：
   - frontmatter 7 个字段（convert / batch / interface_key / interface_name / interface_file / case_count / generated_at）
   - `## <场景名>` 段落
   - 每个段落含：### 用例信息 / ### 请求信息 / ### 请求头 / ### URL参数 / ### 请求体参数 / ### 预期结果
5. **写入文件**（`Write` 工具）：`{module_dir}/<interface_name>_测试用例_<TIMESTAMP>.md`（UTF-8）
   - `module_dir` = 接口 MD 父目录路径
   - 如 `AI-测试用例/{module}/` 不存在则用 `Bash` 工具 `mkdir -p` 创建

### Step 5：汇总报告

处理完所有接口后，main flow 输出汇总报告。

## 关键字段说明

### 接口 MD 读取要点

从 MD 提取（参考 doc-gen 的 `apidoc-spec.md`）：
- `### 接口ID`、`### 请求方法`、`### 请求路径`、`### 完整URL示例`、`### 描述`
- `## 二、URL参数` 表格
- `## 三、请求头参数` 表格
- `## 四、请求体参数` 表格
- `## 五、响应` → `### 5.1 正常响应` / `### 5.2 异常响应`

### frontmatter 字段（必须严格按此格式）

```yaml
---
convert: apitest
batch: <批次号，如 20260609-223046>
interface_key: <METHOD> <PATH>[?param1=&param2=...]
interface_name: <接口名，从 MD 的 ### 接口名称 读取>
interface_file: <相对工作空间的接口 MD 路径>
case_count: <本文件用例总数>
generated_at: <本次生成时间，ISO 格式 YYYY-MM-DDTHH:MM:SS>
---
```

### filename 格式

`<interface_name>_测试用例_<YYYYMMDDHHMMSS>.md`

例：`GET_book_listClickRank_测试用例_20260610150000.md`

## 报告模板

```text
✅ 接口测试用例生成完成

📂 本次处理 {N} 个接口

📁 接口：<interface_name>
   - 文件：{module_dir}/<interface_name>_测试用例_<TIMESTAMP>.md
   - 用例数：{M} 条

📁 接口：<interface_name_2>
   - ...

📊 统计：
- 时间戳：{TIMESTAMP}（整批共用）
- 本次新增用例文件：N 个
- 总用例条数：K 条
```

## 注意事项

1. **可指定单接口生成**——用户说"XXX 接口的用例"时直接处理该 MD，跳过扫描
2. **每次独立**——不读、不改、不合并已有用例文件
3. **整批共用一个时间戳**——Step 3 一次生成，所有接口用同一个 YYYYMMDDHHMMSS
4. **同接口多版本共存**——文件名带时间戳，同一接口多次生成会有多个文件
5. **用户自己挑版本**——历史文件由用户决定保留哪个、删哪个
6. **每个接口一个 MD 文件**——一个 MD 只含一个接口的用例
7. **模块从父目录推**——不维护模块映射表
8. **MD 格式严格**——所有 `##` 标题井号后留半角空格，生成后必须 grep 自检

## 与其他技能的关系

```
bigbear-api-record-cli      →  录制 raw JSON
bigbear-api-doc-generator   →  单个 raw.json → MD
bigbear-api-case-generator  →  单个接口 MD → case 文件（当前技能，main flow 直接处理，无 subagent）
```

**关键数据流**：
1. doc-gen 把**单个** raw JSON 文件转成 MD，输出到 `AI-接口管理/{batch}/`
2. 用户**自行整理**（可选）：把 MD 移到模块子目录 / 改名
3. 当前技能读 MD，用 main flow（AI）直接渲染 case MD，写到 `AI-测试用例/{module}/<interface_name>_测试用例_<TIMESTAMP>.md`
