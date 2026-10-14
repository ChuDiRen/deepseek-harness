# extensions/

自研与便携扩展的定居目录：随本仓库版本管理，`dsh profile` 通过 vendor junction
挂载加载，仓库即事实源，改动重启 dsh 即生效。

```
extensions/
├── install-to-profile.mjs   # 一键把全部扩展接进任意 profile（扫三层，幂等）
├── bigbear-agents/          # 大熊工具箱三智能体（Web/API/APP 自动化）
├── bigbear-toolkit/         # 大熊工具箱本体：20 个 SKILL + 6 个 Python CLI
└── third-party/             # 22 个 DSH 社区插件源码快照（profile vendor 的 junction 目标）
```

`third-party/` 是 web profile `vendor/` 的唯一事实源（vendor 全部是指向这里的
junction，改这里重启 dsh 即生效）。收录范围：仓库快照按部署实态冻结——含各包
可部署构建产物 `lib/`，不含可再生的 `*.map` 与 `node_modules`（`.gitignore`
守着）；上游更新时在对应目录内重放迁移，历史备份在 `~/dsh-plugin-fixes`。

## 新机器一键部署

```bash
# 0. 先恢复 dsh profile 本体：按 profile 内 PORTABLE.md（vendor/ 22 插件 +
#    compatibility.json + 最小 pnpm store 整包携带），extension 只做增量挂接
# 1. 装 toolkit 依赖（Python 3.11 venv + playwright 内核见 bigbear-toolkit/README.md）
# 2. 填各 .env（仓库只带脱敏 .env.example，密钥不进仓库；参考真实 .env 自行填写）
# 3. 接线 profile（默认 web，可用 --dsh-home 指定其他 DSH_HOME）
node extensions/install-to-profile.mjs web
# 4. 重启 dsh web/desktop
```

`install-to-profile.mjs` 幂等：已存在的 junction 跳过、package.json 条目去重。
真实 `.env`（含各家 API key）从不入库；`git status` 里若出现 extensions 下的
`.env` 属于误放，应立即移出。
