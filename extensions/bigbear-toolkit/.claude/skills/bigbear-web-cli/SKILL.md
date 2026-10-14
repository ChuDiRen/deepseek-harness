---
name: bigbear-web-cli
description: Use when working with browser automation, web scraping, Playwright control, or mentions "bigbear-web", "web cli", "playwright", "浏览器自动化".
version: 1.0.8
---

# BigBear Web CLI

AI-powered browser control via Playwright CDP and vision AI.

## 核心原则

### 1. 页面分析策略（重要）

**不要每一步都执行** **`get`** **查看页面**，正确流程：

1. 分析一次页面后，记忆当前页面有哪些可执行步骤
2. 执行完这几个步骤后，再用 `get` 查看最新页面状态
3. 仅在**元素找不到**或**需要确认页面内容**时才使用 `get`

### 2. 并发执行原则（重要）

**同一页面的多个独立操作应并行执行**，而非等待上一个完成再执行下一个：

- 登录表单的用户名、密码、验证码输入可以并行
- 表单填写的多个字段可以并行
- 多个 bigbear-web-cli 进程可同时连接同一个 CDP 端口，各自独立 AI 识别

### 4. 检查策略（重要）

**batch 命令执行后必须用** **`get`** **验证**，普通 click/input 仅在异常时检查。

#### batch 命令 → 必须检查

```bash
# batch 执行完成后验证表单填写结果
bigbear-web-cli --port 9222 batch input 用户名::admin input 密码::123456 click 登录按钮
bigbear-web-cli --port 9222 get "登录表单区域的内容"  # 验证填写是否正确
```

#### 普通 click/input → 仅在异常时检查

以下情况才使用 `get` 检查：

- 元素找不到、AI 识别失败
- 操作后页面没有预期变化（如下拉框未展开、弹窗未出现）
- 需要确认当前页面内容才能执行下一步
- 业务逻辑需要验证结果（如提交后检查是否成功）

```bash
# 异常情况示例
[FAIL] 元素未找到 → 使用 get 确认页面状态后重试
bigbear-web-cli --port 9222 click "添加员工按钮"
bigbear-web-cli --port 9222 get "对话框内容区域"  # 确认弹窗是否出现
bigbear-web-cli --port 9222 click "添加员工按钮" --enhanced "表格顶部右侧的按钮"

# 业务结果验证
bigbear-web-cli --port 9222 click "立即提交按钮"
bigbear-web-cli --port 9222 get "员工列表表格内容"  # 验证新员工是否在列表中
```

## Usage

```bash
# 启动/连接浏览器
bigbear-web-cli --port 9222 start

# 打开网址
bigbear-web-cli --port 9222 navigate https://www.example.com
bigbear-web-cli --port 9222 navigate https://www.example.com -s screenshot.png

# AI 分析页面
bigbear-web-cli --port 9222 get "验证码区域的内容"

# AI 点击元素
bigbear-web-cli --port 9222 click "登录按钮"
bigbear-web-cli --port 9222 click "搜索框" --enhanced "页面顶部的搜索输入框"
bigbear-web-cli --port 9222 click "确认按钮" -s click_after.png

# AI 输入文本
bigbear-web-cli --port 9222 input "搜索框" "关键词"
bigbear-web-cli --port 9222 input "用户名" "admin" --enhanced "在登录表单顶部"
bigbear-web-cli --port 9222 input "密码" "mypassword" -s input_after.png

# 滚动页面
bigbear-web-cli --port 9222 scroll down
bigbear-web-cli --port 9222 scroll up -c 5
bigbear-web-cli --port 9222 scroll down --x 400 --y 300
bigbear-web-cli --port 9222 scroll right --count 3 -s scrolled.png
bigbear-web-cli --port 9222 scroll right --region "右侧列表" -c 3

# 截图
bigbear-web-cli --port 9222 screenshot output.png

# 关闭当前页面
bigbear-web-cli --port 9222 close

# 批量并行输入/点击（一次截图，多元素并行AI识别后逐个执行）
bigbear-web-cli --port 9222 batch input 用户名::admin input 密码::123456 click 记住登录
bigbear-web-cli --port 9222 batch input 搜索框::关键词 click 搜索按钮 -s result.png

# 无头模式
bigbear-web-cli --headless --port 9222 navigate https://www.example.com

# 调试模式（显示各步骤耗时统计）
bigbear-web-cli --port 9222 --debug click "登录按钮"
```

## Parameters

| Parameter  | Description        | Default |
| ---------- | ------------------ | ------- |
| --port, -p | Chrome DevTools 端口 | 9222    |
| --headless | 无头模式运行             | false   |
| --browser-path, -b | Chrome/Chromium 可执行文件路径，未指定时使用 Playwright 内置 chromium | 自动 |
| --debug    | 调试模式，显示各步骤耗时统计     | false   |

## Command Parameters

### click / input

| Parameter        | Description |
| ---------------- | ----------- |
| element          | 元素描述（必填）    |
| --enhanced, -e   | 元素查找加强说明    |
| --screenshot, -s | 操作后保存截图路径   |

### scroll

| Parameter        | Description             |
| ---------------- | ----------------------- |
| direction        | 滚动方向：up/down/left/right |
| --region         | AI识别区域描述，滚动前先聚焦到该区域     |
| --count, -c      | 滚动次数                    |
| --screenshot, -s | 操作后保存截图路径               |

### navigate

| Parameter        | Description |
| ---------------- | ----------- |
| url              | 目标网址（必填）    |
| --screenshot, -s | 操作后保存截图路径   |

### screenshot

| Parameter | Description |
| --------- | ----------- |
| output    | 截图保存路径（必填）  |

### batch

| Parameter        | Description                                 |
| ---------------- | ------------------------------------------- |
| instructions     | 批量指令，格式 `click 描述 \| input 描述::值 ...`，可指定多个 |
| --screenshot, -s | 操作后保存截图路径                                   |

### url / title

| Parameter | Description                                                  |
| --------- | ------------------------------------------------------------ |
| --format  | 输出格式：`text`（默认，单行）或 `json`（`{"url": "...", "title": "..."}`） |

**用途**：读取浏览器当前页面的 URL 与标题（只读，不需要 AI 识别），常用于断言/日志。例如：

```bash
bigbear-web-cli url                       # 单行：当前页面 URL
bigbear-web-cli title                     # 单行：当前页面 title
bigbear-web-cli url --format json         # {"url": "...", "title": "..."}
```

## Environment Variables

支持 `.env` 文件配置：

```bash
# AI API 配置
WEB_AUTOMATION_AI_API_KEY=your_api_key_here
WEB_AUTOMATION_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
WEB_AUTOMATION_AI_MODEL=qwen3.6-flash-2026-04-16

# 浏览器数据目录（用于保持会话、Cookie等）
WEB_AUTOMATION_USER_DATA=/path/to/browser/data/directory

# 浏览器可执行文件路径（可选，未设置时使用 Playwright 内置 chromium）
# 仅支持 Chrome/Chromium 系（不支持 Firefox）
# Windows: WEB_AUTOMATION_BROWSER_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
# macOS:   WEB_AUTOMATION_BROWSER_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
# Linux:   WEB_AUTOMATION_BROWSER_PATH=/usr/bin/google-chrome
# WEB_AUTOMATION_BROWSER_PATH=
```

或设置环境变量：

```bash
export WEB_AUTOMATION_AI_API_KEY=your_api_key_here
export WEB_AUTOMATION_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export WEB_AUTOMATION_AI_MODEL=qwen3.6-flash-2026-04-16
export WEB_AUTOMATION_USER_DATA=/path/to/browser/data/directory
export WEB_AUTOMATION_BROWSER_PATH=/path/to/chrome  # 可选
```

> **注意**：使用前必须配置 `WEB_AUTOMATION_AI_API_KEY`（AI API密钥）。`WEB_AUTOMATION_USER_DATA` 用于指定浏览器数据目录，未指定时默认使用当前工作目录下的 `user_data` 目录。`WEB_AUTOMATION_BROWSER_PATH` 用于指定 Chrome/Chromium 可执行文件路径，未指定时使用 Playwright 内置 chromium。

## ⚠️ 调用本 skill 前的环境前置检查（必须执行）

**AI 在调用任何 `bigbear-web-cli` 命令之前，必须先做以下检查；任何一项不通过就停下来让用户提供，不要继续执行，也不要在缺 Key 情况下反复重试。**

### 1. AI Key 是否就绪

`bigbear-web-cli` 的所有 `get` / 视觉识别 / 元素定位 / `--enhanced` 类命令都依赖 AI 模型。如果 AI Key 缺失，**每一条 `get` / 视觉命令都会立刻报**：

```
[FAIL] 错误: 请设置 AI_API_KEY 环境变量或在 .env 文件中配置
```

**Key 的两个读取来源**（任一即可，按优先级）：

1. **进程环境变量**（最高优先级）：`AI_API_KEY` / `AI_BASE_URL` / `AI_MODEL`，或 `WEB_AUTOMATION_AI_API_KEY` / `WEB_AUTOMATION_AI_BASE_URL` / `WEB_AUTOMATION_AI_MODEL`
2. **`<cwd>/.env` 文件**：`python-dotenv` 自动加载当前工作目录下的 `.env`（不会覆盖系统环境变量）

**快速检查命令**（Windows PowerShell）：

```powershell
# A. 看进程环境变量
Get-Item Env:AI_API_KEY -ErrorAction SilentlyContinue
Get-Item Env:WEB_AUTOMATION_AI_API_KEY -ErrorAction SilentlyContinue

# B. 看当前工作目录的 .env
Test-Path .\.env; if (Test-Path .\.env) { Get-Content .\.env }
```

**不通过时标准动作**：

- ❌ 不要直接 `bigbear-web-cli --port 9222 get ...` 然后看 `请设置 AI_API_KEY` 再回头补
- ❌ 不要让 agent 在缺 Key 情况下空转重试 90+ 条命令
- ✅ 直接告诉用户："缺少 AI_API_KEY，请补到 `<cwd>/.env` 或注入系统环境变量"
- ✅ 等用户补完再继续

### 2. 浏览器数据目录

`WEB_AUTOMATION_USER_DATA` 未设置时默认用 `<cwd>/user_data`。**目录不存在就自动创建**(`mkdir -p`)，不需要停下来让用户提供 —— 这是浏览器持久化数据的本地目录，没有任何风险。创建后即可继续。

### 3. Chrome / Chromium 是否可用

未设置 `WEB_AUTOMATION_BROWSER_PATH` 时会探测：

- Playwright 内置 chromium
- 系统 PATH 中的 chrome/chromium
- 已知安装路径

**快速检查**：

```bash
bigbear-web-cli --port 9222 start   # 启动成功就 OK，失败看错误信息
```

### 4. 端口 9222 是否被占用

如果上一个 `bigbear-web-cli` 进程没正常关闭，端口 9222 会被占着。**启动前先确认**：

```bash
# Windows
netstat -ano | findstr 9222
# 或
Get-NetTCPConnection -LocalPort 9222 -ErrorAction SilentlyContinue
```

如被占用，结束占用进程或换端口（`--port 9223` 等）。

### 5. 不通过的标准动作（再次强调）

1. 明确告诉用户："❌ 环境前置检查不通过：缺少 XXX / 端口被占 / 浏览器不可用"
2. 给出修复建议
3. 等待用户修完再继续，不要自己猜测默认值

## AI 交互规范（重要）

**你不允许自己读取截图并使用多模态能力分析截图内容**，而应该使用 `get` 命令获取指定区域的内容。

原因：让 skill 能够在不支持多模态的大模型中也能被调用运行。

### 元素描述规范（重要）

**所有** **`click`、`input`、`get`** **命令中的元素描述必须遵循** **`元素类型+目标`** **的命名规则**，以确保 AI 能准确定位目标。

**命名格式**：`[位置] + [目标/内容] + [元素类型]`

**元素类型对照表**：

| 元素类型     | 命名示例                       |
| -------- | -------------------------- |
| 输入框      | 员工姓名输入框、邮箱输入框、搜索输入框、手机号输入框 |
| 下拉框/下拉选项 | 部门下拉选项、性别下拉框、角色下拉选项        |
| 单选/复选框   | 性别男单选项、女单选项、同意协议复选框        |
| 按钮       | 登录按钮、保存按钮、提交按钮、取消按钮、删除按钮   |
| 表格/列表    | 员工列表、数据表格、搜索结果的列表          |
| 文本区域     | 备注文本区域、描述文本区域              |
| 日期/时间选择器 | 入职日期选择器、开始时间选择器            |
| 标签页/Tab  | 基本信息标签页、配置标签页              |
| 对话框/弹窗   | 确认删除弹窗、新增员工对话框             |
| 链接       | 查看详情链接、返回上一页链接             |
| 图片/图标    | 编辑图标、删除图标、预览图片             |
| 分组/区域    | 登录表单区域、基本信息区域、操作栏区域        |

**命名规则**：

1. **必须包含元素类型**：描述末尾明确标识是什么元素（输入框、按钮、下拉框等）
2. **目标用原始文字**：目标部分使用页面上显示的实际文字（如"员工姓名"、"部门"、"邮箱"）
3. **位置可选**：当页面存在多个同类元素时，添加位置前缀（如"顶部的搜索输入框"、"右侧的列表"）
4. **单选/复选框需标明值**：如"性别男单选项"、"同意协议复选框"
5. **下拉选项用"下拉选项"后缀**：如"部门下拉选项"、"角色下拉选项"

**正确示例**：

```bash
bigbear-web-cli --port 9222 input "员工姓名输入框" "张三"
bigbear-web-cli --port 9222 input "邮箱输入框" "zhangsan@example.com"
bigbear-web-cli --port 9222 click "性别男单选项"
bigbear-web-cli --port 9222 click "部门下拉选项"
bigbear-web-cli --port 9222 click "确认删除弹窗"
bigbear-web-cli --port 9222 click "提交按钮"
```

**错误示例**：

```bash
# 缺少元素类型 - AI无法判断是输入框还是按钮
bigbear-web-cli --port 9222 input "员工姓名" "张三"    # 错误
bigbear-web-cli --port 9222 click "登录"              # 错误（是按钮还是链接？）

# 目标不清晰
bigbear-web-cli --port 9222 input "输入框" "张三"      # 错误（哪个输入框？）

# 复选框未标明值
bigbear-web-cli --port 9222 click "同意协议复选框"     # 错误（应明确是"同意"还是"不同意"）
```

### get 命令 - 获取指定区域的内容

```bash
# 获取页面某个区域的结构化描述（布局/图标/文字/介绍），不含坐标
bigbear-web-cli --port 9222 get "登录表单区域的内容"
bigbear-web-cli --port 9222 get "标题下方的正文内容"
bigbear-web-cli --port 9222 get "右侧边栏的内容" -s region.png

# 与描述结合使用
bigbear-web-cli --port 9222 get "页面中央的表格的内容"
```

**参数说明：**

| 参数               | 说明                            |
| ---------------- | ----------------------------- |
| description      | 区域描述，如"标题下方的正文内容"、"登录表单区域的内容" |
| --screenshot, -s | 保存原图路径（可选，不加红框——本命令不返回坐标）     |

**返回内容（结构化描述，不含坐标）：**

- 布局（layout）：区域整体布局描述
- 图标（icons）：区域内识别到的图标列表
- 文字（text）：区域内可见的所有文字
- 介绍（intro）：区域整体功能/用途介绍

> **注意**：`get` 命令是"内容描述"命令，**不含坐标**。如果需要坐标定位，请使用 `scroll --region <描述>`（内部走 `content_analysis.txt` prompt 返回 bbox）。

**使用场景：**

- 当需要确认页面状态或内容时，使用 `get` 而非截图
- 当需要获取动态内容（如列表、表格）时，使用 `get`
- 当需要验证操作结果时，使用 `get` 获取相关区域内容

## 下拉框选择

下拉框选项使用 AI 视觉识别，采用**三步查找法**：

### 标准下拉框操作流程

```bash
# 第1步：点击下拉框，弹出选项列表
bigbear-web-cli --port 9222 click "下拉框"

# 第2步：检查下拉列表是否包含目标选项
bigbear-web-cli --port 9222 get "下拉选项列表区域"

# 第3步：如果选项可见，直接点击选择
bigbear-web-cli --port 9222 click "目标选项"
```

### 查找失败时的处理策略

当目标选项**不在当前可见列表中**时，按以下顺序尝试：

#### 策略一：滚动查找（适用于列表过长需要滚动的情况）

```bash
# 1. 确认下拉框已展开
bigbear-web-cli --port 9222 get "下拉选项列表是否已展开"

# 2. 在下拉列表区域内滚动查找
bigbear-web-cli --port 9222 scroll down --region "下拉选项列表"

# 3. 再次检查目标选项是否出现
bigbear-web-cli --port 9222 get "下拉选项列表区域"

# 4. 找到后点击选择
bigbear-web-cli --port 9222 click "目标选项"
```

#### 策略二：展开被折叠的分组（适用于带分组的大型下拉框）

某些下拉框包含折叠的分组（如"更多选项"等）：

```bash
# 1. 先检查有哪些折叠的分组可见
bigbear-web-cli --port 9222 get "下拉列表中的可折叠分组"

# 2. 点击展开目标分组
bigbear-web-cli --port 9222 click "折叠分组名称"

# 3. 在展开的分组内查找选项
bigbear-web-cli --port 9222 get "分组展开后的选项"

# 4. 找到后点击选择
bigbear-web-cli --port 9222 click "目标选项"
```

#### 策略三：搜索过滤（适用于支持搜索的下拉框）

```bash
# 1. 展开下拉框后，在搜索框中输入关键词
bigbear-web-cli --port 9222 input "下拉框搜索框" "关键词"

# 2. 等待过滤结果
bigbear-web-cli --port 9222 get "过滤后的选项列表"

# 3. 点击选择
bigbear-web-cli --port 9222 click "目标选项"
```

### 完整操作示例

```bash
# 步骤1：点击下拉框展开
bigbear-web-cli --port 9222 click "下拉框"

# 步骤2：检查选项列表
bigbear-web-cli --port 9222 get "下拉选项列表区域"

# 步骤3：判断目标选项是否可见
# - 如果可见：直接 click "目标选项"
# - 如果不可见：执行步骤4

# 步骤4：滚动下拉列表
bigbear-web-cli --port 9222 scroll down --region "下拉选项列表"
bigbear-web-cli --port 9222 get "下拉选项列表区域"

# 步骤5：再次检查，如仍找不到，尝试展开折叠分组
bigbear-web-cli --port 9222 click "折叠分组"
bigbear-web-cli --port 9222 get "分组展开后的选项"

# 步骤6：找到后点击
bigbear-web-cli --port 9222 click "目标选项"
```

### 提示与技巧

- **使用** **`--enhanced`** **参数**：当下拉选项名称模糊时，提供更精确的描述
  ```bash
  bigbear-web-cli --port 9222 click "选项名称" --enhanced "下拉框中描述文字为XXX的选项"
  ```
- **确认选择结果**：选择后使用 `get` 确认下拉框显示的值已更新
  ```bash
  bigbear-web-cli --port 9222 get "下拉框当前显示的值"
  ```
- **超时处理**：如果下拉框展开后列表为空，可能是动态加载问题，等待后重试
  ```bash
  bigbear-web-cli --port 9222 get "下拉选项列表是否正在加载"
  # 等待后重试
  ```

## Key Features

- **AI元素识别**：基于视觉AI定位页面元素
- **AI内容获取**：使用 `get` 命令获取指定区域的内容和文字描述
- **批量并行输入/点击**：使用 `batch` 命令，一次截图并行识别多个元素后逐个执行
- **多显示器支持**：自动检测并处理DPI缩放
- **中文输入支持**：自动识别中文并使用 insert\_text 输入
- **调试模式**：--debug 显示各步骤耗时统计
- **JPEG截图**：click/input 命令默认使用JPEG格式加速

## 多步骤操作 - 并发执行

### 同一页面多操作：使用 batch（推荐）

当多个操作在**同一个页面**上时（如登录表单、填写问卷、注册流程等），应优先使用 `batch` 命令：

**原理**：一次截图 → 并行 AI 识别多个元素坐标 → 逐个执行操作

**速度对比**（假设 3 个元素，AI 识别各需 1s）：

| 方式              | 总耗时        | 说明                 |
| --------------- | ---------- | ------------------ |
| 串行 click/input  | \~6s       | 每个操作：截图+识别+执行      |
| 多进程并行           | \~3s       | 多个进程同时识别，但共享截图     |
| **batch（同一页面）** | **\~1.5s** | **一次截图，并行识别，并发执行** |

**核心优势**：

- **只截图一次**：节省截图时间（尤其是 JPEG 也需 \~0.1-0.3s）
- **并行识别**：多个 AI 请求同时进行，识别时间不变
- **顺序执行**：坐标识别后按序填写，保持用户期望的操作顺序

**使用示例**：

```bash
# 登录表单：一次完成用户名、密码输入 + 点击登录
bigbear-web-cli --port 9222 batch input 用户名::admin input 密码::123456 click 登录按钮

# 注册页面：填写多个字段
bigbear-web-cli --port 9222 batch input 邮箱::test@example.com input 手机号::13800138000 input 验证码::1234

# 搜索页面：输入关键词 + 点击搜索
bigbear-web-cli --port 9222 batch input 搜索框::产品名称 click 搜索按钮
```

### 不同页面多操作：多进程并行

当操作涉及**不同页面**时，使用多进程并行启动多个 bigbear-web-cli：

```bash
# 同时打开多个页面（Linux/macOS 后台任务）
bigbear-web-cli --port 9222 navigate https://www.example.com/page1 &
bigbear-web-cli --port 9223 navigate https://www.example.com/page2 &
bigbear-web-cli --port 9224 navigate https://www.example.com/page3 &

# Windows PowerShell
Start-Process "bigbear-web-cli" -ArgumentList "--port 9222 navigate https://www.example.com/page1"
Start-Process "bigbear-web-cli" -ArgumentList "--port 9223 navigate https://www.example.com/page2"
Start-Process "bigbear-web-cli" -ArgumentList "--port 9224 navigate https://www.example.com/page3"
```

> **提示**：Agent 应优先使用 `batch` 处理同一页面多操作，可大幅提升速度。多个 bigbear-web-cli 进程可同时连接同一个 CDP 端口，各自独立进行 AI 识别。

