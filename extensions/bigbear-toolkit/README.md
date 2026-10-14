# 大熊工具箱（Big Bear Toolkit）

从 `自动化/Phase1` 提取的可用资产：**SKILL 指令层 + CLI 执行层**。课件与历史采集数据未包含。
全部命名已从 `huace-*` 统一重命名为 `bigbear-*`（技术标识用纯 ASCII，避免中文路径/包名坑），SKILL.md、pyproject、源码 import 已同步并校验一致。

> **入库说明（2026-10-14）**：本目录已整体迁入 deepseek-harness fork 的
> `extensions/bigbear-toolkit`，随仓库版本管理。真实 `.env`（含 API key）不入库，
> 仓库只带脱敏 `.env.example`；新机器部署时复制为 `.env` 并填入实际 key。
> DSH 侧的 bigbear 三智能体按仓库相对路径定位本目录（可用 `BIGBEAR_TOOLKIT_DIR`
> 覆盖），与 dsh-agent 的挂接见 `../bigbear-agents/README.md`。

## 结构

```
bigbear-toolkit/
├── .claude/skills/     # 20 个 SKILL.md（AI 调度层，Claude Code / ZCode 打开本目录即可发现）
└── apps/               # 6 个 CLI 工具包（真正干活的）
    ├── bigbear-web-record-cli      # Web UI 录制（Playwright + SNAP 按钮，五字段 JSON）
    ├── bigbear-mitmproxy-record-cli# API 抓包录制（mitmproxy 插件，raw{NN}.json）
    ├── bigbear-device-record       # APP UI 录制（midscene 投屏录制台）
    ├── bigbear-web-cli             # Web UI 执行（CDP 直连 + AI 视觉定位 0~1000 归一化坐标）
    ├── bigbear-android-cli         # Android UI 执行（adb shell 直连 + AI 视觉定位）
    └── bigbear-test-runner         # 执行引擎（agentscope，读 YAML 计划/编排，pytest+allure 报告）
```

SKILL → CLI 对应关系：

| 录制链 | 执行链 | 编排执行 |
|---|---|---|
| bigbear-web-record → bigbear-web-record-cli | bigbear-web-cli → bigbear-web-cli | bigbear-test-plan-generator / bigbear-test-flow-builder → bigbear-test-runner |
| bigbear-mitmproxy-record → bigbear-mitmproxy-record-cli | bigbear-api-cli（curl 替代，接口任务用） | |
| bigbear-android-record → bigbear-device-record | bigbear-android-cli → bigbear-android-cli | |

其余 skill（*-case-generator、*-testpoint、bigbear-api-doc-generator、bigbear-report-generate-html、zentao-cli 等）是提示词型技能，不依赖本地 CLI，可直接用。

## 安装

```bash
cd bigbear-toolkit

# 1. 建虚拟环境（Python 3.11）
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash；cmd 用 .venv\Scripts\activate.bat

# 2. 装全部 CLI 工具
for d in apps/*/; do pip install -e "$d"; done

# 3. Playwright 浏览器内核（Web 录制/执行必需）
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
playwright install chromium

# 4. 外部依赖按需检查
mitmweb --version        # API 录制需要（缺了 pip install mitmproxy）
adb devices -l           # Android 执行/录制需要
node -v                  # >=18，midscene / playwright-cli 需要
```

## 配置

`apps/bigbear-test-runner/.env` 已随包带过来（本机网关 192.168.1.6:13000 的 Agent/视觉模型配置）。
换环境时改里面的 `*_API_KEY / *_BASE_URL / *_MODEL` 四组即可。

## 快速使用

```bash
# Web 录制
bigbear-web-record record <url>

# API 抓包（控制面板 http://127.0.0.1:9090/）
bigbear-api-record record

# Web 执行
bigbear-web-cli --port 9222 start
bigbear-web-cli --port 9222 navigate <url>
bigbear-web-cli --port 9222 click 登录按钮

# 执行引擎（在含 project_data 的项目目录下）
bigbear-test-runner --skills-dir <本目录>/.claude/skills --skill bigbear-web-cli
```

正常使用姿势：在本目录（或任何把 `.claude/skills` 放进项目根的目录）启动 Claude Code / ZCode，
用自然语言说「帮我录制 xx 页面」「生成测试计划」「执行这个测试计划」，AI 自动匹配 skill → 调 CLI。

## 注意

- runner 的 console 命令名是 `bigbear-test-runner`（课件里写作 huace-ai-test-runner，以包内 pyproject.toml 为准）
- `apps/bigbear-android-cli/demo/demo_step_by_step.py` 有一处原始代码就存在的括号 bug，已顺手修复
- 本目录不是 git 仓库，需要版本管理时自行 `git init`
