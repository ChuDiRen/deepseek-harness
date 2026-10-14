# BigBear Android CLI

基于 **adb 命令** 与 **AI 视觉大模型** 的 Android 设备控制 CLI 工具。轻量、零 Appium 依赖、单命令即时执行。

## 功能

### 镜像自 bigbear-web-cli
- 📱 **连接设备** — 自动选择首个 adb 设备（或 `-s <serial>` 指定）
- 🚀 **启动应用** — `launch <package> [activity]`
- 👆 **AI点击** — 通过 AI 视觉识别元素并点击
- ⌨️ **AI输入** — 通过 AI 视觉定位元素并输入文本
- 👆 **滑动** — 上下左右滑动页面
- 📸 **截图** — 截取设备屏幕
- 🏠 **回到桌面** — 关闭当前应用
- 🔍 **AI获取内容** — 获取指定区域文本
- ⚡ **批量操作** — 并行 AI 识别 + 批量执行

### Android 扩展
- 📋 **设备列表** — `devices` 列出所有 adb 设备
- 🔘 **按键** — `keyevent <code|name>` 支持 back/home/recents/menu/enter 等 30+ 别名
- 👇 **长按** — `longpress <element>`
- ↔️ **显式滑动** — `swipe-to <x1> <y1> <x2> <y2>`
- 🤏 **双指缩放** — `pinch` / `zoom` 通过并行 `input swipe` 实现地图类应用的双指手势
- 🪟 **最近任务** — `recents` / `keyevent recents` 打开应用快速切换界面
- 🔔 **通知栏** — `notifications` 下拉通知栏 + 快捷开关
- 🛠️ **shell 透传** — `shell <cmd>` 直接执行 adb shell
- 📜 **UI 层次** — `dump-ui <output>` 保存 uiautomator dump
- 📦 **应用信息** — `appinfo <package>` dumpsys package
- 🎯 **当前前台** — `current-app` 通过 dumpsys activity / window 读取 package + activity
- 💡 **屏幕控制** — `wake` / `sleep` 唤醒/休眠

## 安装

### 方式一：安装为全局命令（推荐）

```bash
cd bigbear-android-cli
pip install -e .
```

确保 `adb` 在 PATH 中（Android SDK Platform Tools）：
```bash
adb --version  # 应能输出版本号
```

安装后即可全局使用 `bigbear-android-cli`：
```bash
bigbear-android-cli devices
bigbear-android-cli click "登录按钮"
bigbear-android-cli input "搜索框" "关键词"
bigbear-android-cli swipe up
bigbear-android-cli screenshot output.png
```

### 方式二：直接运行

```bash
cd bigbear-android-cli
pip install -r requirements.txt

python -m bigbear_android devices
```

## 配置

复制 `.env.example` 为 `.env` 并配置 AI API：

```bash
cp .env.example .env
```

```env
ANDROID_AI_API_KEY=your_api_key_here
ANDROID_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ANDROID_AI_MODEL=qwen-vl-max
```

CLI 继承系统环境变量，并且只读取执行命令时当前工作目录下的 `.env`。系统环境变量优先于 `.env` 中的同名变量；CLI 不会搜索用户目录、安装目录、父目录或其他工作区目录。

## 使用方法

### 常用命令

**设备管理**
```bash
bigbear-android-cli devices
bigbear-android-cli start -s emulator-5554
```

**启动应用**
```bash
bigbear-android-cli launch com.android.settings
bigbear-android-cli launch com.example.app .MainActivity
```

**AI 点击**
```bash
bigbear-android-cli click "登录按钮"
bigbear-android-cli click "页面顶部的搜索框" -s output.png
```

**AI 输入**
```bash
bigbear-android-cli input "搜索框" "hello world"
bigbear-android-cli input "评论框" "你好世界"  # 中文自动剪贴板/ADBKeyboard 回退
```

**滑动**
```bash
bigbear-android-cli swipe up
bigbear-android-cli swipe down -c 3
bigbear-android-cli swipe up --region "新闻列表"  # AI 识别区域后聚焦滑动
```

**显式坐标滑动**
```bash
bigbear-android-cli swipe-to 500 1500 500 500 --duration 300
```

**双指缩放（地图等场景）**
```bash
bigbear-android-cli zoom 540 1100 --scale 2.0   # 双指放大 2 倍
bigbear-android-cli pinch 540 1100 --scale 0.5  # 双指缩小
```

**长按**
```bash
bigbear-android-cli longpress "图标" --duration 1500
```

**按键**
```bash
bigbear-android-cli keyevent back
bigbear-android-cli keyevent home
bigbear-android-cli keyevent recents   # 最近任务 / 应用切换
bigbear-android-cli keyevent menu     # 菜单
bigbear-android-cli keyevent enter
bigbear-android-cli keyevent 4        # 等同于 keyevent back
bigbear-android-cli recents           # 专用命令，等同 keyevent 187
bigbear-android-cli notifications     # 下拉通知栏
```

**截图**
```bash
bigbear-android-cli screenshot screen.png
```

**UI 层次**
```bash
bigbear-android-cli dump-ui ui.xml
```

**应用信息**
```bash
bigbear-android-cli appinfo com.android.settings
```

**当前前台应用**
```bash
bigbear-android-cli current-app                      # 单行：com.example.app/.MainActivity
bigbear-android-cli current-app --format json        # {"package": "...", "activity": "..."}
```

**批量操作**
```bash
bigbear-android-cli batch click "登录按钮" input "搜索框"::"hello" longpress "头像"
```

**shell 透传**
```bash
bigbear-android-cli shell ls /sdcard/
bigbear-android-cli shell pm list packages
```

**屏幕控制**
```bash
bigbear-android-cli wake
bigbear-android-cli sleep
```

## 项目结构

```
bigbear-android-cli/
├── pyproject.toml              # 打包配置
├── requirements.txt            # 依赖列表
├── .env.example                # 配置示例
├── README.md                   # 本文件
├── src/
│   └── bigbear_android/
│       ├── __init__.py         # 包初始化
│       ├── __main__.py         # python -m bigbear_android 入口
│       ├── cli.py              # argparse 入口 + 命令处理
│       ├── adb.py              # ADBManager（设备管理）
│       ├── actions.py          # AndroidActions（点击/滑动/按键）
│       ├── ai_control.py       # AI 视觉控制
│       └── prompts/            # AI 提示词模板
│           ├── single_element.txt
│           ├── batch_elements.txt
│           └── content_analysis.txt
└── tests/                      # 单元测试
    ├── test_adb.py
    ├── test_actions.py
    └── test_ai_control.py
```

## 工作原理

1. **设备连接**：通过 `subprocess` 调用 `adb devices -l` 获取设备列表，自动选择首个或指定 `-s` 设备
2. **截图获取**：执行 `adb -s <serial> exec-out screencap -p` 获取 PNG 字节流，压缩为 JPEG base64
3. **AI 识别**：将截图发送给 AI 视觉模型，模型返回 0-1000 归一化坐标
4. **坐标转换**：按设备屏幕尺寸缩放回原生像素
5. **操作执行**：通过 `adb -s <serial> shell input <args>` 执行点击/滑动/按键

## 与其他工具对比

| 维度 | bigbear-web-cli | bigbear-mobile-cli | **bigbear-android-cli** |
|------|---------------|------------------|----------------------|
| 协议 | Playwright CDP | Appium WebDriver | **adb shell** |
| 平台 | 浏览器 | Android/iOS | **仅 Android** |
| 启动速度 | 慢（启动浏览器） | 慢（启动 Appium） | **快（直接 adb）** |
| 依赖 | Chrome + Playwright | Appium Server + driver | **adb 可执行即可** |
| AI 视觉 | ✓ | ✓ | **✓** |
| 多设备 | ✗ | ✓ | **✓（-s serial）** |

`bigbear-android-cli` 不是 `bigbear-mobile-cli` 的替代品，而是**轻量级互补**：当场景只需要 adb 原生能力时，本工具更轻更快。

## 测试

```bash
pip install -e ".[dev]"
pytest tests/      # 77 个单元测试，全部通过
```

## 真机验证（V2148A + 贝壳找房）

| 命令 | 状态 | 验证场景 |
|---|---|---|
| `devices` | ✅ | 检测到 V2148A (1080x2400) |
| `start` | ✅ | 自动选择首个设备，获取屏幕尺寸 |
| `screenshot` | ✅ | 全屏截图保存 |
| `shell pm list packages \| grep beike` | ✅ | 找到 `com.lianjia.beike` |
| `launch` | ✅ | 启动贝壳找房 |
| `click` (AI) | ✅ | 识别"地图找房" → (918.5, 196.8) |
| `swipe up/down` (方向) | ✅ | 地图上下平移 |
| `swipe-to` (坐标) | ✅ | 任意方向拖拽 |
| `zoom` (双指放大) | ✅ | scale=2.0 地图放大到街道级 |
| `pinch` (双指缩小) | ✅ | scale=0.5 地图缩小到区域级 |
| `input` (AI 中文输入) | ✅ | 搜索框输入"天心区"，自动跳转 |
| `keyevent back` | ✅ | 返回首页 |
| `keyevent home` / `keyevent recents` / `recents` | ✅ | 桌面 / 最近任务（看到贝壳地图卡片） |
| `notifications` | ✅ | 下拉通知栏（WiFi/蓝牙/通知列表） |
| `dump-ui` | ✅ | 保存 38KB UI 层次 XML |
| `appinfo` | ✅ | dumpsys package 完整输出 |
| `shell dumpsys window` | ✅ | 透传确认当前 Activity 为 MapShowHouseActivity |

## 已知限制

- `astron-code-latest`（讯飞 MaaS）偶发 `Engine Busy` 错误——服务端问题，AI 重试 3 次后明确报错退出。如频繁触发可换支持视觉的模型（如 `qwen-vl-max`）
- 双指缩放是"近似"实现：通过并行两个 `adb shell input swipe`（threading）。少数机型/系统可能识别为两次单指，缩放失败
- `longpress` 在贝壳地图空白处长按无效果——这是应用本身不响应，非工具问题

## 中文输入机制

`input` 命令对非 ASCII 文本（中文、emoji 等）采用**两段式策略**，自动选择可行的方案：

1. **剪贴板方案**（首选）：`cmd clipboard set-primary-clip` + KEYCODE_PASTE。
   - 适用：标准 Android 10+（Pixel、Galaxy、原生 AOSP 等）
   - 不适用：vivo（OriginOS/FuntouchOS）、OPPO（ColorOS）、华为（HarmonyOS/EMUI）、小米（HyperOS/MIUI）
     等定制 ROM —— 这些系统**阉割了 `cmd clipboard` 的实现**，但仍返回 rc=0。本工具会通过
     `cmd clipboard get-primary-clip` **读回校验**，发现不可用时立刻回退。
2. **ADBKeyboard 方案**（自动回退）：下载安装 [senzhk/ADBKeyBoard](https://github.com/senzhk/ADBKeyBoard)，
   临时切换到该 IME，通过 `am broadcast -a ADB_INPUT_TEXT --es msg "..."` 发送文本。
   - 首次使用需联网下载 APK（缓存到 `~/.cache/bigbear-android-cli/ADBKeyboard.apk`）
   - **安装过程是静默自动的**，完成后恢复用户原 IME
   - 适用于所有 Android 版本和 ROM（行业标准方案）
   - ADBKeyboard 源码为 GPL-2.0，本工具不修改它，仅通过 adb shell 调用

如果两种方案都失败，会抛出明确的 RuntimeError 而不是静默假装成功。

### 手动跳过自动安装

如不希望自动下载 ADBKeyboard，可先手动安装：

```bash
adb install ADBKeyboard.apk  # 从 GitHub 下载
adb shell ime enable com.android.adbkeyboard/.AdbIME
adb shell ime set com.android.adbkeyboard/.AdbIME
```

## 参考

- 设计文档：`../docs/superpowers/specs/2026-06-22-bigbear-android-cli-design.md`
- 命令风格参考：`../bigbear-web-cli/`
- AI 视觉逻辑参考：`../bigbear-web-cli/src/bigbear_web/ai_control.py`
- ADBKeyboard 项目：<https://github.com/senzhk/ADBKeyBoard>