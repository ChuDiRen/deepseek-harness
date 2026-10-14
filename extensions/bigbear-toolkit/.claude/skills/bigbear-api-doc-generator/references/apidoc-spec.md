# API 接口文档生成规范

本文档定义 `bigbear-api-doc-generator` 的生成规则。最终 Markdown 文件结构见 `apidoc-template.md`。

## 事实性约束

- 只记录 raw JSON 中真实存在的数据，禁止臆测业务规则、异常响应、示例值或参数说明。
- 正常响应必须来自 `response.body`；未捕获时标注"未捕获到响应体"，**不得伪造 JSON**。
- 异常响应必须来自真实 HTTP 4xx/5xx 或业务错误码；没有异常响应时，5.2 章节写"录制批次中未捕获到异常响应，请补充"。
- 用户主动补充的信息可以写入文档，但应保留用户原话，不擅自扩写。

## 输入规则

- **本技能处理单个 raw JSON 文件**——调用方（用户或上层 AI）必须明确提供 `xx.json` 的具体路径。
- 一次只处理一个文件；跨文件 / 跨批次处理不在本技能范围。
- 脚本**不**扫描工作空间找 raw 文件——必须传路径。
- 一个 `raw.json` 可以是单个 dict（一个接口）或 list（多个接口），两种都支持。
- 所有 JSON 和 Markdown 按 UTF-8 读写。

## 解析规则

- `method` 来自 `request.method`，输出时统一大写。
- `path` 来自 `request.url` 去掉域名和 query 后的路径。
- URL query 参数来自 `request.url` 的 `?` 后部分。
- 请求头只保留必要字段：`Content-Type`、`Authorization`、`Accept`、`x-requested-with`；浏览器自动头默认不写入文档。
- 请求体示例直接来自 `request.body`，缺失则写统一占位。
- 响应示例直接来自 `response.body` 原始字符串，不重新构造。

## 去重规则（文件内）

- 一个 `raw.json` 内部按 `method + path` 组合去重（不含 query）。
- 多条命中时**优先保留 `response.body` 非空的那条**；都为空时按 entry 顺序（`seq` 升序）兜底。
- 去重后次序作为文件名 `seq` 前缀，**稳定**。
- **不跨文件去重**——两个 `raw.json` 里的同名接口会分别产出 MD，由用户决定如何合并。

## 命名规则

- 文件名：`{seq:03d}_{METHOD}_{path_safe}.md`
  - `seq`：去重后条目次序，3 位补零
  - `METHOD`：HTTP 方法大写
  - `path_safe`：path 去掉首尾斜杠，斜杠替换为 `_`
- MD 标题：`{METHOD} {path}`（如 `# GET /book/listClickRank`）
- 非法字符：`< > : " / \ | ? *` 自动替换为 `_`，避免 Windows 文件名规则冲突。

## 输出规则

- **默认输出目录**：镜像 `AI-信息采集/` → `AI-接口管理/`
  - 例：`AI-信息采集/20260609-223046/raw01.json` → `AI-接口管理/20260609-223046/`
- **自定义输出目录**：`--output-dir <dir>` 覆盖默认行为
- 目录不存在时自动 `mkdir -p`
- 每个接口必须有一个 32 位小写无横杠 UUID：`uuid.uuid4().hex`
- 文档必须完整包含"一、基本信息"到"五、响应"，其中 5.1 和 5.2 小节必须齐备
- raw 中缺失内容时：
  - 表格单元格写 `待补充`
  - 代码块内写 `// 待补充：请提供真实数据`
  - 章节顶部可写 `⚠️ 录制批次中未捕获到 XX 数据，请补充`

## 重跑行为

- 用户对**同一个 raw.json** 重新执行 `api_doc_generator.py` 时：**直接覆盖**同名 MD 文件，**不备份**。
- 这是显式选择的最简行为：
  - ✅ 简单可预测——同名输入永远产出同名输出
  - ⚠️ 用户的**手工修改**（重命名、补描述）会被覆盖
  - 用户要保留历史版本 → 跑前先 `cp` 一份，或用 `--output-dir` 输出到不同目录
- 用户的**手工移入模块子目录**（如 `AI-接口管理/用户模块/001.md`）在重跑时**不会**被触碰——脚本不跨目录操作。

## Markdown 渲染硬性约束（防反引号污染）

**禁止用反引号（`` ` ``）包裹纯文本字段**——反引号会把内容渲染成代码块，导致：

- `完整URL示例` 行的 `http://xxxx` 变成 `` `http://xxxx` ``，失去可点击链接属性
- `接口描述`、`接口名称`、`参数值` 等纯文本被代码字体显示
- 各种需要正常排版的字段被破坏

**正确做法**：

| 字段类型 | 写法 | 渲染效果 |
|---|---|---|
| 纯文本（URL、描述、参数值等）| `lines.append("### 完整URL示例")`<br>`lines.append(full_url)` | 普通文本，可自动链接 |
| 真正的代码 / JSON | `lines.append("```json")`<br>`lines.append(json.dumps(...))`<br>`lines.append("```")` | 代码块 |
| 转换说明（"来自 Content-Type"等）| 普通中文句，不加反引号 | 普通文本 |

**反例**（禁止）：

```python
# ❌ 错：把 URL 包成代码
lines.append(f"| 完整URL示例 | `{full_url}` | ...")

# ❌ 错：把参数值包成代码
lines.append(f"| 字段 | `{value}` | ...")

# ❌ 错：把描述包成代码
lines.append(f"| 描述 | `{desc}` | ...")
```

**正例**（正确）：

```python
# ✅ 对：URL 纯文本
lines.append("### 完整URL示例")
lines.append(full_url)

# ✅ 对：参数值纯文本
lines.append(f"| 字段 | {value} | 说明 |")

# ✅ 对：JSON 才用代码块
lines.append("```json")
lines.append(pretty_body)
lines.append("```")
```

**额外防御**：

- 如果 raw JSON 里某个字段值自带反引号（如 `desc` 含 `` `code` ``），生成器**转义**或**剥除**反引号，**不要**让它进 MD
- 文件名也不应含反引号（`sanitize_filename` 已处理）

## 完成报告

完成后用中文输出：

```text
输入文件：{raw_path}
原始条目：{entry_count} 条 → 按 method+path 去重后 {unique_count} 个接口
已写入 MD：{written_count} 个

输出目录：{工作空间}/AI-接口管理/{batch}/

接口列表：
1. 001_GET_book_listClickRank.md ← GET /book/listClickRank [有响应体] [无异常响应]
2. 002_GET_book_listNewRank.md ← GET /book/listNewRank [有响应体] [无异常响应]
...

验证：
- 仅处理指定文件：{raw_path}
- 正常响应体非空接口：N 个 / 无响应体：M 个
- 异常响应捕获：K 个有 / L 个无
- 未编造响应、示例值或参数说明
- 重跑同文件：直接覆盖（无备份），用户需自行保留历史版本
```
