---
name: bigbear-api-cli
description: |
  确定性执行 AIQE 测试计划中的 api 任务。
  流程:读取 case 详情 → Jinja2 渲染 {{var}} → Python requests 发请求 →
  自然语言断言评估响应 → 返回 JSON 结果(PASS/FAIL + 详细)。

  使用时机:编排文件 AI-自动化测试编排/*.yaml 中 task.type == "api" 时,
  必须用本技能,不要自己拼 curl 命令(Windows cmd + 引号 + 中文路径三连坑)。
allowed-tools: Bash(python:*) Read
---

# bigbear-api-cli

确定性 API 请求执行 + 自然语言断言。专为 AIQE 测试计划的 `type: api` 任务设计。

## 为什么需要这个 skill

直接 `curl` 跑 API 测试有三个问题:
1. **shell 引号 / JSON 转义** — Windows cmd + JSON 体的双重引号很容易出错
2. **中文路径** — `AI-动态函数管理\通用工具\xxx.py` 这种路径直接喂给 curl 经常乱码
3. **断言主观** — Agent 用 LLM 自由判断"响应是否成功"不稳定,不可复现

本 skill 用 Python `requests` 库直接发请求,并对响应做**正则匹配的自然语言断言**,
输出结构化 JSON 结果。

## 使用方法

对每个 `type: api` 的 task,Agent 应执行:

### ✅ 推荐方式:用 `--ctx-file`(避免中文/引号转义)

Windows + Git Bash / cmd 下,JSON 里的中文键名和嵌套引号极易被 shell 转义破坏。
Agent 应先把 ctx 写成 UTF-8 JSON 文件,再传文件路径:

```bash
python <skill-dir>/bigbear_api_cli.py execute \
  --project <project_root> \
  --case-id <case_id> \
  --ctx-file <ctx_json_文件路径>
```

具体步骤:
1. 用 Python 写 ctx.json(用 `json.dump(..., ensure_ascii=False)`,文件用 `encoding='utf-8'`):
   ```python
   import json
   with open(r"<任意不含中文的路径>\ctx.json", "w", encoding="utf-8") as f:
       json.dump({"URL": "http://novel.hctestedu.com", "正确账号": "13800138001", "正确密码": "123456"}, f, ensure_ascii=False)
   ```
2. 调用 helper 时传 `--ctx-file <ctx.json 路径>`。
3. 读取 helper stdout 的 JSON,解析 `ok` 字段。

> **为什么用文件**:命令行参数 `--ctx '{...}'` 在 Windows Git Bash 下会把中文 key 转义成 `\uXXXX`、
> 双引号被 shell 吃掉、含空格/换行的 JSON 直接断成多 argv。文件方式全程 UTF-8 字节流,
> 跨平台、跨 shell 一致。

### 备选方式:`--ctx` 直接传(简单场景,纯 ASCII key/value 时可用)

```bash
python <skill-dir>/bigbear_api_cli.py execute \
  --project <project_root> \
  --case-id <case_id> \
  --ctx '{"URL": "http://novel.hctestedu.com", "正确账号": "13800138001", "正确密码": "123456"}'
```

> 含中文 key/value、嵌套引号或换行时,**禁止**用此方式,必须用 `--ctx-file`。

参数说明:
- `--project`:测试项目根目录(含 `AI-自动化测试用例/api/` 子目录)
- `--case-id`:case yaml 的 `case_id`(编排 task.source_id)
- `--ctx`:JSON 字符串,所有 `{{var}}` 的实际值(仅适合纯 ASCII key/value)
- `--ctx-file`:从 UTF-8 JSON 文件读 ctx,优先于 `--ctx`
  - 来源:`task.input_datas` 经 Jinja2 渲染后的 name→value + 之前 task 通过 `outputs` 暴露的变量
- `--timeout`:可选,HTTP 超时秒数(默认 30)

## 输出格式

stdout 输出一个 JSON 对象,退出码 0 表示 PASS,1 表示 FAIL:

```json
{
  "ok": true,
  "request": {
    "method": "POST",
    "url": "http://novel.hctestedu.com/user/login",
    "headers": {"x-requested-with": "XMLHttpRequest", "content-type": "..."},
    "body_params": {"username": "13800138001", "password": "123456"}
  },
  "response": {
    "status_code": 200,
    "body_json": {"code": "200", "msg": "SUCCESS", "data": {"token": "abc..."}}
  },
  "assertions": [
    {"assertion": "响应状态码：200", "ok": true, "detail": "expected=200, got=200"},
    {"assertion": "响应 code 等于 \"200\"", "ok": true, "detail": "code=200"},
    {"assertion": "响应 msg 包含\"SUCCESS\"", "ok": true, "detail": "msg contains 'SUCCESS'"},
    {"assertion": "响应 data.token 存在", "ok": true, "detail": "data.token=abc..."},
    {"assertion": "响应 data.token 应为非空字符串", "ok": true, "detail": "non-empty str"}
  ]
}
```

## 支持的断言模式

`expected:` 列表里每条自然语言字符串用正则匹配(大小写不敏感):

| 模式 | 例子 | 检查 |
|---|---|---|
| `响应状态码：N` | `响应状态码：200` | `status_code == 200` |
| `响应 <path> 等于 "X"` | `响应 code 等于 "200"` | `json[code] == "200"` |
| `响应 <path> 包含"X"` | `响应 msg 包含"SUCCESS"` | `"SUCCESS" in str(json[msg])` |
| `响应 <path> 存在` | `响应 data.token 存在` | `json[path]` 不是 `None` |
| `响应 <path> 应为非空字符串` | `响应 data.token 应为非空字符串` | `isinstance(str) and len>0` |

不支持的断言模式会被跳过(返回 `ok: true, detail: "skip(...)"`)。

## 完整工作流

1. **读 case 详情**:
   ```bash
   Read AI-自动化测试用例/api/<case_id>.yaml
   ```
   或 helper 内部通过 `--project` 自动读取(走 `_index.yaml` 索引)。

2. **准备 `--ctx`**:
   - 从 task.input_datas 的每条 `{name, value}` 取 `name` 和 Jinja2 渲染后的 `value`
   - 从之前 task 的 outputs 里取已暴露的变量
   - 把所有 name→value 拼成一个 JSON dict

3. **调用 helper**(含中文 key/value 时必须用文件):
   ```bash
   # 写 ctx.json
   python -c "import json; json.dump({...}, open(r'C:/temp/ctx.json','w',encoding='utf-8'), ensure_ascii=False)"
   # 调 helper
   python <skill-dir>/bigbear_api_cli.py execute --project <root> --case-id <id> --ctx-file C:/temp/ctx.json
   ```

4. **读取 stdout JSON**,解析 `ok` 字段。

5. **按统一格式回报**:
   ```
   --- TASK OUTPUT ---
   (无)
   --- TASK STATUS ---
   PASS
   响应 status=200,所有 5 条断言通过
   ```
   或
   ```
   --- TASK OUTPUT ---
   (无)
   --- TASK STATUS ---
   FAIL
   <失败的断言 + detail>
   ```

## 失败处理

- helper 进程退出码非 0 → `ok: false`
- 任何一条断言 `ok: false` → 整条 task FAIL
- 读取 case yaml 失败 / 渲染失败 / 请求超时 → 都返回 `ok: false` + `error` 字段