---
name: bigbear-report-generate-html
description: 当用户给出一个 `<batch_dir>`（含 `batch_result.json`）并要求"生成 HTML 报告/出 HTML/做 HTML 报告"时调用。封装 `render_html_report.py`：读 `batch_result.json` + `report_template.html`（Jinja2），输出 `<batch_dir>/report.html` 单文件，浏览器双击即可打开看**三栏同屏布局**（左：流程列表 / 中：当前流程的任务列表 / 右：任务详情，含 request/response/assertion/screenshots/attachments）。
---

# generate-html-report

把 `<batch_dir>/batch_result.json` 渲染为单文件 HTML 报告。

## 脚本位置

本 skill 的脚本在 `scripts/` 子目录下（与 SKILL.md 同级），下文中 `<skill_dir>` 即 SKILL.md 所在目录。`scripts/` 含两个文件：
- `render_html_report.py`（主渲染器）
- `report_template.html`（Jinja2 模板，单文件 HTML 含内联 CSS/JS）

运行命令时使用相对路径：

```
python <skill_dir>/scripts/render_html_report.py "<batch_dir>"
```

> 注：`scripts/` 下的文件是项目根对应文件的副本，逻辑保持一致。修改源文件后请跑 `python sync_scripts.py` 同步。

## 输入

- `batch_dir`：批次目录绝对路径，形如 `C:\...\AI-自动化测试执行\执行记录-20260605221506`
  - 必须含 `batch_result.json`（由 `bigbear-run-test-plan` 的 `prepare` 或 `refresh` 生成）

可选：
- `--output` / `-o`：指定 HTML 输出路径，默认 `<batch_dir>/report.html`

如果用户没给 `batch_dir`，先问；不要猜。

## 执行步骤

### 1. 跑渲染

```
python <skill_dir>/scripts/render_html_report.py "<batch_dir>"
```

完整捕获 stdout。脚本退出码非 0 → 把 stderr 抛给用户，停止。

### 2. 校验产物

渲染成功后，`<batch_dir>/report.html` 应存在且大小 > 0（典型 20-100 KB）。报告用户：
- 文件路径
- 文件大小
- 打开方式：`file://<绝对路径>`（Chrome 双击 file:// 需加 `--allow-file-access-from-files` 或起 `python -m http.server`）

### 3. （可选）截图场景说明

如果批次里有 web 任务且 AI 已截图到 `<batch_dir>/screenshots/`，报告里 `screenshots` 字段是相对 batch_dir 的路径（如 `screenshots/task_4_step_1.png`）。浏览器加载时用相对路径，**HTML 和 screenshots 必须在同一目录树里**（即 `report.html` 和 `screenshots/` 目录是兄弟关系，浏览器以 `file://` 或本地 server 打开时都能正常解析）。

附件（`task.attachments`）路径也走相同的相对解析规则，HTML 不做 base64 内联。

## 报告交互特性

- **三栏同屏布局**（页面打开即全部可见，无 drill-down）
  - **左栏** — 流程列表：每张卡片含名称、ID、pass/fail/error 计数、底部按比例着色的进度条
  - **中栏** — 任务列表：当前流程的所有任务，按 task_index 升序，含类型徽标、状态徽标、耗时；顶部过滤 chip（全部 / 通过 / 失败 / 异常 / 未跑）
  - **右栏** — 任务详情：固定头部（标题 + 类型 + 状态 + 开始/结束/耗时/文件元数据） + 可折叠 section 列表（输入 / 输出 / 期望项 / 断言详情 / 请求 / 响应 / 执行步骤 / 终态 / 截图 / 附件 / 错误信息）
- **统计条**：顶栏下方一排 5 个卡片（总数 / 通过 / 失败 / 异常 / 总耗时），hover 微浮起
- **状态徽标**：pass（绿）/ fail（红）/ error（黄）/ pending（灰）
- **类型徽标**：api（蓝）/ web（橙）/ dynamic-function（紫）
- **JSON 响应体自动格式化**：response.body 若 Content-Type 是 JSON，会尝试 `JSON.parse` 缩进显示
- **请求/响应体复制按钮**：一键复制到剪贴板，含"已复制"反馈
- **截图灯箱**：点击缩略图放大查看（fixed + 模糊背景），Esc 或点击空白关闭
- **附件展现**：`task.screenshots` 按扩展名识别为图片（缩略图网格 + 步骤编号徽标）或非图片附件（带文件类型 chip + 大小 + 打开链接）；`task.attachments` 作为通用附件列表渲染
- **键盘导航**：`↑/↓` 或 `j/k` 切任务（按当前过滤生效），`Esc` 关灯箱
- **响应式降级**：< 1024px 隐藏中栏，< 640px 隐藏左栏
- **损坏容错**：result 文件损坏时显示黄色横幅 + 仅文件元信息

## 输出

向用户报告：
- `<batch_dir>/report.html` 已生成（路径 + 大小）
- 打开建议（file:// 或起本地 server）
- 如果 batch_result.json 不存在，提示先跑 `bigbear-run-test-plan` 或 `run_test_plan.py refresh`

## 不做的事

- 不重新执行任何 task —— 只读 `batch_result.json`
- 不修改 `batch_result.json` 或任何 per-task result
- 不生成截图 —— 截图由 web 任务的 AI 在浏览器中执行步骤时产出
- 不联网 / 不发任何请求
- 不需要外部库（除 Jinja2 用于模板渲染）
