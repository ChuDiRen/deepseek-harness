---
name: bigbear-android-cli
description: Use when working with Android device automation, adb control, AI-driven mobile testing, or mentions "bigbear-android", "android cli", "adb", "Android 自动化", "安卓测试". Covers AI clicking, text input, swipe, gestures, keyevents, app launching, and multi-device control via adb.
version: 1.0.0
---

# BigBear Android CLI

AI-powered Android device control via adb commands and vision AI. Lightweight, no Appium required, single-command execution.

## 核心原则

### 1. 页面分析策略（重要）
**不要每一步都执行 `get` 查看页面**，正确流程：
1. 分析一次页面后，记忆当前页面有哪些可执行步骤
2. 执行完这几个步骤后，再用 `get` 查看最新页面状态
3. 仅在**元素找不到**或**需要确认页面内容**时才使用 `get`

### 2. 并发执行原则（重要）
**同一页面的多个独立操作应并行执行**，而非等待上一个完成再执行下一个：
- 登录表单的用户名、密码输入可以并行
- 表单填写的多个字段可以并行
- 多个 bigbear-android-cli 进程可同时操作不同 adb 设备（通过 `-s <serial>` 指定）

### 3. 设备选择策略（重要）
- 默认自动选择 `adb devices` 列表中的**首个** device
- 多设备场景必须用 `-s <serial>` 指定设备，否则操作的是随机第一个
- 操作前建议先 `devices` 确认目标设备在线

### 4. 检查策略（重要）

**batch 命令执行后必须用 `get` 验证**，普通 click/input 仅在异常时检查。

#### batch 命令 → 必须检查
```bash
# batch 执行完成后验证表单填写结果
bigbear-android-cli batch input 用户名输入框::admin input 密码输入框::123456 click 登录按钮
bigbear-android-cli get "登录表单区域的内容"  # 验证填写是否正确
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
bigbear-android-cli click "添加员工按钮"
bigbear-android-cli get "对话框内容区域"  # 确认弹窗是否出现

# 业务结果验证
bigbear-android-cli click "立即提交按钮"
bigbear-android-cli get "员工列表内容"  # 验证新员工是否在列表中
```

## Usage

```bash
# 设备管理
bigbear-android-cli devices                          # 列出所有 adb 设备
bigbear-android-cli start                            # 选择首个设备（默认行为）
bigbear-android-cli start -s emulator-5554           # 选择指定设备

# 启动应用
bigbear-android-cli launch com.android.settings
bigbear-android-cli launch com.example.app .MainActivity

# AI 点击元素
bigbear-android-cli click "登录按钮"
bigbear-android-cli click "页面顶部的搜索框" -s output.png

# AI 输入文本
bigbear-android-cli input "搜索框" "hello world"
bigbear-android-cli input "评论框" "你好世界"  # 中文强制走剪贴板+粘贴（不用拼音）

# AI 长按
bigbear-android-cli longpress "图标" --duration 1500

# 滑动
bigbear-android-cli swipe up
bigbear-android-cli swipe down -c 3
bigbear-android-cli swipe up --region "新闻列表"  # AI 识别区域后聚焦滑动

# 显式坐标滑动
bigbear-android-cli swipe-to 500 1500 500 500 --duration 300

# 双指缩放（地图等场景）
bigbear-android-cli zoom 540 1100 --scale 2.0      # 双指放大
bigbear-android-cli pinch 540 1100 --scale 0.5     # 双指缩小

# 按键
bigbear-android-cli keyevent back
bigbear-android-cli keyevent home
bigbear-android-cli keyevent recents                # 最近任务
bigbear-android-cli keyevent enter
bigbear-android-cli keyevent 4                       # 数字码等同 back

# 专用命令
bigbear-android-cli recents                          # 等同 keyevent 187
bigbear-android-cli notifications                    # 下拉通知栏

# 截图
bigbear-android-cli screenshot screen.png

# 回到桌面
bigbear-android-cli close                            # 等同 keyevent home

# AI 获取内容
bigbear-android-cli get "验证码区域的内容"

# 批量并行操作
bigbear-android-cli batch click "登录按钮" input "搜索框"::"hello" longpress "头像"

# adb shell 透传
bigbear-android-cli shell ls /sdcard/
bigbear-android-cli shell pm list packages

# UI 层次 dump
bigbear-android-cli dump-ui ui.xml

# 应用信息
bigbear-android-cli appinfo com.android.settings

# 屏幕控制
bigbear-android-cli wake
bigbear-android-cli sleep

# 停止应用
bigbear-android-cli stop com.android.settings

# 调试模式（显示各步骤耗时统计）
bigbear-android-cli --debug click "登录按钮"
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| -s, --serial | 目标 adb 设备序列号（多设备时必填） | 首个 device |
| --debug | 调试模式，显示各步骤耗时统计 | false |
| --version | 显示版本号并退出 | - |

## Command Parameters

### click
| Parameter | Description |
|-----------|-------------|
| element | 元素描述（必填） |
| --screenshot, -s | 操作后保存截图路径 |

### input
| Parameter | Description |
|-----------|-------------|
| element | 输入框描述（必填） |
| text | 要输入的文本（必填） |
| --screenshot, -s | 操作后保存截图路径 |

### longpress
| Parameter | Description |
|-----------|-------------|
| element | 元素描述（必填） |
| --duration, -d | 长按时长（ms），默认 1000 |
| --screenshot, -s | 操作后保存截图路径 |

### swipe
| Parameter | Description |
|-----------|-------------|
| direction | up / down / left / right（必填） |
| --region | AI 识别区域，滑动前先聚焦到该区域 |
| --count, -c | 滑动次数，默认 1 |
| --distance | 滑动距离比例 0.1~1.0，默认 0.6 |
| --screenshot, -s | 操作后保存截图路径 |

### swipe-to
| Parameter | Description |
|-----------|-------------|
| x1 y1 x2 y2 | 起点和终点坐标（必填） |
| --duration, -d | 时长（ms），默认 500 |

### pinch / zoom
| Parameter | Description |
|-----------|-------------|
| x y | 中心点坐标（必填） |
| --scale, -s | 缩放比例（pinch 默认 0.5，zoom 默认 2.0） |
| --duration, -d | 单指时长（ms），默认 500 |

### keyevent
| Parameter | Description |
|-----------|-------------|
| code | 数字键码或别名（必填），如 `back` / `home` / `4` |

### screenshot
| Parameter | Description |
|-----------|-------------|
| output | 截图保存路径（必填） |

### get
| Parameter | Description |
|-----------|-------------|
| description | 区域描述（必填），如"验证码区域的内容" |
| --screenshot, -s | 保存原图路径（不加红框——本命令不返回坐标） |

### batch
| Parameter | Description |
|-----------|-------------|
| instructions | 批量指令，格式 `click 描述 \| input 描述::值 \| longpress 描述` |
| --screenshot, -s | 操作后保存截图 |

### launch
| Parameter | Description |
|-----------|-------------|
| package | 应用包名（必填） |
| activity | Activity 名（可选），如 `.MainActivity` |

### appinfo
| Parameter | Description |
|-----------|-------------|
| package | 应用包名（必填） |

### current-app
| Parameter | Description |
|-----------|-------------|
| --format | 输出格式：`text`（默认，单行 `package/activity`）或 `json`（`{"package": "...", "activity": "..."}`） |

**用途**：读取当前前台应用的 package 与 activity（只读，不需要 AI 识别），常用于断言/日志。例如：
```bash
bigbear-android-cli current-app                      # 单行：com.lianjia.beike/.map.MapShowHouseActivity
bigbear-android-cli current-app --format json        # {"package": "...", "activity": "..."}
```

> 实现：优先解析 `dumpsys activity activities` 的 `mResumedActivity`，兜底 `dumpsys window` 的 `mFocusedApp`。

### shell
| Parameter | Description |
|-----------|-------------|
| cmd | 要执行的 adb shell 命令及参数（必填） |

### dump-ui
| Parameter | Description |
|-----------|-------------|
| output | XML 保存路径（必填） |

## Environment Variables

支持 `.env` 文件配置：

```bash
# AI API 配置
ANDROID_AI_API_KEY=your_api_key_here
ANDROID_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ANDROID_AI_MODEL=qwen-vl-max

# 默认设备（可选）
ANDROID_DEFAULT_DEVICE=emulator-5554

# adb 可执行路径（可选，默认从 PATH 查找）
ANDROID_ADB_PATH=/path/to/adb
```

或设置环境变量：
```bash
export ANDROID_AI_API_KEY=your_api_key_here
export ANDROID_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export ANDROID_AI_MODEL=qwen-vl-max
```

`.env` 加载规则：CLI 继承系统环境变量，并且只读取执行命令时当前工作目录下的 `.env`。系统环境变量优先于 `.env` 中的同名变量；不会搜索用户目录、安装目录、父目录或其他工作区目录。

> **注意**：使用前必须配置 `ANDROID_AI_API_KEY`（AI API 密钥）。`adb` 必须在 PATH 中，或通过 `ANDROID_ADB_PATH` 指定完整路径。

## AI 交互规范（重要）

**你不允许自己读取截图并使用多模态能力分析截图内容**，而应该使用 `get` 命令获取指定区域的内容。

原因：让 skill 能够在不支持多模态的大模型中也能被调用运行。

### 元素描述规范（重要）

**所有 `click`、`input`、`longpress`、`get` 命令中的元素描述必须遵循 `元素类型+目标` 的命名规则**，以确保 AI 能准确定位目标。

**命名格式**：`[位置] + [目标/内容] + [元素类型]`

**元素类型对照表**：

| 元素类型 | 命名示例 |
|----------|----------|
| 输入框 | 员工姓名输入框、邮箱输入框、搜索输入框、手机号输入框 |
| 下拉框/下拉选项 | 部门下拉选项、性别下拉框、角色下拉选项 |
| 单选/复选框 | 性别男单选项、同意协议复选框 |
| 按钮 | 登录按钮、保存按钮、提交按钮、取消按钮、删除按钮 |
| 列表/网格 | 商品列表、搜索结果的列表、新闻列表 |
| 文本区域 | 备注文本区域、描述文本区域 |
| 日期/时间选择器 | 入职日期选择器、开始时间选择器 |
| 标签页/Tab | 基本信息标签页、配置标签页 |
| 对话框/弹窗 | 确认删除弹窗、新增员工对话框 |
| 链接 | 查看详情链接、返回上一页链接 |
| 图片/图标 | 编辑图标、删除图标、预览图片、头像图标 |
| 分组/区域 | 登录表单区域、基本信息区域、操作栏区域 |
| 菜单项 | 设置菜单项、退出登录菜单项 |
| 卡片 | 商品卡片、订单卡片、新闻卡片 |

**命名规则**：
1. **必须包含元素类型**：描述末尾明确标识是什么元素（输入框、按钮、下拉框、列表等）
2. **目标用原始文字**：目标部分使用页面上显示的实际文字（如"员工姓名"、"部门"、"邮箱"）
3. **位置可选**：当页面存在多个同类元素时，添加位置前缀（如"顶部的搜索输入框"、"右侧的列表"）
4. **单选/复选框需标明值**：如"性别男单选项"、"同意协议复选框"
5. **下拉选项用"下拉选项"后缀**：如"部门下拉选项"、"角色下拉选项"
6. **菜单项必须以"菜单项"结尾**：与底部 tab bar 区分，如"设置菜单项"而非"设置"

**正确示例**：
```bash
bigbear-android-cli input "员工姓名输入框" "张三"
bigbear-android-cli input "邮箱输入框" "zhangsan@example.com"
bigbear-android-cli click "性别男单选项"
bigbear-android-cli click "部门下拉选项"
bigbear-android-cli click "确认删除弹窗"
bigbear-android-cli click "提交按钮"
bigbear-android-cli click "设置菜单项"
bigbear-android-cli click "登录头像图标"
bigbear-android-cli swipe up --region "新闻列表"
```

**错误示例**：
```bash
# 缺少元素类型 - AI无法判断是输入框还是按钮
bigbear-android-cli input "员工姓名" "张三"    # 错误
bigbear-android-cli click "登录"              # 错误（是按钮还是菜单项？）

# 目标不清晰
bigbear-android-cli input "输入框" "张三"      # 错误（哪个输入框？）

# 复选框未标明值
bigbear-android-cli click "同意协议复选框"     # 错误（应明确是"同意"还是"不同意"）
```

### get 命令 - 获取指定区域的内容

```bash
# 获取页面某个区域的结构化描述（布局/图标/文字/介绍），不含坐标
bigbear-android-cli get "登录表单区域的内容"
bigbear-android-cli get "标题下方的正文内容"
bigbear-android-cli get "右侧边栏的内容" -s region.png

# 与描述结合使用
bigbear-android-cli get "页面中央的列表的内容"
bigbear-android-cli get "搜索结果区域的内容"
```

**参数说明：**
| 参数 | 说明 |
|------|------|
| description | 区域描述，如"标题下方的正文内容"、"登录表单区域的内容" |
| --screenshot, -s | 保存原图路径（可选，不加红框——本命令不返回坐标） |

**返回内容（结构化描述，不含坐标）：**
- 布局（layout）：区域整体布局描述，如"上下结构：顶部标题栏 + 中部表单 + 底部按钮"
- 图标（icons）：区域内识别到的图标列表（如["返回箭头图标", "搜索图标"]）
- 文字（text）：区域内所有可见的文字内容（含标签、按钮文案、占位提示等）
- 介绍（intro）：区域整体功能/用途介绍，如"这是一个登录表单，用户输入账号密码后点击登录进入系统"

> **注意**：`get` 命令是"内容描述"命令，**不含坐标**。如果需要坐标定位，请使用 `swipe --region <描述>`（内部走 `content_analysis.txt` prompt 返回 bbox）。

**使用场景：**
- 当需要确认页面状态或内容时，使用 `get` 而非截图
- 当需要获取动态内容（如列表、表格）时，使用 `get`
- 当需要验证操作结果时，使用 `get` 获取相关区域内容

## keyevent 按键别名

支持 30+ 常用别名，数字码等同 Android KeyEvent：

| 分类 | 别名 | 键码 |
|------|------|------|
| 导航 | `back` | 4 |
| 导航 | `home` | 3 |
| 导航 | `menu` | 82 |
| 导航 | `recents` / `app_switch` / `recent` / `overview` | 187 |
| 导航 | `notifications` | 83 |
| 导航 | `quick_settings` | 224 |
| 文本 | `enter` | 66 |
| 文本 | `delete` / `backspace` | 67 |
| 文本 | `tab` | 61 |
| 文本 | `space` | 62 |
| 文本 | `esc` | 111 |
| 系统 | `power` | 26 |
| 系统 | `volume_up` | 24 |
| 系统 | `volume_down` | 25 |
| 系统 | `wakeup` / `wake` | 224 |
| 系统 | `sleep` | 223 |
| 剪贴板 | `paste` | 279 |
| 剪贴板 | `copy` | 278 |
| 剪贴板 | `cut` / `select_all` | 277 |
| 方向 | `up` / `down` / `left` / `right` | 19/20/21/22 |
| 媒体 | `refresh` | 231 |
| 媒体 | `forward` | 125 |
| 媒体 | `search` | 84 |

数字键码也可直接使用，如 `keyevent 4` 等同 `keyevent back`。

## 中文输入（粘贴方式，重要）

**所有非 ASCII 字符（含中文、emoji）一律通过剪贴板 + 粘贴实现**，不走拼音 IME、不走 `adb shell input text`。

### 实现机制

```bash
bigbear-android-cli input "评论输入框" "你好世界"
# 实际执行步骤：
# 1. 点击输入框获取焦点
# 2. MOVE_END (123) + 50 次 DEL 清空输入框
# 3. adb shell cmd clipboard set-primary-clip --user 0 "你好世界"
# 4. keyevent 279 (PASTE)
```

### 为什么不走拼音

- **拼音太慢**：每字 6 次按键 + 候选词弹窗选择
- **不受 IME 状态影响**：设备装搜狗/百度/讯飞等都不影响
- **跨设备一致**：IME 行为差异巨大，剪贴板方案稳定
- **不误触候选词弹窗**：截图和断言更可靠

### 失败行为（明确退出，不兜底乱码）

**剪贴板设置失败时立即抛 `RuntimeError` 并退出（exit code != 0）**，**绝不**兜底为 `input text`。原因：`adb shell input text` 对中文必然产生乱码，"看似成功但内容乱码"比"明确失败"更危险。

```bash
# 典型失败场景：设备 Android < 10
bigbear-android-cli input "搜索框" "天心区"
# [FAIL] 剪贴板设置失败 [emulator-5554]（需 Android ≥ 10 / API 29+）：...
#       如设备版本较低或权限受限，请安装 ADBKeyboard 后改用其广播接口输入。
# exit code: 1
```

### 已知副作用

1. **Android 12+ 粘贴后会显示系统 Toast** "已从剪贴板粘贴"，会出现在截图中（如需 AI 识别，需在 `get` 时描述忽略该 Toast）
2. **某些 App 禁用剪贴板读取**（金融/隐私类），本路径会失败 → 需安装 ADBKeyboard 兜底
3. **不触发应用内 IME 回调**：少数 App 强依赖 IME 监听的事件，可能识别为"非真实输入"
4. **清空输入框用 50 次 DEL**：若光标不在末尾，长文本场景可能卡住或误删

## stop vs close：离开应用的两个层级（重要）

`stop` 和 `close` 都能让 App 从前台消失，但底层行为完全不同。**绝大多数情况下应该用 `close`**，只有需要冷启动/释放内存时才用 `stop`。

### 对比

| 命令 | 实现 | 进程 | 内存 | 下次启动 | 适用场景 |
|------|------|------|------|----------|----------|
| `close` | `keyevent home` (3) | **保留** | **保留** | 恢复原状态 | 临时离开、切换其他 App |
| `stop <pkg>` | `am force-stop <pkg>` | **杀死** | **释放** | 冷启动（无缓存状态） | 测试冷启动、释放内存、完整重置 |

### 行为差异示例

```bash
# 场景 A：暂时离开 App，过会儿还要回来
bigbear-android-cli close
# → 按 Home 键回桌面，App 进程仍在后台运行
# → 再次 launch 或从最近任务点回，App 直接恢复到离开时的页面

# 场景 B：测试冷启动（验证 App 首屏、引导页、登录态丢失等）
bigbear-android-cli stop com.example.app
bigbear-android-cli launch com.example.app
# → 第一次启动：走完整 Splash → 首屏 → 可能要求重新登录

# 场景 C：调试时重置 App 状态
bigbear-android-cli stop com.example.app
# → 等同于在系统设置里"强行停止"，下次启动是全新实例
```

### 常见误区

- ❌ 用 `stop` "退出" App 来"节省内存"——会丢失所有未保存状态和后台任务
- ❌ 用 `close` 期望清空登录态——只会最小化，登录信息完全保留
- ❌ 把 `stop` 和 `close` 当作可互换的同义词

### 选择决策树

```
需要离开 App？
├─ 之后还要回到同一个 App？→ close
├─ 测试冷启动/首屏？     → stop + launch
├─ 释放被测 App 内存？    → stop
├─ 切换到另一个 App？     → launch <新包名>（旧 App 自动后台，无需显式 close）
└─ 不确定？               → 优先 close（可逆、最安全）
```

## 下拉框选择

Android 下拉框选项使用 AI 视觉识别，采用**三步查找法**：

### 标准下拉框操作流程

```bash
# 第1步：点击下拉框，弹出选项列表
bigbear-android-cli click "下拉框"

# 第2步：检查下拉列表是否包含目标选项
bigbear-android-cli get "下拉选项列表区域"

# 第3步：如果选项可见，直接点击选择
bigbear-android-cli click "目标选项"
```

### 查找失败时的处理策略

当目标选项**不在当前可见列表中**时，按以下顺序尝试：

#### 策略一：滑动查找（适用于列表过长需要滑动的情况）

```bash
# 1. 确认下拉框已展开
bigbear-android-cli get "下拉选项列表是否已展开"

# 2. 在下拉列表区域内滑动查找
bigbear-android-cli swipe up --region "下拉选项列表"

# 3. 再次检查目标选项是否出现
bigbear-android-cli get "下拉选项列表区域"

# 4. 找到后点击选择
bigbear-android-cli click "目标选项"
```

#### 策略二：搜索过滤（适用于支持搜索的下拉框）

```bash
# 1. 展开下拉框后，在搜索框中输入关键词
bigbear-android-cli input "下拉框搜索框" "关键词"

# 2. 等待过滤结果
bigbear-android-cli get "过滤后的选项列表"

# 3. 点击选择
bigbear-android-cli click "目标选项"
```

### 完整操作示例

```bash
# 步骤1：点击下拉框展开
bigbear-android-cli click "下拉框"

# 步骤2：检查选项列表
bigbear-android-cli get "下拉选项列表区域"

# 步骤3：判断目标选项是否可见
# - 如果可见：直接 click "目标选项"
# - 如果不可见：执行步骤4

# 步骤4：滑动下拉列表
bigbear-android-cli swipe up --region "下拉选项列表"
bigbear-android-cli get "下拉选项列表区域"

# 步骤5：找到后点击
bigbear-android-cli click "目标选项"
```

### 提示与技巧

- **使用 --region 滑动**：在列表区域内滑动比整屏滑动更精准
- **确认选择结果**：选择后使用 `get` 确认下拉框显示的值已更新
- **超时处理**：如果下拉框展开后列表为空，可能是动态加载问题，等待后重试

## Key Features

- **AI元素识别**：基于视觉AI定位页面元素
- **AI内容获取**：使用 `get` 命令获取指定区域的内容和文字描述
- **批量并行输入/点击**：使用 `batch` 命令，一次截图并行识别多个元素后逐个执行
- **中文输入支持**：自动识别非 ASCII 字符，强制走剪贴板+粘贴（Android 10+）。**不**走拼音 IME、不兜底为 `input text`（避免中文乱码）；剪贴板失败时立即报错退出
- **双指手势**：`zoom` / `pinch` 通过并行 `adb shell input swipe` 模拟双指
- **多设备支持**：通过 `-s <serial>` 并行控制多台 adb 设备
- **adb shell 透传**：`shell` 命令直接透传任意 adb shell 调用
- **调试模式**：--debug 显示各步骤耗时统计
- **JPEG截图**：click/input 默认使用 JPEG 压缩加速

## 多步骤操作 - 并发执行

### 同一页面多操作：使用 batch（推荐）

当多个操作在**同一个页面**上时（如登录表单、填写问卷、注册流程等），应优先使用 `batch` 命令：

**原理**：一次截图 → 并行 AI 识别多个元素坐标 → 逐个执行操作

**速度对比**（假设 3 个元素，AI 识别各需 1s）：
| 方式 | 总耗时 | 说明 |
|------|--------|------|
| 串行 click/input | ~6s | 每个操作：截图+识别+执行 |
| 多设备并行 | ~3s | 多个进程同时操作不同设备 |
| **batch（同一页面）** | **~1.5s** | **一次截图，并行识别，并发执行** |

**核心优势**：
- **只截图一次**：节省截图时间（screencap 通常 ~0.3-0.5s）
- **并行识别**：多个 AI 请求同时进行，识别时间不变
- **顺序执行**：坐标识别后按序填写，保持用户期望的操作顺序

**使用示例**：
```bash
# 登录表单：一次完成用户名、密码输入 + 点击登录
bigbear-android-cli batch input 用户名输入框::admin input 密码输入框::123456 click 登录按钮

# 注册页面：填写多个字段
bigbear-android-cli batch input 邮箱输入框::test@example.com input 手机号输入框::13800138000 input 验证码输入框::1234

# 搜索页面：输入关键词 + 点击搜索
bigbear-android-cli batch input 搜索输入框::产品名称 click 搜索按钮
```

> **注意**：`batch input` 当前以屏幕中心作为输入位置（未单独 AI 识别输入框坐标）。若输入框不在屏幕中央，请使用 `input` 命令单独定位输入。

### 不同设备多操作：多进程并行

当操作涉及**不同设备**时，使用多进程并行启动多个 bigbear-android-cli：

```bash
# 同时在多台设备上执行（Linux/macOS 后台任务）
bigbear-android-cli -s emulator-5554 launch com.example.app &
bigbear-android-cli -s emulator-5556 launch com.example.app &
bigbear-android-cli -s V2148A launch com.example.app &

# Windows PowerShell
Start-Process "bigbear-android-cli" -ArgumentList "-s emulator-5554 launch com.example.app"
Start-Process "bigbear-android-cli" -ArgumentList "-s emulator-5556 launch com.example.app"
Start-Process "bigbear-android-cli" -ArgumentList "-s V2148A launch com.example.app"
```

> **提示**：Agent 应优先使用 `batch` 处理同一页面多操作，可大幅提升速度。多设备场景下，进程级别的并行是唯一选择。

## 典型工作流示例

### 应用启动 + 操作 + 验证

```bash
# 1. 确认设备
bigbear-android-cli devices

# 2. 启动应用
bigbear-android-cli launch com.lianjia.beike

# 3. 等待加载 + AI 点击
sleep 2
bigbear-android-cli click "地图找房按钮"

# 4. 区域滑动（如地图平移）
bigbear-android-cli swipe up -c 3

# 5. 双指缩放（地图）
bigbear-android-cli zoom 540 1100 --scale 2.0

# 6. 输入搜索词（中文强制走剪贴板+粘贴）
bigbear-android-cli input "搜索输入框" "天心区"

# 7. 验证搜索结果
bigbear-android-cli get "搜索结果列表"
```

### 表单批量填写

```bash
bigbear-android-cli launch com.example.app .RegisterActivity
sleep 2
bigbear-android-cli batch \
  input 姓名输入框::张三 \
  input 邮箱输入框::zhangsan@example.com \
  input 手机号输入框::13800138000 \
  click 提交按钮
sleep 1
bigbear-android-cli get "提交结果提示"
```

### 调试排查

```bash
# UI 层次结构
bigbear-android-cli dump-ui ui.xml

# 应用信息
bigbear-android-cli appinfo com.example.app

# 当前 Activity
bigbear-android-cli shell dumpsys window | grep -i mCurrentFocus

# 截图调试
bigbear-android-cli --debug click "登录按钮"
```