# extensions/bigbear-agents

大熊工具箱（`extensions/bigbear-toolkit`）三条自动化链的 DSH 智能体：

| 预设 id | 名称 | 链路 |
| --- | --- | --- |
| `bigbear-web` | Web 自动化 | 页面采集 → 测试点 → 用例 → 编排 → 计划 → 执行 → 报告 |
| `bigbear-api` | API 自动化 | mitmproxy 录制 → 接口文档 → 用例 → 编排 → 计划 → 执行 → 报告 |
| `bigbear-android` | APP 自动化 | 设备采集 → 测试点 → 用例 → 编排 → 计划（执行走 adb+视觉驱动） |

## 结构

```
bigbear-agents/
├── package.json        # dsh.bundle.patch + dsh.client 声明；运行时依赖仅 schema/cosmokit（已打进 lib）
├── cordis.patch.yml    # 插入唯一宿主行 bigbear-agents
├── src/                # 源码：宿主插件（index/config）+ 浏览器设置页（client/）
├── tsdown.config.ts    # 双面构建：node ESM lib/index.js + client CJS lib/client.js（闭包工厂）
├── lib/                # 构建产物，入库——部署机不做本地构建
└── personas/*.md       # 每链一份人格文本（独立 diff，改这里即改智能体）
```

## 部署配置入口（前端设置页）

网关地址、API key、各链模型、工具箱目录都在 Web 界面配置，不再依赖部署机 `.env`：

- 入口：主界面 **插件** 面板 → 基础分组 → **大熊工具箱** 卡片（与
  `ui-settings-shell` 同一 `plugins.item` 槽位契约）。
- 链路：设置页表单 → config-editor 把覆盖写进 profile 的 `cordis.patch.yml`
  → loader 热重载本行 → `apply` 恢复旧环境后按新值注入
  `AGENT_AI_*` / `WEB_AUTOMATION_AI_*` / `ANDROID_AI_*` / `VISION_*` 与
  `BIGBEAR_TOOLKIT_DIR` → bash/pwsh 子进程继承，工具箱 CLI 优先读注入值
  （python-dotenv `override=False`），项目 `.env` 只作回退。
- 所有字段 `.volatile()`：host 侧 settings 服务只投影 volatile 字段为可编辑
  表单，普通字段不可见。
- 注意：profile 补丁里的值（含 API key）是本机明文，等同原来 `.env` 的安全
  边界；补丁文件不要提交或外发。

## 沙箱与依赖自举（动态安装）

会话沙箱保持 `workspace-write`（base bundle 统一策略，本插件不加不减）：只许
写当前工作区，系统 Python/用户 site-packages 一律不可写。因此工具箱依赖**不做
部署期预装**，由智能体按 persona 里的「环境自举」协议在沙箱内动态自举：

- 统一装进工作区根 `.venv-bigbear`，已存在直接复用、按需增量装；
- venv 内命令行工具用 `<工作区根>\.venv-bigbear\Scripts\<命令>` 全路径调用；
- 已知机器坑写进协议：Windows curl.exe schannel 吊销检查会 000（机器级修复：
  `%USERPROFILE%\.curlrc` 加 `--ssl-no-revoke`），pip 镜像偶发超时重试加
  `--timeout 120`。

依赖永不越出沙箱；技能库目录（仓库副本，经 junction 挂到
`<profile>/node_modules/bigbear-toolkit`）对会话只读。

## 可移植性契约

- **toolkit 相对定位**：技能目录按「设置页 `toolkitDir` → `BIGBEAR_TOOLKIT_DIR`
  环境变量 → 本包的 `../../bigbear-toolkit/.claude/skills` → 历史独立路径」解析，
  全不存在时激活报错并列出尝试过的路径。persona 里的运行时路径用
  `{{BIGBEAR_SKILL_DIR}}` 占位符，注册时由插件替换（该占位符刻意避开 prompt
  模板的 `{{…}}` 语法）。
- **密钥不入库**：toolkit 只带脱敏 `.env.example`；key 走设置页或部署机本地
  `.env`，仓库零密钥。
- **profile 挂接**：不写 `$DSH_HOME/.agent-presets/` 副本（那会产生遮蔽副本、
  阻断仓库修改）；由根目录 `install-to-profile.mjs` 建 vendor junction。

## 修改与验证

- 加链：`personas/` 加一个 md（必须含 `{{BIGBEAR_SKILL_DIR}}` 占位符）+ `PRESETS`
  加一项；改公共能力行只动 `commonPlugins()`。
- persona 前缀的模板插值严格：只允许 `{{model}}`/`{{provider}}` 与
  `{{BIGBEAR_SKILL_DIR}}`（注册前已被替换），其余 `{{...}}` 字面量会在会话轮报
  unknown prompt variable。
- 改完必须重新构建 **并刷新 profile 副本**（pnpm 对 `file:` 依赖做真实目录拷贝）：

```bash
cd extensions/bigbear-agents && E:.../node_modules/.bin/tsdown   # 双面构建
cd ~/.dsh/profiles/web && pnpm install                            # 刷新拷贝
pnpm dsh --profile web --dump-config | grep bigbear-agents        # 组合门
node --import tsx/esm apps/cli/src/bin.ts web --no-open           # 启动门 + UI 验收
```
