---
name: bigbear-web-record
description: Use when working with "bigbear-web-record", "华测WEB采集", "WEB录制", or capturing WEB interface snapshots with DOM/screenshot.
version: 1.0.0
---
重点： 请使用中文沟通！！

# BigBear Web Record

华测 WEB 界面采集工具，通过 Playwright CDP 录制浏览器界面快照，包含 DOM 结构、截图和可选的 AI 视觉分析。

## 使用场景

- **界面录制**：采集 WEB 页面的 DOM 结构、截图和界面描述
- **需求文档**：结合多模态 AI 生成界面需求描述
- **测试点分析**：基于录制内容分析测试点

## Usage

```bash
# 录制 WEB 界面。 注意！除非用户明确指定，不要配置output
bigbear-web-record record <url> [--output <dir>]

# 示例
bigbear-web-record record https://www.example.com
# 指定输出目录。注意！除非用户明确指定，不要配置output
bigbear-web-record record https://www.example.com --output ./output

# 启用视觉 AI 分析
bigbear-web-record record <url> --enable-vision

# 帮助信息
bigbear-web-record --help
```

## 录制流程

1. 运行录制命令，启动浏览器并打开指定 URL
2. 浏览器右上角出现悬浮球（模块/功能点/描述 输入框 + SNAP 按钮）
3. 填写模块编号（如 `用户模块/登录注册`，支持多层路径）、功能点描述（可选）、界面描述（可选）
4. 点击 **SNAP** 捕获当前页面快照
5. 可多次捕获，每次生成独立的截图和 DOM 文件

## 输出文件

统一命名规则：录制会自动按时间戳生成批次号目录，所有数据落在 `AI-信息采集/<批次号>/<模块路径>/` 下。

- **批次目录**：`{output}/{批次号}/`（批次号由工具自动生成，例如 `20260602-215450`）
- **功能目录**：`{output}/{批次号}/{模块路径}/`（`{模块路径}` 即悬浮球里填入的模块字段，支持多层）
- **图片**：`{output}/{批次号}/{模块路径}/img/screenshot_{N}.png`
- **DOM**：`{output}/{批次号}/{模块路径}/json/dom_{N}.json`

完整目录示意（web 项目根目录下三个统一命名的根目录并列）：

```text
web/                                  ← web 项目根目录
├── AI-信息采集/                       ← --output 默认值
│   └── 20260602-215450/              ← 自动生成的批次号
│       └── 用户模块/登录注册/         ← 用户填入的模块路径
│           ├── json/dom_1.json
│           └── img/screenshot_1.png
├── AI-测试点分析/                     ← testpoint 写入
└── AI-测试用例/                       ← case-generator 写入
```

## DOM 文件内容

```json
{
  "content": "DOM 结构文本",
  "img": "img/screenshot_1.png",
  "module": "模块编号",
  "func": "功能点描述",
  "desc": "界面描述",
  "interface_desc": "AI 视觉分析-界面整体描述",
  "layout_desc": "AI 视觉分析-布局描述",
  "elements_desc": "AI 视觉分析-元素描述列表"
}
```

## 参数说明

| 参数                 | 说明                                               | 默认值                       |
| -------------------- | -------------------------------------------------- | ---------------------------- |
| `url`              | 目标网站 URL                                       | -                            |
| `--output`, `-o` | 输出目录（**本工具应在项目根目录下运行**，如 `WEB功能测试/`；除非用户明确指定，不要配置output） | `./AI-信息采集`             |
| `--enable-vision`  | 启用多模态 AI 截图分析                             | false                        |
| `--vision-model`   | 视觉分析使用的模型                                 | `qwen3.6-flash-2026-04-16` |
| `--cdp-port`       | CDP 调试端口                                       | 9222                         |

## 环境变量

```bash
# AI API 配置（用于视觉分析）
VISION_API_KEY=your_api_key_here
VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen3.6-flash-2026-04-16

```

## 环境要求

- Python 3.9+
- Playwright 浏览器：`playwright install chromium`

## 工作原理

- 通过 Chrome DevTools Protocol (CDP) 捕获页面 DOM 和截图
- 使用 `playwright-cli snapshot` 获取 DOM 结构
- 可选：调用多模态大模型分析截图内容
