---
name: bigbear-api-doc-generator
description: 接口文档生成器。将 bigbear-record-cli 录制的 raw JSON 单个文件解析并生成标准化 MD 接口文档。触发场景：用户说"生成接口文档"、"接口文档梳理"、"整理接口文档"、"接口文档生成"，并提供具体 raw JSON 文件路径时使用。
---

重点： 请使用中文沟通！！

# bigbear-api-doc-generator — 接口文档生成技能

## ⚠️ 硬性约束（必读，优先级最高）

**本技能的核心原则：基于事实，不臆测任何内容。**

| 类型       | 处理规则                                                                                                  |
| ---------- | --------------------------------------------------------------------------------------------------------- |
| **正常响应** | 必须从 raw JSON 的 `response.body` 中提取，未捕获到则标注"未捕获到响应体"，**禁止伪造 JSON**            |
| **异常响应** | **必须**从 raw JSON 中真实存在的异常响应（HTTP 4xx/5xx 或业务错误码）提取，**严禁脑补、臆测、编造** |
| **接口描述** | 默认"待补充：{METHOD} {path}"，由用户生成后手工补全；脚本不参与业务命名                                 |
| **参数说明** | 必须从 raw JSON 实际参数名/值中归纳，不存在的字段绝不写入                                                   |
| **示例值**   | 只能使用 raw JSON 中真实出现过的值，不允许构造示例                                                         |
| **占位符**   | 表格单元格统一用 `待补充`；代码块内统一用 `// 待补充：请提供真实数据`                                       |
| **脚本位置** | 正式生成脚本统一放在 `scripts/` 目录                                                                        |

> **对异常响应信息的特殊约束**：
> - raw JSON 中**没有**异常响应数据 → 5.2 章节明确标注 **"⚠️ 录制批次中未捕获到任何异常响应"**
> - raw JSON 中**有**异常响应数据 → 必须**完整、真实**地记录每一条
> - 用户**主动提供**的异常响应信息 → 写入时**保留用户原话**，不擅自改写
> - **绝对禁止**：在没有真实数据的情况下，生成 `{"error_code": 500, "msg": "Internal Server Error"}` 这类凭空想象的异常响应示例
>
> **本技能的定位是"如实记录"，不是"知识库生成器"**——没有提供的内容就留空，让用户去补充。

## 核心能力

将 `bigbear-record-cli` 录制的**单个 raw JSON 文件**直接转为 MD 接口文档。**不做模块分类、不做接口命名（中英文双名）**——这些都交给用户在生成后自己整理。

```
AI-信息采集/{batch}/raw01.json  →  AI-接口管理/{batch}/001_GET_xxx.md
```

**作用域**：
- 一次处理**一个** `raw.json` 文件
- 该文件里通常含**多个**接口条目（数组或单个 dict），每个条目 = 一个 MD
- 跨文件 / 跨批次处理不在本技能范围

## 产物模板与规范

执行前必须按需读取：

- `references/apidoc-template.md`：最终 MD 文件结构与字段
- `references/apidoc-spec.md`：事实性约束、去重规则

## 目录结构

```
bigbear-api-doc-generator/
├── SKILL.md                          ← 本文件
├── references/
│   ├── apidoc-template.md             ← MD 文件结构
│   └── apidoc-spec.md                 ← 生成规则
└── scripts/
    ├── scanner.py                    ← 单文件解析工具
    └── api_doc_generator.py          ← MD 生成器（主入口）

{工作空间}/
├── AI-信息采集/{batch}/raw{NN}.json   ← 录制数据（输入）
└── AI-接口管理/{batch}/                ← MD 文档（输出，按批次组织）
    ├── 001_GET_xxx.md
    ├── 002_GET_xxx.md
    └── ...
```

> **按批次组织输出**：`AI-接口管理/{batch}/{seq:03d}_{METHOD}_{path_safe}.md`
> 用户在生成后可自由重命名文件、移入模块子目录、补充业务描述。

## 触发条件

满足任一即可：
- 用户说"生成接口文档" + 提供具体 raw.json 路径
- 用户说"接口文档梳理" + 提供具体 raw.json 路径
- 用户说"整理接口文档" + 提供具体 raw.json 路径
- 用户说"接口文档生成" + 提供具体 raw.json 路径

## 执行流程

### Step 1：确认输入文件

询问用户具体要处理哪个 `raw.json` 文件（如 `AI-信息采集/20260609-223046/raw01.json`）。

如果用户没指定，**必须询问**——本技能**不**自己扫描整个工作空间找 raw 文件。

### Step 2：执行生成

```bash
python .claude/skills/bigbear-api-doc-generator/scripts/api_doc_generator.py <raw_json_path>
```

可选参数：
- `--output-dir <dir>`：自定义输出目录（默认镜像到 `AI-接口管理/...`）
- `--dry-run`：仅生成预览，不写文件
- `--include-all`：不过滤任何响应 Content-Type（默认会过滤 HTML/CSS/JS/图片/证书等非业务接口）
- `--include-content-types <MIME>`：自定义保留的响应 Content-Type（可多次指定，如 `--include-content-types application/json --include-content-types application/xml`）。**与 `--include-all` 互斥**

### Step 3：输出完成报告

按下方"完成报告"模板输出清单。

## 输出目录默认规则

- 输入 `AI-信息采集/{batch}/raw01.json` → 输出 `AI-接口管理/{batch}/{seq:03d}_{METHOD}_{path_safe}.md`
- 镜像规则：路径里的 `AI-信息采集` 替换为 `AI-接口管理`，**去掉 `raw01.json` 前缀**
- 文件名模板：`<seq:03d>_<METHOD>_<path_safe>.md`
- **跨 raw 文件续编号**：脚本执行前扫描输出目录中已有 `{seq:03d}_*.md`，从 `max_seq+1` 开始编号
  - 例：raw01.json 写入 001-005 后，跑 raw02.json 时会从 006 继续编（避免每个 raw 文件都从 001 开始互相覆盖）
- **(method, path) 重复样本自动加 `__N` 后缀**：扫描输出目录中已存在的 MD 文件名反推 `(method, path)`，新接口遇到已存在的接口时自动用 `__2`、`__3`、`__N` 后缀
  - 例：raw14.json (POST /user/login) 写入 002_POST_user_login.md；raw17.json (POST /user/refreshToken) 是新接口 → 写入 003_POST_user_refreshToken.md；raw23.json 还是 POST /user/refreshToken → 写入 004_POST_user_refreshToken__2.md（保留多份 token 刷新样本）
- **续编号 + `__N` 后缀都基于 `used_names` 状态机**，重跑同文件会直接覆盖 `__N` 同名文件

## Content-Type 过滤（默认行为）

录制时浏览器会发出大量"非业务"请求（HTML 页面、CSS、JS、图片、证书下载等），**默认会被过滤掉**：

| MIME 类别 | 是否保留 | 说明 |
|---|---|---|
| `application/json` / `+json` | ✅ 保留 | 标准 JSON API |
| `application/xml` / `text/xml` | ✅ 保留 | XML API |
| `text/plain` / `text/` | ✅ 保留 | 文本响应 |
| `application/x-www-form-urlencoded` | ✅ 保留 | 表单响应 |
| `text/html` | ❌ 过滤 | HTML 页面（带 `.html` 的页面 URL） |
| `text/css` | ❌ 过滤 | CSS 静态资源 |
| `application/javascript` / `text/javascript` | ❌ 过滤 | JS 静态资源 |
| `image/*`、`audio/*`、`video/*` | ❌ 过滤 | 媒体文件 |
| `application/x-pkcs12` | ❌ 过滤 | mitm 证书下载 |
| `application/octet-stream`、`application/pdf` | ❌ 过滤 | 二进制文件 |
| 空 Content-Type | ❌ 过滤 | 无法判定则按"非业务"对待（保守） |

**自定义保留范围**：`--include-content-types application/json --include-content-types application/xml`
**不过滤（保留全部）**：`--include-all`

## 完成报告

```text
输入文件：{raw_path}
原始条目：N 条 → 按 method+path 去重后 M 个
Content-Type 过滤：{默认 / 自定义白名单 / include-all}
过滤后：M 个接口（丢弃 K 个非业务接口）
已写入 MD：M 个（编号 001 - {seq_end:03d}）

输出目录：{工作空间}/AI-接口管理/{batch}/

接口列表：
1. 001_GET_xxx.md  ←  GET /xxx  [有响应体] [无异常响应]
2. 002_GET_yyy.md  ←  GET /yyy  [有响应体] [无异常响应]
3. 003_GET_xxx__2.md  ←  GET /xxx  ← 第 2 份样本（method+path 重复）
4. ...

- 仅处理指定文件：{raw_path}
- 正常响应体非空接口：X 个 / 无响应体：Y 个
- 异常响应捕获：A 个有 / B 个无（无异常的接口 5.2 已写"未捕获到异常响应"占位）
- 续编号：本次写入起始 seq={seq_start:03d}（自动扫描输出目录已有 N 个文件）
- 重跑同文件：直接覆盖（无备份），用户需自行保留历史版本
```

## 重跑行为

对同一个 `raw.json` 重新执行时：**直接覆盖**同名 MD 文件，**不备份**。这是显式选择的最简行为。

- ✅ 简单可预测——同名输入永远产出同名输出
- ⚠️ 用户的**手工修改**（重命名、补描述）会被覆盖
- 用户要保留历史版本 → 跑前先 `cp` 一份，或用 `--output-dir` 输出到不同目录

## 注意事项

1. **必须先确认输入文件**——禁止自动扫描工作空间找 raw 文件
2. **接口 ID 一律 `uuid.uuid4().hex`**：32 位小写十六进制，不含横杠
3. **UTF-8 编码**写入，防止中文乱码
4. **每个接口单独一个 MD 文件**，文件名见 `apidoc-template.md`
5. **单文件内去重规则**：按 `method + path` 去重；多条命中时优先保留 `response.body` 非空的那条
6. **跨文件续编号**：多次调用脚本时，扫描输出目录已有 `{seq:03d}_*.md` 自动续编（不会出现多个 001_xxx.md 互相覆盖）
7. **跨文件 (method, path) 重复样本**：保留多份，自动加 `__N` 后缀（用于记录同一接口的多次响应，如 token 刷新、分页查询等）
8. **默认 Content-Type 过滤**：自动丢弃 HTML/CSS/JS/图片/证书等非业务接口，避免把浏览器页面请求当成 API
9. **重跑直接覆盖**——无需用户手动备份，但 `(method, path)` 重复样本在重跑时会按 seq 大小重新分布（建议保留历史版本前先 `cp` 一份）
10. **不在生成过程中编造任何内容**：正常响应、异常响应、参数说明、示例值，都必须来自 raw JSON 真实数据
11. **不做模块分类与命名**：用户生成后自行整理文件、移入模块子目录、补充业务名
12. **后续工作**：用户可手工把文件移入模块子目录（如 `AI-接口管理/用户模块/001.md`）；这不影响技能本身的运行

## 与其他技能的关系

```
bigbear-record-cli      →  录制 raw JSON
bigbear-api-doc-generator   →  单个 raw.json 文件 → MD（当前技能）
bigbear-api-case-generator  →  读 MD → 生成测试用例
```

**关键数据流**：
1. doc-gen 把**单个** raw JSON 文件转成 MD，输出到 `AI-接口管理/{batch}/`
2. 用户**自行整理**（可选）：把 MD 移到模块子目录 / 改名
3. case-gen 读 MD，生成测试用例
