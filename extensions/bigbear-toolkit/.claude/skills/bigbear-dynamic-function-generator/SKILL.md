---
name: bigbear-dynamic-function-generator
description: AI 自动化流程中动态生成符合 AIQE 规范的动态函数文件。当 AI 需要在流程中创建可被节点调用的函数时，当用户要求 AI 创建动态函数、自动化函数、workflow 函数时，或流程执行时需要动态生成工具函数时，都应使用此 Skill。AI 会直接在指定工作区目录下编辑文件，无需通过界面操作。
enabled: true
---
重点： 请使用中文沟通！！

# AI 动态函数生成器

在 AI 自动化流程执行过程中，直接在工作区创建符合规范的动态函数文件。

> **执行边界：** 本 Skill 负责动态函数文件的生成规范，不负责为测试计划拼接
> shell 命令。`bigbear-ai-test-runner` 执行已有 dynamic-function Task 时必须调用
> `run_dynamic_function` 工具；不得使用 Bash、Write/Edit、wrapper、context.json
> 或 bat 文件替代。该工具会自动注入计划环境变量，并通过 stdin 传递 Flow outputs。

---

## 🎯 我该怎么用这个技能？

> **如果你是第一次使用，先读这一节。** 后面的「参考手册」是给需要查细节时用的。

### 三种使用模式

| 模式 | 适用场景 | 引导程度 | 触发方式 |
|------|---------|---------|---------|
| **跳过模式** | 你已经知道 function_type / function_code / 用途三个关键信息 | 0 个问题 | 用户一句话说清楚时自动进入 |
| **快速补全** | 只缺 1-2 个关键信息 | 1-2 个问题 | 启发式判断后自动进入 |
| **场景向导** | 完全没头绪 / 说"我不会做" | 4-6 个问题 | 启发式判断后自动进入 |

### 启发式判断规则（AI 自动执行）

AI 收到请求后会提取三个关键信号：

1. **`function_code` 是否明确** —— 例：`query_user_info`、`http_login`
2. **`function_type` 是否明确** —— 例：`数据库查询`、`通用工具`
3. **用途是否清楚** —— 例："查询用户信息"、"调用登录接口"

判定：

- ✅ **三个都给齐** → 跳过模式，直接生成文件
- ⚠️ **只缺 1-2 个** → 快速补全模式，只问缺失的那 1-2 项
- ❌ **三个都缺 / 用户说"我不会" / 描述模糊** → 场景向导模式，按下面分叉问

### 随时退出

在引导的任何一步，你都可以说：

- **"跳过"** —— 立即按已有信息生成文件，缺失字段留空
- **"我自己来"** —— 退出引导，给你一个空白模板
- **"先这样"** —— 用当前信息先生成，回头再改

---

## 📋 场景向导：5 个常见场景分叉

> 这是「场景向导」模式的具体提问清单。AI 会先问你属于哪个场景，然后只问 4-6 个关键问题。

### 场景 A：数据库查询 🗄️

**典型用途**：连 MySQL 查数据、读配置、批量更新

**AI 会问你**：
1. 库表定位 —— `SQL` 语句还是"按表+条件"自动拼？
2. 连接配置 —— 走环境变量（推荐）还是函数参数传入？
3. 查询/返回哪些字段？
4. 输出是单行、多行、还是聚合结果？

**典型 function_type**：`数据库查询`
**典型 params**：`sql` 或 `table_name`+`where_clause`
**典型 outputs**：`rows` / `count` / `first_row`

**模板示例**：[数据库查询/query_user_info.py](../../AI-动态函数管理/数据库查询/query_user_info.py)

---

### 场景 B：HTTP / API 调用 🌐

**典型用途**：调登录接口、请求第三方 API、文件上传下载

**AI 会问你**：
1. base_url 放哪 —— 环境变量（推荐）还是函数参数？
2. 请求方法 —— GET / POST / 其它？
3. 入参在 query、body、还是 header？
4. 鉴权方式 —— 无 / Bearer Token / Cookie / 自定义 Header？
5. 返回什么 —— 整个响应体、提取特定字段、还是状态码？

**典型 function_type**：`API调用`
**典型 params**：`url` / `method` / `headers` / `body` / `params`
**典型 outputs**：`response` / `status_code` / `extracted_field`

---

### 场景 C：通用工具 🛠️

**典型用途**：生成随机字符串、获取固定配置、日期格式化、文件读取

**AI 会问你**：
1. 输入是什么、要做什么处理？
2. 输出是什么格式（字符串 / 数字 / dict）？
3. 有没有现成的"输入 → 输出"映射逻辑？

**典型 function_type**：`通用工具`
**典型 params**：按业务自定义
**典型 outputs**：按业务自定义

**模板示例**：[通用工具/get_login_info.py](../../AI-动态函数管理/通用工具/get_login_info.py)

---

### 场景 D：数据处理 📊

**典型用途**：JSON 解析、字符串清洗、Excel 读写、数据转换、批量处理

**AI 会问你**：
1. 输入数据格式 —— 字符串 / JSON / 文件路径 / 列表？
2. 处理逻辑 —— 解析 / 清洗 / 转换 / 聚合？
3. 输出去向 —— 返回 dict / 写文件 / 打印？
4. 是否需要 pandas / openpyxl 这类数据处理库？

**典型 function_type**：`数据处理`
**典型 params**：`input_data` / `field_mapping` / `output_format`
**典型 outputs**：`processed_data` / `record_count` / `output_path`

**模板示例**：见下方「参考手册」中的 `parse_json_response.py`

---

### 场景 E：其它 / 不确定 🎲

**AI 会问你**：
1. 一句话描述这个函数要做什么？
2. 输入从哪来 —— 用户传、文件读、还是 _context 里拿？
3. 输出给谁用 —— 下一个节点？日志？写文件？
4. 有没有现成的库可以用？

**典型 function_type**：根据回答新建一个类型目录（如 `邮件通知`、`文件操作`）

---

## 🚪 生成后的回退与修改

生成完文件后：

- **想改字段** —— 直接说"把 outputs 的 xxx 字段类型改成 number"，AI 会重新生成文件
- **想加参数** —— 说"加一个 param：name=timeout，type=number，default=30"
- **想换类型目录** —— AI 会创建新目录并把文件移过去
- **想删除** —— 告诉 AI 删除，它会从文件系统直接删除
- **想看现有函数** —— 让 AI 读 `AI-动态函数管理/{type}/` 目录，列出所有函数

---

# 📚 参考手册（详细规范）

> 下面是和 AIQE 动态函数相关的所有规范细节。生成文件过程中如有疑问，AI 会从这里查证。

## 文件路径规范

```
AI-动态函数管理/{function_type}/{function_code}.py
```

- AI-动态函数管理： 这是统一存放动态函数的文件夹
- `function_type`: 函数类型目录，如 `通用工具`、`数据处理`、`API调用` 等
- `function_code`: 函数代码，同时也是文件名（不含 .py 后缀）

## 文件格式

每个动态函数文件包含两部分：**元数据行** + **代码体**

```python
# AIQE_DYNAMIC_FUNCTION_META {"function_code": "xxx", "function_type": "xxx", ...}

def execute(**kwargs):
    """函数说明..."""
    ...
```

## 元数据格式

元数据是 JSON 格式，放在文件第一行 `# AIQE_DYNAMIC_FUNCTION_META ` 之后：

| 字段          | 类型   | 必填 | 说明                                                          |
| ------------- | ------ | ---- | ------------------------------------------------------------- |
| function_code | string | 是   | 函数代码，字母/下划线开头，数字不能开头。例：`http_request` |
| function_type | string | 是   | 函数类型，对应文件夹名。例：`通用工具`                      |
| function_name | string | 是   | 函数名称，用于展示。例：`HTTP请求`                          |
| description   | string | 否   | 函数说明                                                      |
| enabled       | bool   | 否   | 是否启用，默认 `true`                                       |
| params        | array  | 否   | 输入参数表                                                    |
| outputs       | array  | 否   | 规则输出表                                                    |

### params 元素格式

```json
{"key": "token", "name": "访问令牌", "value_type": "string", "required": true, "default_value": "", "description": "", "test_value": ""}
```

| 字段          | 类型   | 必填 | 说明                      |
| ------------- | ------ | ---- | ------------------------- |
| key           | string | 是   | 参数代码                  |
| name          | string | 否   | 参数名称                  |
| value_type    | string | 否   | 参数类型，默认 `string` |
| required      | bool   | 否   | 是否必填，默认 `false`  |
| default_value | string | 否   | 默认值                    |
| description   | string | 否   | 参数说明                  |
| test_value    | string | 否   | 测试值                    |

> **特殊参数：** `_context` 是系统自动传入的运行时上下文信息 JSON 字符串，无需在 params 中定义即可通过 `kwargs.get("_context", "")` 获取。

### outputs 元素格式

```json
{"key": "result", "name": "执行结果", "value_type": "string", "description": ""}
```

| 字段        | 类型   | 必填 | 说明                      |
| ----------- | ------ | ---- | ------------------------- |
| key         | string | 是   | 输出代码                  |
| name        | string | 否   | 输出名称                  |
| value_type  | string | 否   | 输出类型，默认 `string` |
| description | string | 否   | 输出说明                  |

## 代码体规范

- 必须包含 `execute(**kwargs)` 函数作为入口
- `kwargs` 接收流程传入的所有参数
- 返回值应为 `dict`，包含 `outputs` 中定义的输出键
- 所有用到的模块（标准库 + 第三方库）都必须在函数体内**显式 import**，不得依赖外部已导入的命名空间（详见下方「包引入管理」）

### 包引入管理

动态函数运行在隔离的 Python 沙箱中，**函数体外没有任何自动注入的包**。所有用到的模块都必须显式 import，不能假设 `import xxx` 已经被别处执行，也不能依赖模块顶层已存在的变量。

#### 规范

1. **import 集中放在 `execute` 函数体顶部**：在函数最前面一次性引入全部依赖，不要散落在中间；**不要写到文件顶层**（`def execute` 之外），避免污染模块命名空间。
2. **每个用到的模块都要 import**：包括标准库（`json` / `re` / `os` / `sys` / `time` / `hashlib` / `base64` / `datetime` / `urllib.parse` 等）。例如代码里出现 `sys.argv`，就一定要 `import sys`；出现 `time.sleep` 就一定要 `import time`。
3. **第三方库用 `try/except ImportError` 保护**：运行环境未必预装了 `pymysql` / `requests` / `pandas` 等，捕获后给出合理的回退返回。
4. **禁止隐式依赖**：不要写 `from somewhere import something` 然后假设该包已在某处被加载过；不允许出现"动态函数 a 里 import 过了，所以动态函数 b 里不用再 import"这种隐式约定。
5. **import 顺序**：先标准库 → 再第三方库 → 再本地模块，每组之间空一行（可选但推荐）。

### 异常处理规范（重要）

动态函数的业务逻辑必须用 **`try / except / finally`** 整体包裹，且遵循以下原则：

1. **不要设置默认值**：当业务逻辑出现异常时，禁止返回 `""`、`0`、`None`、`False`、`{}`、`[]` 之类的占位默认值来"假装执行成功"。默认值会掩盖真实错误，导致上层流程拿到错误结果还继续往下走。
2. **必须抛出异常信息**：捕获到异常后应使用 `raise` 重新抛出（或抛出更具体的异常类型），让调用方清楚地知道"哪里、为什么失败"。
3. **`finally` 用于资源清理**：连接、文件句柄、临时对象等无论成功还是异常都要释放，统一放在 `finally` 中。
4. **ImportError 也属于异常**：第三方库缺失时同样要 `raise` 抛出，不要 `return {"error": ...}` 后继续往下走。
5. **校验失败也走异常**：参数缺失、类型不对、业务规则不满足等场景，使用 `raise ValueError(...)` / `raise TypeError(...)` 等显式抛出。

#### 推荐模板

```python
def execute(**kwargs):
    """函数说明"""
    # 标准库
    import json
    import sys
    import re
    import time
    import hashlib
    import traceback
    from datetime import datetime

    # 第三方库（必须 try/except ImportError 保护）
    try:
        import pymysql
    except ImportError as e:
        raise ImportError(f"pymysql 未安装，请先 pip install pymysql: {e}") from e

    try:
        import requests
    except ImportError as e:
        raise ImportError(f"requests 未安装，请先 pip install requests: {e}") from e

    # 业务逻辑（try/except/finally 整体结构）
    conn = None
    try:
        # --- 参数校验（失败就 raise） ---
        if not kwargs.get("required_param"):
            raise ValueError("required_param 不能为空")

        # --- 业务执行 ---
        conn = pymysql.connect(...)
        result = do_something(conn)
        return {"result": result}
    except Exception:
        # 出现异常不要设置默认值，直接把异常信息抛给调用方
        raise
    finally:
        # 无论成功还是异常，都要释放资源
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# === CLI 入口（必加，不能省）===========================================
# runner 的 `run_dynamic_function` 工具会用参数数组启动当前 Python 解释器,
# 并把 UTF-8 JSON 通过 stdin 传给 `<脚本路径> --_context-stdin`,
# 所以每个动态函数文件**必须**自带 `if __name__ == "__main__":` 块,
# 否则 `python` 跑这个文件不会有任何输出(只 import 了 execute 然后退出)。
# 下面这段是固定模板,直接复制到文件末尾即可,不要修改。
#
# **为什么用 `--_context-stdin` 而不是 `--_context "<json>"`?**
# stdin 能原样传输 JSON 字节,同时规避 shell 引号和系统默认编码差异。
if __name__ == "__main__":
    import argparse
    import json
    import sys
    import traceback

    parser = argparse.ArgumentParser(description="AIQE 动态函数执行入口")
    parser.add_argument(
        "--_context",
        default="",
        help="运行时上下文 JSON 字符串(命令行直接传,简单场景用)",
    )
    parser.add_argument(
        "--_context-stdin",
        action="store_true",
        help="从 stdin 读取运行时上下文 JSON(推荐,避免 shell 引号嵌套问题)",
    )
    # parse_known_args:除已注册选项外,允许透传任意 --key value 给 execute(**kwargs)
    _parsed, _extras = parser.parse_known_args()

    if _parsed._context_stdin:
        try:
            _context_str = sys.stdin.read()
        except Exception as _e:
            raise RuntimeError(f"从 stdin 读取 _context 失败:{_e}") from _e
    else:
        _context_str = _parsed._context

    _kwargs: dict = {"_context": _context_str}
    _i = 0
    while _i < len(_extras):
        _arg = _extras[_i]
        if not _arg.startswith("--"):
            raise ValueError(
                f"不支持的位置参数 {_arg!r},请使用 --key value 形式"
            )
        _key = _arg[2:]
        if not _key:
            raise ValueError(f"参数名不能为空:{_arg!r}")
        if _i + 1 < len(_extras) and not _extras[_i + 1].startswith("--"):
            _kwargs[_key] = _extras[_i + 1]
            _i += 2
        else:
            # 布尔型标记:只传 --flag,不接 value
            _kwargs[_key] = ""
            _i += 1

    try:
        _result = execute(**_kwargs)
        print(json.dumps(_result, ensure_ascii=False))
    except SystemExit:
        raise
    except Exception as _e:
        # 诊断信息走 stderr,stdout 仍保持干净,调用方用 returncode 区分成功/失败
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"error": str(_e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
# === CLI 入口结束 =====================================================
```

> **为什么必须有 `__main__` 块？** `run_dynamic_function` 会直接启动这个 .py 文件,通过 stdin 注入上下文,再从 stdout 解析 JSON。如果文件里只有 `def execute(**kwargs)`,`python` 解释器执行完文件不会产生结果。`__main__` 块负责把 stdin JSON 喂给 `execute`,并把返回 dict JSON 化后输出。

#### 异常处理反例（不要这样写）

```python
# ❌ 反例 1：异常被吞掉，返回默认值
try:
    data = json.loads(json_str)
except json.JSONDecodeError:
    data = {}        # 错误！默认值掩盖了解析失败
    return {"data": data}

# ❌ 反例 2：捕获后只 return error 字段，继续走成功分支
try:
    result = api.call()
except Exception as e:
    return {"error": str(e)}   # 错误！调用方可能只读 result 字段

# ❌ 反例 3：缺包也不抛，只置 None 继续运行
try:
    import pandas
except ImportError:
    pandas = None    # 错误！后面用到 pandas 时会报 NoneType 错误，信息更模糊
```

#### AI 生成完函数后的自检清单

**写完代码必须逐项核对，否则不予提交：**

- [ ] 函数体内实际用到的每一个模块（包括 `sys` / `os` / `re` / `time` / `hashlib` / `base64` / `datetime` / `urllib` 等标准库）都写了对应 `import`？
- [ ] 第三方库（`pymysql` / `requests` / `pandas` / `openpyxl` 等）都包了 `try/except ImportError`，且**直接 `raise` 抛出**，没有 `return {"error": ...}` 或置 `None` 后继续？
- [ ] 所有 import 都集中在 `execute` 函数体顶部，**没有**写到 `def execute` 之外？
- [ ] 没有出现"假设别处已经 import 过"的隐式依赖？
- [ ] 没有任何用到的名字（变量/函数/常量）找不到 import 来源？
- [ ] 业务逻辑是否被 `try / except / finally` 整体包裹？
- [ ] `except` 中是否使用 `raise` 把异常信息抛出，**没有**用 `return {}` / `return ""` / `return False` 等默认值代替？
- [ ] 资源（连接、文件、临时文件等）是否在 `finally` 中释放？
- [ ] **文件末尾是否包含 `if __name__ == "__main__":` CLI 入口块**（否则 agent `python` 调用无输出,task 直接 FAIL）？

### 运行时上下文信息

函数代码中获取运行时上下文信息的方式为 `kwargs.get("_context", "")`，这是一个 JSON 字符串，解析后得到 `context` 字典，包含当前流程执行的上下文信息（如租户、用户、流程参数、节点输出等）。

**基础示例：**

```python
def execute(**kwargs):
    """使用运行时上下文信息的示例函数"""
    import json

    try:
        _context_str = kwargs.get("_context", "")
        if not _context_str:
            raise ValueError("_context 缺失，无法获取运行时上下文")

        context = json.loads(_context_str)
        if not isinstance(context, dict):
            raise TypeError(f"_context 解析后必须是 dict，实际为 {type(context).__name__}")

        user_id = context.get("user_id", "")
        tenant_id = context.get("tenant_id", "")
        flow_params = context.get("flow_params", {})

        if not user_id:
            raise ValueError("context 中缺少 user_id")

        # 使用上下文信息进行操作
        ...
    except Exception:
        # 直接把异常信息抛出，不要设置默认值
        raise
    finally:
        pass
```

> 注意：`kwargs` 中的 `_context` 是函数运行时的上下文信息，不是操作系统的环境变量。

### 环境变量读取方式

`AI-环境变量/<name>/env_var.yaml` 中定义的每个变量，在运行时会被**平铺注入到 `context` 顶层**（不是嵌套在 `env_vars` 子对象里），与 yaml 键一一对应。例如 yaml 中有：

```yaml
DB_HOST: localhost
DB_NAME: novel_plus
api_project_url: http://novel.hctestedu.com
```

则 `context["DB_HOST"] == "localhost"`，`context["DB_NAME"] == "novel_plus"`，`context["api_project_url"] == "http://novel.hctestedu.com"`，**直接用 `context.get("DB_HOST", "localhost")` 即可**，不要再额外做嵌套查找。

**读取环境变量示例：**

```python
def execute(**kwargs):
    """读取环境变量中的数据库配置，查询用户信息"""
    import json

    conn = None
    try:
        _context_str = kwargs.get("_context", "")
        if not _context_str:
            raise ValueError("_context 缺失，无法获取环境变量")

        context = json.loads(_context_str)

        # 缺少必填环境变量时直接 raise，不要用默认值掩盖
        db_host = context.get("DB_HOST")
        if not db_host:
            raise ValueError("环境变量 DB_HOST 未配置")

        db_name = context.get("DB_NAME")
        if not db_name:
            raise ValueError("环境变量 DB_NAME 未配置")

        db_user = context.get("DB_USER")
        if not db_user:
            raise ValueError("环境变量 DB_USER 未配置")

        # 可选变量有合理兜底，没有也不致命
        db_port_str = context.get("DB_PORT", "3306")
        try:
            db_port = int(db_port_str)
        except (TypeError, ValueError):
            raise ValueError(f"环境变量 DB_PORT 必须是整数，实际为 {db_port_str!r}") from None

        db_password = context.get("DB_PASSWORD", "")

        # 接下来用 db_host / db_port / db_name / db_user / db_password 连接数据库即可
        ...
    except Exception:
        # 直接把异常信息抛出，不设置默认值
        raise
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
```

> 写代码前可以先读 `AI-环境变量/<name>/env_var.yaml` 了解有哪些变量可用，但取值时**必须直接 `context.get(...)`，不要走任何嵌套结构**。

## 创建函数步骤

1. **确定函数类型目录**：根据函数用途选择或创建类型目录（如 `通用工具`）
2. **确定函数代码**：使用有意义的英文名，以下划线分隔，如 `parse_json_response`
3. **编写元数据 JSON**：按照上述格式编写
4. **编写代码体**：实现 `execute(**kwargs)` 函数
5. **添加 CLI 入口（必做）**：在文件末尾追加 `if __name__ == "__main__":` 块，使用上文「推荐模板」里的固定模板，让 `python <脚本> --_context '<json>'` 能直接跑出 JSON 结果。**缺这步 agent 调用会失败**。
6. **写入文件**：创建 `{function_code}.py` 文件

## 示例

### 创建文件：数据处理/parse_json_response.py

```python
# AIQE_DYNAMIC_FUNCTION_META {"function_code": "parse_json_response", "function_type": "数据处理", "function_name": "JSON响应解析", "description": "解析JSON格式的API响应，提取指定字段", "enabled": true, "params": [{"key": "json_str", "name": "JSON字符串", "value_type": "string", "required": true, "default_value": "", "description": "待解析的JSON字符串", "test_value": "{\"code\": 200, \"data\": {\"name\": \"test\"}}"}, {"key": "field_path", "name": "字段路径", "value_type": "string", "required": false, "default_value": "data", "description": "要提取的字段路径，支持点号分隔", "test_value": "data.name"}], "outputs": [{"key": "extracted_value", "name": "提取值", "value_type": "string", "description": "从JSON中提取的值"}, {"key": "parse_success", "name": "解析状态", "value_type": "boolean", "description": "是否解析成功"}]}

def execute(**kwargs):
    """解析JSON响应，提取指定字段。"""
    import json

    # 业务逻辑用 try/except/finally 整体包裹
    try:
        # --- 参数校验（失败直接 raise，不设置默认值） ---
        json_str = kwargs.get("json_str", "")
        if not json_str:
            raise ValueError("json_str 不能为空")

        field_path = kwargs.get("field_path", "data")
        if not field_path:
            raise ValueError("field_path 不能为空")

        # --- 业务执行 ---
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise TypeError(f"JSON 顶层必须是对象，实际为 {type(data).__name__}")

        value = data
        for key in field_path.split("."):
            if not isinstance(value, dict):
                raise TypeError(f"无法在 {type(value).__name__} 类型上访问字段 '{key}'")
            if key not in value:
                raise KeyError(f"字段路径 '{field_path}' 在 JSON 中不存在")
            value = value[key]

        return {"extracted_value": str(value), "parse_success": True}
    except Exception:
        # 出现异常不要设置默认值（如 {"extracted_value": "", "parse_success": False}），
        # 直接把异常信息抛给调用方
        raise
    finally:
        # 资源清理（无外部资源时留空即可，但结构保留）
        pass


# === CLI 入口(必加,直接复用上文「推荐模板」里的固定代码) ===
if __name__ == "__main__":
    import argparse
    import json
    import sys
    import traceback

    parser = argparse.ArgumentParser(description="AIQE 动态函数执行入口")
    parser.add_argument(
        "--_context",
        default="",
        help="运行时上下文 JSON 字符串(命令行直接传,简单场景用)",
    )
    parser.add_argument(
        "--_context-stdin",
        action="store_true",
        help="从 stdin 读取运行时上下文 JSON(推荐,避免 shell 引号嵌套问题)",
    )
    _parsed, _extras = parser.parse_known_args()

    if _parsed._context_stdin:
        try:
            _context_str = sys.stdin.read()
        except Exception as _e:
            raise RuntimeError(f"从 stdin 读取 _context 失败:{_e}") from _e
    else:
        _context_str = _parsed._context

    _kwargs: dict = {"_context": _context_str}
    _i = 0
    while _i < len(_extras):
        _arg = _extras[_i]
        if not _arg.startswith("--"):
            raise ValueError(f"不支持的位置参数 {_arg!r},请使用 --key value 形式")
        _key = _arg[2:]
        if not _key:
            raise ValueError(f"参数名不能为空:{_arg!r}")
        if _i + 1 < len(_extras) and not _extras[_i + 1].startswith("--"):
            _kwargs[_key] = _extras[_i + 1]
            _i += 2
        else:
            _kwargs[_key] = ""
            _i += 1

    try:
        _result = execute(**_kwargs)
        print(json.dumps(_result, ensure_ascii=False))
    except SystemExit:
        raise
    except Exception as _e:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"error": str(_e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
```

## 验证规则

- `function_code` 必须是有效的 Python 变量名：`^[A-Za-z_]\w*$`
- 文件第一行必须是 `# AIQE_DYNAMIC_FUNCTION_META {...}`
- 代码体必须包含 `execute(**kwargs)` 函数定义
- 文件末尾必须包含 `if __name__ == "__main__":` 块（否则 agent `python` 调用无输出,直接 FAIL）
- 同一类型目录下不能有重复的 `function_code`
- `params` 和 `outputs` 中的 `key` 不能重复

## 常见错误处理

- 如果类型目录不存在，先创建目录
- 如果函数已存在，应更新而非重复创建
- JSON 元数据中的引号应使用双引号，字符串值需要转义
- 代码体语法错误会导致函数执行失败，写入前应检查
