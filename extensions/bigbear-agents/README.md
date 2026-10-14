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
├── package.json        # dsh.bundle.patch 声明，零运行时依赖
├── cordis.patch.yml    # 插入唯一宿主行 bigbear-agents
├── lib/index.js        # 命名空间插件：公共能力行一份 + 逐个 register preset
└── personas/*.md       # 每链一份人格文本（独立 diff，改这里即改智能体）
```

## 可移植性契约

- **toolkit 相对定位**：技能目录按「`BIGBEAR_TOOLKIT_DIR` 环境变量 → 本包的
  `../../bigbear-toolkit/.claude/skills` → 历史独立路径」解析，全不存在时激活
  报错并列出尝试过的路径。persona 里的运行时路径用 `{{BIGBEAR_SKILL_DIR}}`
  占位符，注册时由插件替换（该占位符刻意避开 prompt 模板的 `{{…}}` 语法）。
- **密钥不入库**：toolkit 只带脱敏 `.env.example`；部署时复制为 `.env` 填各家
  API key。persona 不写网关地址，只引用项目 `.env`。
- **profile 挂接**：不写 `$DSH_HOME/.agent-presets/` 副本（那会产生遮蔽副本、
  阻断仓库修改）；由根目录 `install-to-profile.mjs` 建 vendor junction。

## 修改与验证

- 加链：`personas/` 加一个 md（必须含 `{{BIGBEAR_SKILL_DIR}}` 占位符）+ `PRESETS`
  加一项；改公共能力行只动 `commonPlugins()`。
- persona 前缀的模板插值严格：只允许 `{{model}}`/`{{provider}}` 与
  `{{BIGBEAR_SKILL_DIR}}`（注册前已被替换），其余 `{{...}}` 字面量会在会话轮报
  unknown prompt variable。

```bash
pnpm dsh --profile web --dump-config | grep bigbear-agents   # 组合门
node --import tsx/esm apps/cli/src/bin.ts web --no-open      # 启动门 + UI 验收
```
