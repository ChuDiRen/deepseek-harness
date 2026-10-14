# bigbear-android-cli 输入数据 Demo（0基础版）

> 目标读者：**第一次接触 adb / Android 自动化 / 移动端 AI 视觉的同学**。
>
> 这个工具和 `bigbear-web-cli` 思路完全一样，只是底座从「Chrome + Playwright」换成了「Android 设备 + adb」。

---

## 0. 这个 demo 包含什么

```
demo/
├── README.md                  ← 你正在看的文件
├── demo_hardcoded.py          ← Demo 1：固定坐标版（不用 AI，最容易懂）
├── demo_ai_input.py            ← Demo 2：AI 找元素版（完整流程，需要 API Key）
├── demo_step_by_step.py       ← Demo 3：拆成 7 步，每步独立可跑
├── requirements.txt           ← 依赖清单
└── .env.example               ← 配置示例
```

**学习路径**：

```
Demo 1（固定坐标） → Demo 3（拆解每一步） → Demo 2（AI 版）
     ↑                  ↑                    ↑
   跑通就行          理解原理            学会用 AI
```

---

## 1. 和 web 版的对应关系

把「浏览器自动化」换成「Android 自动化」后，整个链路一一对应：

```
                 ┌──────────────────────────────────┐
                 │  CLI / Python 脚本              │
                 │  cli.py / demo_*.py            │
                 └──────────────┬─────────────────┘
                                │
       ┌────────────────────────┼──────────────────────┐
       ▼                        ▼                      ▼
 ┌──────────────┐         ┌─────────────┐         ┌──────────────┐
 │  ADB         │         │  AI 视觉     │         │  Actions     │
 │  adb.py      │         │  ai_control │         │  actions.py  │
 │              │  ─截图→ │             │  ─坐标→  │             │
 │ • adb devices│  bytes  │ • 套 prompt │  (x,y)  │ • tap       │
 │ • screencap  │         │ • 调 LLM    │         │ • input     │
 │ • wm size    │         │ • 解析 bbox │         │ • swipe     │
 │ • shell input│         │ • 重试 3 次 │         │ • keyevent  │
 └──────────────┘         └─────────────┘         └──────────────┘
```

---

## 2. 0 基础需要先知道的概念

### 2.1 adb 是什么

> **Android Debug Bridge**——Google 官方的「Android 设备命令行工具」。装在 PC 上，可以控制 USB/WiFi 连过来的 Android 设备。

```bash
# 安装
# Windows: 下载 https://developer.android.com/tools/releases/platform-tools
#          把 platform-tools 加到 PATH
# macOS:   brew install android-platform-tools
# Linux:   sudo apt install adb

# 验证
adb version          # 应能输出版本号
adb devices          # 应能看到连接的设备
```

### 2.2 adb 常用操作（先混个脸熟）

| adb 命令 | 干嘛的 |
|---|---|
| `adb devices` | 列出所有连接的设备 |
| `adb shell screencap -p /sdcard/s.png` | 截屏到设备 |
| `adb shell input tap 500 1000` | 点击屏幕坐标 (500, 1000) |
| `adb shell input swipe 500 1000 500 500` | 从 (500,1000) 滑到 (500,500) |
| `adb shell input text "hello"` | 输入文本（空格用 `%s`） |
| `adb shell input keyevent 4` | 按返回键 |
| `adb shell wm size` | 看屏幕分辨率 |
| `adb shell am start -n <pkg>/<activity>` | 启动应用 |

### 2.3 Android 设备怎么连

1. **USB 连接**：
   - 手机开「USB 调试」（开发者选项 → USB 调试）
   - 用数据线连电脑
   - 手机弹窗点「允许 USB 调试」
   - `adb devices` 看到设备序列号

2. **WiFi 连接**（进阶）：
   - `adb tcpip 5555`
   - `adb connect <手机IP>:5555`

3. **模拟器**：
   - 启动 Android Studio 模拟器
   - 自动会出现 `emulator-5554`

> Demo 默认会选第一个 device，多个设备可用 `-s <serial>` 指定。

### 2.4 坐标系统：直接用屏幕像素

- 屏幕尺寸通过 `adb shell wm size` 获取，比如 `1080x2400`
- **AI 返回的 bbox 也是 0-1000 归一化**，还原成像素：`bbox × (size/1000)`
- Android **不需要 DPR 校正**（不像浏览器有 devicePixelRatio）

### 2.5 中文输入比 web 麻烦

`adb shell input text` 只能输入 ASCII。中文要走两条路：

| 方案 | 适用 | 命令 |
|---|---|---|
| **剪贴板** | 标准 Android 10+ | `adb shell cmd clipboard set-primary-clip "..."` + `keyevent 279`（粘贴） |
| **ADBKeyboard** | 所有 ROM（兜底） | 安装第三方 IME，用广播 `am broadcast -a ADB_INPUT_TEXT --es msg "..."` |

Demo 里走剪贴板方案（多数现代设备 OK），vivo/ColorOS/HyperOS 等定制 ROM 会自动回退到 ADBKeyboard。

---

## 3. 环境准备（必做）

### 3.1 装 adb

去 [Google Platform Tools](https://developer.android.com/tools/releases/platform-tools) 下载，解压后把目录加到 PATH。

验证：

```bash
adb version
adb devices    # 应该能看到你的设备（至少一台）
```

### 3.2 装 Python 依赖

```bash
cd apps/bigbear-android-cli/demo

# 装依赖
pip install -r requirements.txt
```

### 3.3 配 .env（Demo 2 / Demo 3 需要）

```bash
cp .env.example .env
```

打开 `.env`，填入：

```env
ANDROID_AI_API_KEY=sk-你的阿里云key
ANDROID_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ANDROID_AI_MODEL=qwen-vl-plus
```

> **没有 API Key？** 先跑 Demo 1 和 Demo 3 的 Step 1-3（不调 AI）。

---

## 4. Demo 1：固定坐标版（最先跑这个）

### 4.1 它做了什么

```
adb 连设备 → 截图保存 → 在固定坐标 tap → 用 adb input text 输入文字 → 再截图
```

**全程不调 AI**，坐标是写死的。

### 4.2 运行

```bash
python demo_hardcoded.py
```

### 4.3 预期输出

```
[DEMO1] 第 1 步：检测 adb 设备 ...
[DEMO1]   ✓ 发现设备: emulator-5554
[DEMO1] 第 2 步：获取屏幕尺寸 ...
[DEMO1]   ✓ 屏幕尺寸: 1080 x 2400
[DEMO1] 第 3 步：截图（操作前） → output/01_before.png
[DEMO1] 第 4 步：在坐标 (540, 1200) tap 一下 ...
[DEMO1] 第 5 步：输入文本 'hello adb' ...
[DEMO1] 第 6 步：截图（操作后） → output/02_after.png
[DEMO1] 完成！请打开 output/02_after.png 查看效果
```

### 4.4 怎么看结果

打开 `output/02_after.png`，能看到：
- 屏幕某个位置被点了一下
- 如果你点中了一个输入框，会出现 "hello adb" 文字

> **如果点偏了**：用 `output/01_before.png` 对照坐标（屏幕 1080×2400 的中心点是 540,1200）。

---

## 5. Demo 2：AI 找元素版

### 5.1 它做了什么

```
adb 连设备 → 截图 → AI 视觉找"搜索框" → 还原坐标 → tap + 输入
```

### 5.2 运行

```bash
python demo_ai_input.py
```

### 5.3 预期输出

```
[DEMO2] 读配置 ...
[DEMO2]   Model: qwen-vl-plus
[DEMO2] 第 1 步：检测设备 ...
[DEMO2]   ✓ 设备: emulator-5554, 屏幕 1080x2400
[DEMO2] 第 2 步：截图 ...
[DEMO2] 第 3 步：调 AI 找'搜索框' ...
[DEMO2]   AI 响应：{"found": true, "bbox": [240, 178, 960, 253]}
[DEMO2]   还原后坐标：(648, 260)
[DEMO2] 第 4 步：在 (648, 260) tap + 输入 'Playwright 真好用' ...
[DEMO2] 第 5 步：截图（操作后） → output/ai_after.png
[DEMO2] 完成！
```

---

## 6. Demo 3：逐步拆解版

把流程拆成 7 步，**每步独立可跑**。在 `demo_step_by_step.py` 文件最末尾选择要跑哪个 step：

| Step | 函数 | 学到什么 |
|---|---|---|
| 1 | `step_1_check_adb()` | adb 路径、设备列表 |
| 2 | `step_2_screen_size()` | 怎么拿屏幕分辨率 |
| 3 | `step_3_screenshot()` | 截图怎么转 PIL + base64 |
| 4 | `step_4_call_ai()` | AI 接口怎么调，0-1000 怎么还原 |
| 5 | `step_5_tap()` | `adb shell input tap` |
| 6 | `step_6_input_text()` | `adb shell input text` + 中文剪贴板 |
| 8 | `step_8_full_pipeline()` | 完整流程 |

---

## 7. 三种错误排查

### 错误 1：`adb: command not found`

```
adb 不是内部或外部命令
```

解决：装 Android Platform Tools，加 PATH。

### 错误 2：`adb devices` 看不到设备

```
List of devices attached
（空）
```

解决：
1. USB 调试开了吗？（开发者选项 → USB 调试）
2. 数据线连好了吗？试换一个 USB 口
3. 手机弹窗点「允许 USB 调试」
4. 装驱动（Windows 经常要装手机厂商驱动）

### 错误 3：AI 返回 None

参考[bigbear-web-cli 的同样问题](../bigbear-web-cli/demo/demo_ai_input.py)——多数情况是 **.env 里模型不是视觉模型**，改成 `qwen-vl-plus` / `qwen-vl-max` / `gpt-4o`。

---

## 8. 与 web 版 demo 的对比

| 维度 | web demo | android demo |
|---|---|---|
| **底座** | Chrome + Playwright | Android 设备 + adb |
| **截图** | `page.screenshot()` | `adb shell screencap -p` |
| **点击** | `page.mouse.click()` | `adb shell input tap x y` |
| **中文输入** | `keyboard.insert_text()` | 剪贴板 + ADBKeyboard |
| **多设备** | ❌ 单例浏览器 | ✅ `-s <serial>` 多设备并行 |
| **启动速度** | 慢（启 Chrome） | 快（adb 即时） |
| **依赖** | Chrome 浏览器 | adb 可执行即可 |

---

## 9. 下一步学什么

跑通 3 个 demo 后：

1. **看正式源码**：[src/bigbear_android/adb.py](../src/bigbear_android/adb.py) — 完整的 adb 封装
2. **看正式源码**：[src/bigbear_android/actions.py](../src/bigbear_android/actions.py) — 点击/滑动/输入/按键
3. **看正式源码**：[src/bigbear_android/ai_control.py](../src/bigbear_android/ai_control.py) — AI 视觉逻辑（和 web 版几乎一样）
4. **多设备实战**：试试用 `-s emulator-5554 -s <另一台serial>` 是不是真能并行

---

## 附：3 个 demo 对比

| 维度 | Demo 1 (hardcoded) | Demo 2 (AI) | Demo 3 (step-by-step) |
|---|---|---|---|
| **难度** | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| **需要 API Key** | ❌ | ✅ | Step 4/8 需要 |
| **需要真实设备** | ✅ | ✅ | Step 5+ 需要 |
| **代码长度** | 80 行 | 120 行 | 200 行 |
| **运行时间** | 5 秒 | 10 秒（含 AI） | 按 step 跑，每步 3-5 秒 |