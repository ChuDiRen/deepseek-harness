# 安卓（Android）UI 自动化执行工具 + SKILL 底层开发

## 一、为什么要开发这个工具：痛点与核心价值
### 1. 业务背景和传统方案的痛点
前面我们已经有了**测试用例**（设备端录制工具把安卓手机上的页面、操作、用例都录下来了），接下来要解决**用例执行**——把这些用例在真实安卓设备（真机 / 模拟器）上跑起来：启动应用、点击按钮、输入数据、滑动翻页、验证结果。

传统手工执行用例存在如下痛点：

+ **重复劳动**：同样的登录、下单、搜索流程，每个版本回归都要手工在手机上点一遍
+ **效率极低**：几十上百条用例，手工执行既慢又容易漏
+ **难以自动化驱动**：我们希望测试用例能被 AI 用自然语言指挥着在手机上跑起来，而不是人肉操作

### 2. 可选方案盘点
想直接"拿来用"现有的安卓执行工具，先看两条主流路：

#### 方案1：midscene.js（AI 视觉驱动，但太慢）
Midscene 是"视觉驱动 UI 测试与自动化"的开源 SDK，支持 Android 端。用自然语言描述操作目标，驱动多模态模型规划并操作界面。

```bash
# 入门：安装 Chrome 扩展（浏览器端 Playground），或接入 Android SDK
npm i midscene
# Android 场景：通过 adb 截图 + 视觉模型定位，驱动设备操作
```

**局限**：每一步操作都要调用一次视觉模型做推理，**速度太慢、成本偏高**，不适合批量执行大量用例；且模型强依赖外部服务。

#### 方案2：Appium（功能全，但重量级）
行业标准的移动端自动化框架，需要：

```bash
# 入门：装 Appium Server + Appium 驱动 + 客户端库
npm install -g appium
appium driver install uiautomator2
appium                    # 启动 Appium Server
# 再写脚本通过 WebDriver 协议连上执行
```

**局限**：**每次都要启动 Appium Server + 初始化 driver**，启动慢、依赖重（Node 环境 + Server + driver 三层）；纯 UI 树定位对自定义控件、跨端 H5 页面不够稳，深度定制成本高。

### 3. 结论：自研安卓 UI 自动化执行工具
两条路各有短板：**一个太慢，一个太重**。我们的需求是"既能被自然语言驱动、又要轻快"，所以自研一条中间路线：

> **adb shell 直连设备 + AI 视觉只做"元素定位"一步，操作执行仍走 adb 原生命令。**

+ **快**：不依赖 Appium Server，直接 `adb shell input` 执行点击/滑动/按键，单命令即时执行
+ **轻**：零 Appium 依赖，只要 `adb` 可执行即可，跨平台
+ **AI 可驱动**：元素用自然语言描述（"登录按钮"），AI 视觉返回坐标，天然支持大模型指挥
+ **多设备**：`-s <serial>` 可并行控制多台设备
+ **安卓原生能力全覆盖**：按键、双指缩放、通知栏、UI dump、shell 透传，一套命令全搞定

## 二、技术选型：Appium vs midscene.js vs 自研
### 1. 选型核心考量
安卓用例执行工具要能被 AI 自然语言驱动，同时能批量高效跑用例，需要满足：

+ **AI 能力**：能理解"自然语言描述的元素"并定位
+ **执行速度**：能批量跑大量用例，不能每步都等模型 / 每次启动都等 Server
+ **轻量部署**：依赖越少越好，方便讲师和学生本机直接跑
+ **原生能力**：安卓特有的手势、按键、通知栏、UI dump 都能覆盖

### 2. 三大方案对比
| **对比维度** | **Appium** | **midscene.js** | **自研（adb + AI 视觉）** |
| --- | --- | --- | --- |
| **依赖与部署** | 重：Appium Server + driver + Node | 中：SDK + 视觉模型 | **轻：仅 adb 可执行即可** |
| **AI 视觉能力** | 弱：以 UI 树定位为主 | 有：纯视觉自然语言驱动 | 有：AI 视觉定位元素坐标 |
| **启动/执行速度** | 慢（每次起 Server + driver） | 慢（每步调视觉模型） | **快（直接 adb shell input）** |
| **自然语言驱动** | 不支持，靠脚本选择器 | 支持，但整体流程都走模型 | 支持，AI 描述元素→坐标→原生执行 |
| **批量执行** | 支持，但启动开销大 | 不适合（慢、贵） | 支持 batch 并行识别 + 多设备并行 |
| **安卓原生能力** | 需装 driver / 扩展 | 一般 | **全覆盖（手势/按键/通知栏/shell）** |
| **多设备** | 支持 | 有限 | 支持（-s serial 并行控制） |

### 3. 结论：自研路线
安卓用例执行需要**AI 可驱动 + 轻快 + 原生能力全覆盖**。Appium 太重、midscene.js 太慢，自研方案把"AI 视觉定位"和"adb 原生执行"解耦，既快又能被自然语言指挥，还能无缝嵌入 SKILL 作为底层驱动。

## 三、工具形态设计：命令行 CLI 工具
:::tips
**问题：**那么到底我应该做成什么样子的呢？
:::

我们的核心调用方是 AI（SKILL 底层调用），因此工具需要满足：

+ **AI 易调用**：大模型可直接拼接命令参数，无需图形界面交互
+ **可脚本化**：可编写批量脚本
+ **轻量**：不依赖 Appium Server，单命令即时执行
+ **易集成**：可轻松嵌入 SKILL、流水线、CI 设备集群

所以我们做成命令行工具，通过命令的方式去进行调用：

```bash
xxx --version                          # 显示版本号
xxx --help                             # 显示帮助信息
xxx devices                            # 列出所有 adb 设备
xxx start -s emulator-5554             # 连接指定设备
xxx launch <包名>                      # 启动应用
xxx click <元素描述>                   # AI 视觉点击
xxx input <元素> <文本>                # AI 视觉输入（中文走剪贴板粘贴）
xxx swipe up                           # 滑动
xxx zoom 540 1100 --scale 2.0          # 双指放大（地图等）
xxx keyevent back                      # 按键
xxx screenshot out.png                 # 截图
xxx get <区域描述>                     # AI 读取页面某区域内容
xxx current-app                        # 只读断言（当前前台应用）
xxx batch input 用户名::admin click 登录按钮   # 批量并行
xxx shell <cmd>                        # adb shell 透传
xxx close                              # 回到桌面（保留进程）
xxx stop <包名>                        # 强停应用（冷启动测试）
```

## 四、环境搭建说明
### 基础环境要求
+ Python 3.9+（授课使用 3.11 版本）
+ adb（Android SDK Platform Tools），需在 PATH 中
+ 一台开启 USB 调试的安卓真机 / 模拟器
+ AI 视觉模型 API Key（用于元素定位 / 区域内容识别）

### 详细安装步骤验证
1. **验证 Python 环境**

```bash
python --version
# 确保输出 3.9 及以上
```

2. **验证 adb**

```bash
adb --version    # 应能输出版本号
adb devices      # 能看到设备列表（真机需开 USB 调试 / 模拟器已启动）
```

3. **安装项目**

```bash
cd 项目目录
pip install -e .           # 安装为全局命令（或 pip install -r requirements.txt）
```

4. **配置 AI API（当前工作目录 .env）**

```env
ANDROID_AI_API_KEY=your_api_key_here
ANDROID_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ANDROID_AI_MODEL=qwen-vl-max
```

5. **验证环境**

```bash
xxx --version               # 能看到版本号
xxx devices                 # 能看到在线设备
xxx screenshot test.png     # 能截到设备屏幕
```

## 五、核心功能实现
---

### 版本1：最简原型版 —— CLI 骨架 + 设备连接 + 启动/关闭应用
**目标**：先搭出命令行工具的"骨架"，把版本号、帮助、设备连接、启动/关闭应用跑通，证明「Python CLI 能通过 adb 连接安卓设备、启动并关闭应用」这一核心链路可行。

**做成什么样：**

+ 形态：可全局执行的 Python 命令行工具
+ 核心动作：`--version` 显示版本号 → `--help` 显示命令帮助 → `devices` 列出设备 → `start` 连接设备（自动选择首个或 `-s` 指定）→ `launch` 启动应用 → `close` 回到桌面
+ 所有命令连不上设备时输出友好中文提示，不抛一堆堆栈
+ 关键点：**adb 不在 PATH 要能识别并提示**；多设备场景必须有 `-s` 指定，否则提示用首个

**本环节AI生成提示词**

> 我要做一个能通过命令行控制安卓设备、并且能被 AI 自然语言驱动的 Android UI 自动化执行工具。你帮我一步步实现，先讲背景：
>
> 我们已经有了测试用例（设备端录制工具录的手机操作 + 用例），现在要做"用例执行"这一环——让一个命令行工具能连接安卓设备、启动应用、在页面上点一点、输一输，把测试用例在真机/模拟器上真实跑起来。而且这个工具后面要被大模型调用（用自然语言指挥它操作手机），所以交互要简单直接、输出要结构化。
>
> 技术底座我定了：用 adb 命令直连安卓设备。为什么不用别的：不依赖 Appium Server（太重、启动慢），只要 adb 可执行文件即可；adb shell input 原生支持点击、滑动、按键，跨设备一致。
>
> 用 Python 写，做成本地命令行工具。开发方式：分阶段来，我一个阶段一个阶段告诉你做什么，做完说下做了啥、怎么验证、有没有遗留问题，我确认了再继续。工程结构、文件名你自己拿主意。
>
> 第一阶段，先搭个能跑的 CLI 骨架，目标很小：
> - 装好后能全局敲命令，支持这样几个子命令：
>   - 显示版本号：xxx --version
>   - 显示帮助：xxx --help（列出所有子命令和参数）
>   - 列出设备：xxx devices（adb devices 解析成友好列表）
>   - 连接设备：xxx start（默认选 adb 列表里的第一个设备；-s <serial> 指定）
>   - 启动应用：xxx launch <包名>（可带可选的 Activity 名）
>   - 回到桌面：xxx close（按 Home 键，保留 App 进程）
> - 命令执行前先检查 adb 能不能用、设备在不在线，缺了输出友好提示（比如"未连接到设备，请检查 USB 调试"），不要抛一堆堆栈
> - 全局参数留好：-s/--serial 指定设备、--debug 调试模式，现在用不上也先占位
>
> 做完告诉我怎么验证（连真机或模拟器，devices 看设备、launch 启动一个 App、close 回桌面）。

**本阶段验收**：

```plain
# 显示版本号
xxx --version
xxx --version: 1.0.0

# 显示帮助
xxx --help        # 能看到所有子命令

# 列出设备
xxx devices
V2148A    device    product:V2148A model:... device:...

# 连接设备 + 启动应用
xxx start
xxx launch com.android.settings
[OK] 已启动应用: com.android.settings

# 未连接设备时执行其它命令
xxx click "登录按钮"
[FAIL] 未连接到设备，请检查 USB 调试 / 模拟器是否启动。
```

【图：--version / --help / devices / launch 输出截图】

---

### 版本2：截图 + AI 点击/输入（含中文）
**但是目前还是有需要进行优化：**

1. 只能连设备、起应用，没法操作页面，用例执行无从谈起；中文输入还是安卓的"老大难"。

**做成什么样：**

+ 新增能力：`screenshot` 截图、`click`/`input` **AI 视觉定位**元素坐标后点击/输入
+ 核心逻辑：adb 截图 → 发 AI 视觉模型（返回 **0-1000 归一化坐标**）→ 按设备屏幕尺寸缩放回原生像素 → `adb shell input tap` 执行
+ 中文输入：非 ASCII 一律走**剪贴板 + 粘贴**（`cmd clipboard set-primary-clip` + `keyevent 279 PASTE`），不走拼音 IME、不兜底 `input text`（会乱码）

**本环节AI生成提示词**

> 第二阶段，加入截图、以及"AI 视觉点击/输入"。这是安卓执行的灵魂，先解释核心思路：
> 1. 用 adb 截一张当前屏幕截图（exec-out screencap -p）
> 2. 把截图发给一个 AI 视觉模型（配好 API Key 就能用），同时告诉它"我要点/输入哪个元素（用自然语言描述）"
> 3. 这里有个关键设计：让 AI 返回 **0-1000 的归一化坐标**（不管屏幕是 720p 还是 2K，都归一化），我们再按设备真实屏幕尺寸缩放回原生像素——这样不同分辨率设备共用一套识别逻辑
> 4. 用 adb shell input tap 点击、或点击后输入文本
>
> 具体要求：
> - 命令：xxx screenshot <输出路径>；xxx click <元素描述>；xxx input <元素描述> <要输入的文本>
> - AI Key 通过当前目录的 .env 或环境变量读取（用 python-dotenv），没配就报清晰错误并退出，别反复试
> - 操作前先检查设备在不在线、AI Key 配没配，缺了先报错
> - **中文输入是重点**：非 ASCII 字符（中文、emoji）强制走"剪贴板 + 粘贴"（Android 10+ 用 cmd clipboard set-primary-clip，再发 keyevent 279 粘贴）；**绝对不要用 adb shell input text 兜底**（中文必然乱码，"看似成功但内容乱码"比"明确失败"更危险）。剪贴板方案失败就明确报错退出，提示用户换 ADBKeyboard
> - 每个操作成功/失败都输出 [OK] / [FAIL] 这样的标志，方便 AI 解析
> - click/input 支持可选的 -s 操作后截图、--debug 显示耗时
>
> 做完告诉我怎么验证（比如 launch 一个 App，click 登录按钮，input 搜索框输入中文）。

**本阶段验收**：`launch` 启动 App → `click "搜索框"` 识别并点击 → `input "搜索框" "天心区"` 中文正常粘贴输入 → 无乱码、无逐字蹦。

【图：click + input 中文输入执行截图】

:::warning
不一定一模一样，只需要功能方面是相似的即可。
:::

---

### 版本3：滑动/按键 + 只读断言 + 区域内容读取
**但是目前还是有需要进行优化：**

1. 页面列表滑不动、安卓的返回/主页按键没法按、跑完用例没法断言"当前在哪个界面"、AI 想看页面状态没通道。

**做成什么样：**

+ 新增能力：`swipe` 滑动（支持指定区域聚焦滑动）、`keyevent` 按键（back/home/recents 等 30+ 别名）、`current-app` 只读断言（无 AI）、`get` AI 读取指定区域内容（布局/图标/文字/介绍）
+ 核心逻辑：滑动带区域时先用 AI 识别区域 bbox，在区域内拖拽滑动；`current-app` 通过 `dumpsys` 读当前前台 package/activity；`get` 返回结构化描述，让不支持多模态的大模型也能"看懂"页面

**本环节AI生成提示词**

> 第三阶段，补上"滑动、按键、看页面状态"三类能力，这些都是安卓用例里的高频动作。
>
> 1. 滑动：xxx swipe <方向 up/down/left/right> [-c 次数] [-s 截图] [--region 区域描述] [--distance 距离比例]
>    - 不指定区域：整屏滑动（adb shell input swipe 按屏幕比例算起点终点）
>    - 指定区域：先用 AI 视觉识别区域坐标（bbox），在区域内部滑动（不然滑的是整个屏幕）
>    - 显式坐标滑动：xxx swipe-to x1 y1 x2 y2 --duration 300（给精确定位场景）
> 2. 按键：xxx keyevent <code|别名>，支持 back/home/menu/recents/enter/volume_up 等 30+ 别名，也支持数字键码（keyevent 4 = back）
>    - 另外做两个专用命令：xxx recents（最近任务）、xxx notifications（下拉通知栏）
> 3. 只读断言（不需要 AI，快）：xxx current-app 输出当前前台应用的 package/activity（单行）；支持 --format json 输出 {"package": "...", "activity": "..."}，方便脚本断言。实现用 dumpsys activity/window 解析
> 4. 区域内容读取：xxx get <区域描述> [-s 截图]
>    - 用 AI 视觉描述页面上某个区域：布局(layout)、图标(icons)、文字(text)、介绍(intro) 四部分，不返回坐标
>    - 用途：AI 判断页面状态、验证操作结果、读取动态列表内容
>
> 做完给我一份验证清单（滑动不同方向、keyevent 返回主页、current-app 断言、get 描述页面区域）。

**本阶段验收**：长列表 `swipe up --region "新闻列表"` 正常滑动；`keyevent back` / `home` / `recents` 生效；`current-app` 输出准确；`get "登录表单区域的内容"` 返回结构化描述。

【图：swipe / keyevent / current-app / get 输出截图】

---

### 版本4：标准生产版 —— 批量并行 + 长按/双指 + 设备调试
**但是目前还是有需要进行优化：**

1. 登录表单要输用户名、密码、点登录，一个个操作太慢；地图类要双指缩放；排查问题要 UI dump、看应用信息、透传 shell；冷启动测试要杀进程。

**做成什么样：**

+ 新增能力：`batch` 批量命令（一次截图并行识别多个元素再逐个执行）、`longpress` 长按、`zoom` / `pinch` 双指缩放（并行两条 swipe 近似实现）、`shell` 透传、`dump-ui` / `appinfo` 调试、`stop` 强停应用、`-s` 多设备
+ 性能优化：AI 识别截图默认用 JPEG；`--debug` 显示各步骤耗时统计
+ 核心逻辑：batch 把"截图一次 + 并行识别 + 顺序执行"串起来，大幅提速；多设备用进程级并行

**本环节AI生成提示词**

> 第四阶段，做性能和生产性优化，让工具能真正批量跑用例：
>
> 1. 批量命令：xxx batch click "登录按钮" input "用户名输入框"::admin input "密码输入框"::123456
>    - 同一页面多个操作只截一次图，多个元素描述一起发给 AI 并行识别坐标，再按顺序逐个执行（注意：batch input 可先用屏幕中心作为输入位置，若输入框不在中央则让用户改用 input 单独定位）
> 2. 长按：xxx longpress <元素描述> --duration 1500（AI 定位后按住不放）
> 3. 双指缩放：xxx zoom x y --scale 2.0 / xxx pinch x y --scale 0.5
>    - 通过两个线程并行执行两条 adb shell input swipe 模拟双指；这是"近似"实现，少数机型可能识别为两次单指，文档里注明
> 4. 调试三件套：xxx shell <任意 adb shell 命令>（透传）、xxx dump-ui <输出.xml>（保存 uiautomator dump）、xxx appinfo <包名>（dumpsys package）
> 5. 停止应用：xxx stop <包名>（am force-stop，杀进程，用于冷启动测试）——注意要和 close（Home 键回桌面、保留进程）区分开
> 6. 多设备：所有命令都支持 -s <serial> 指定设备，可并行控制多台
> 7. 性能：AI 识别截图默认用 JPEG（screencap 后压缩）；提供 --debug 显示各步骤耗时统计
>
> 做完给一份性能对比验证（串行 vs batch）和冷启动验证（stop + launch）。

**本阶段验收**：`batch` 一次完成登录表单填写 + 提交；`zoom`/`pinch` 地图缩放生效；`shell`/`dump-ui`/`appinfo` 调试输出正常；`stop` + `launch` 走冷启动；`-s` 多设备各操作各的。

【图：batch 命令输出 + 耗时统计截图】

## 六、SKILL 层封装开发
工具做出来后，要封装成 SKILL 让 AI 真正"会用它"。这一层解决三个问题：**什么情况该用它、怎么指挥它、环境坏了怎么办**。

### 第一步：梳理 SKILL 完整执行流程
1. **环境前置检查（必须，缺一不可）**
   - AI Key 是否配置（`.env` / 环境变量，`ANDROID_AI_API_KEY`）——缺了先停下来让用户补，不要反复重试报错
   - adb 是否可用（`adb --version`）；设备是否在线（`xxx devices`）
   - 多设备场景必须先确认用哪台，用 `-s <serial>` 指定，不要操作随机设备
2. **设备选择策略**
   - 默认自动选择 `adb devices` 列表第一个；多设备必须 `-s` 指定
   - 操作前建议先 `devices` 确认目标设备在线
3. **页面分析策略**
   - 不要每一步都 `get` 查看页面：分析一次后**记住当前页面有哪些可执行步骤**，执行完这几步再用 `get` 看最新状态
   - 仅在元素找不到、需要确认页面内容、需要验证业务结果时才 `get`
4. **操作执行**
   - 元素描述遵循「**元素类型 + 目标**」规范：`登录按钮`、`员工姓名输入框`、`部门下拉选项`、`同意协议复选框`、`提交按钮`、`设置菜单项`（菜单项必须以"菜单项"结尾，与底部 tab 区分）
   - 中文输入强制走剪贴板+粘贴，**不要用 `adb shell input text` 兜底**
   - 离开 App：之后还要回来用 `close`；测试冷启动用 `stop + launch`
   - 下拉框用**三步查找法**：点开下拉框 → `get` 确认选项 → `click` 目标选项；找不到再滑动 / 搜索过滤
5. **结果验证与返回**
   - 返回：操作结果（[OK]/[FAIL]）、当前前台应用、区域内容描述
   - 询问用户下一步：继续执行 / 生成测试报告 / 记录结果

SKILL 交互示例

```plain
用户：用 bigbear-android-cli 在这个 App 里搜索"天心区"的房子
SKILL：环境检查通过（设备 V2148A 在线），正在启动贝壳找房...
       → xxx launch com.lianjia.beike
       → click "搜索输入框"
       → input "搜索输入框" "天心区"     # 中文走剪贴板粘贴
       → get "搜索结果列表"
SKILL：搜索完成！共 12 条结果，第一条是"天心区 XX 小区"。需要我继续下一步吗？
```

### 第二步：生成对应的 SKILLS
1. 遵循技能规范：生成技能时，务必遵守标准规范，以确保其他工具都能直接调用使用。详细规范请参考：Skill 规范（skill-creator / 平台技能规范）

2. 在当前项目路径下创建一个技能目录（如 `.claude/skills` 或对应平台的技能目录）

3. 把如上梳理的流程告诉 AI，让它按规范生成 SKILL 描述（触发场景、输入参数、执行步骤、输出产物）

**本环节AI生成提示词**

> 工具做完了，帮我把这个工具变成一个 AI 可以自动调用的技能（SKILL）：
>
> 写清楚：什么时候该用它、要什么输入、会输出什么。调用流程大概这样：
> 1) 先做环境前置检查：AI Key 配没配、adb 能不能用、设备在不在线；多设备必须先确认用哪台（-s 指定）；任何一项不通过就停下来让用户处理，不要反复重试
> 2) 执行操作前先记下当前页面的可执行步骤，不要每一步都重新分析页面（浪费）
> 3) 元素描述要规范：元素类型 + 目标（登录按钮、员工姓名输入框、部门下拉选项、设置菜单项）
> 4) 中文输入强制走剪贴板+粘贴，不要用 adb shell input text 兜底（会乱码）
> 5) 离开 App：还要回来用 close，测冷启动用 stop + launch，两者别混
> 6) 同一页面多个操作优先用 batch；下拉框用"点开→查看→点击"三步法
> 7) 操作完用 current-app / get 验证结果，把 [OK]/[FAIL]、当前页面状态返回给用户
>
> 别贴大段源码，写成"调用说明"就行。过程中要用户做决定的时候，停下来问。

### 第三步：测试与验证
+ 真机测试：连接真机 → 启动被测 App → 用自然语言让 AI 完成"搜索/登录/滑动"等真实流程
+ 验证环境异常处理：故意不配 AI Key、adb 不在 PATH、设备未连接，看 SKILL 是否停下来正确提示
+ 用自然语言触发 SKILL，验证是否能正确提取参数、调用工具、返回结果

**重新打开一个 Agent 对话框**，查看是否能正确的驱动起来。

## 七、整体测试与验证
### 自动化测试（pytest）
项目内置 pytest 测试用例覆盖核心能力（77 个用例）：

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

覆盖点：设备管理（test_adb）、动作执行（test_actions：点击/滑动/按键/缩放）、AI 控制（test_ai_control）、环境加载、坐标点击。

### 真机手工验收清单（真机 V2148A + 贝壳找房）
1. `xxx --version` 显示版本号；`xxx --help` 显示帮助
2. `xxx devices` 检测到真机（如 V2148A，1080x2400）
3. `xxx start` 自动选择设备并获取屏幕尺寸
4. `xxx screenshot screen.png` 全屏截图保存
5. `xxx launch com.lianjia.beike` 启动贝壳找房
6. `xxx click "地图找房"` AI 识别并点击
7. `xxx swipe up/down` 地图上下平移；`xxx zoom 540 1100 --scale 2.0` 双指放大
8. `xxx input "搜索输入框" "天心区"` 中文输入正常，自动跳转
9. `xxx keyevent back` 返回首页；`xxx keyevent home` / `xxx recents` / `xxx notifications` 正常
10. `xxx get "搜索结果列表"` 返回结构化描述
11. `xxx current-app` 断言当前前台应用（package/activity）正确
12. `xxx batch click "登录按钮" input "用户名输入框"::admin ...` 一键完成表单
13. `xxx dump-ui ui.xml` 保存 UI 层次；`xxx appinfo <包名>` 输出应用信息
14. `xxx close` 回桌面（进程保留）；`xxx stop <包名>` + `xxx launch` 走冷启动
15. 重新打开 Agent 对话框，用自然语言完整跑一遍"搜索"流程

### 常见问题与排查
| 现象 | 排查 |
| --- | --- |
| 报"未连接到设备" | 检查 USB 调试是否开启、`adb devices` 是否识别；模拟器是否已启动 |
| 报"请设置 ANDROID_AI_API_KEY" | 在 `<cwd>/.env` 配置 AI Key，或注入系统环境变量；不要反复重试 |
| 中文输入乱码 | 确认走的是剪贴板+粘贴；若设备 Android < 10 或 ROM 阉割剪贴板（vivo/OPPO/华为/小米），会明确报错，按提示装 ADBKeyboard |
| 元素识别失败 / 点错位置 | 元素描述加"元素类型+目标"（如"顶部的搜索输入框"）；多设备要 `-s` 指定；截图里出现系统 Toast 时描述里忽略它 |
| 双指缩放没效果 | 是近似实现，少数机型识别为两次单指；换机型或用 swipe-to 手动模拟 |
| 报 Engine Busy（讯飞 MaaS） | 服务端问题，AI 已重试 3 次后报错；换支持视觉的模型（如 qwen-vl-max） |
| batch input 输入位置不对 | batch input 当前以屏幕中心作为输入位置；输入框不在中央时改用 input 单独定位 |
