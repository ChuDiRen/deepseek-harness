---
name: bigbear-android-record
description: Use when working with "bigbear-device-record --platform android", "bigbear-android-record", "华测安卓采集", "安卓录制", "Android画面采集", or capturing Android device snapshots with module/func/desc tags via ADB + Midscene.
version: 1.0.0
---
重点： 请使用中文沟通！！

# BigBear Android Record

华测 Android 设备画面采集工具，基于 `bigbear-device-record --platform android`，通过 `adb` 发现设备 + Midscene (`@midscene/android@1`) 截屏，输出与 `bigbear-web-record` 兼容的 JSON 快照（截图 + UI 层次 + 可选 vision 分析）。

## 使用场景

- **App 界面录制**：采集 Android 设备当前 App 画面与 UI 层次
- **需求文档**：结合多模态 AI 生成 App 界面需求
- **测试点分析**：基于录制内容分析测试点

## 默认行为

- **视觉 AI 分析**：默认就是开启的（`--enable-vision`），除非用户**明确说不开启**才传 `--no-enable-vision` 关闭
- **实时投屏帧率**：默认 `2fps`，除非用户**明确说要调整**才传 `--fps` 自定义
- **输出目录**：默认 `./AI-信息采集`（**本工具应在项目根目录下运行**，如 `WEB功能测试/`、`Android测试/`，输出会直接落到项目根下的 `AI-信息采集/` 中），除非用户**明确指定**才传 `--output` / `-o`
- **浏览器**：默认自动打开，除非用户**明确要求**不打开才传 `--no-browser`

## Usage

```bash
# 1) 确认设备已连接
adb devices -l

# 2) 启动采集（自动选第一台设备，默认已开启视觉 AI 分析、帧率 2fps）
#    注意！除非用户明确指定，不要配置 --output
bigbear-device-record record --platform android --enable-vision

# 指定具体设备
bigbear-device-record record --platform android --device-id emulator-5554 --enable-vision

# 指定输出目录（注意！除非用户明确指定，不要配置 output）
bigbear-device-record record --platform android --output ./output --enable-vision

# 关闭视觉 AI 分析（仅当用户明确要求不开启时使用）
bigbear-device-record record --platform android --no-enable-vision

# 调整实时投屏帧率（仅当用户明确要求调整时使用）
bigbear-device-record record --platform android --fps 5

# 不自动打开浏览器（适合 SSH/容器环境）
bigbear-device-record record --platform android --no-browser

# 帮助信息
bigbear-device-record record --platform android --help
```

## 录制流程

1. 确认 `adb devices -l` 至少列出一台 `device` 状态的设备
2. 运行 `bigbear-device-record record --platform android [--device-id <serial>]`
3. 浏览器左侧实时/按需展示 Android 设备画面（默认 `实时投屏` 模式）
4. 右侧面板填写 **Module**（必填，如 `电商-购物车`）、**Func**（可选）、**Desc**（可选）
5. 点击 **📸 SNAP** 捕获当前画面 + 设备 UI 层次
6. 可多次 SNAP，每次生成独立 `screenshot_NNN.png` + `android_NNN.json`
7. 关闭浏览器即结束采集会话

## 输出文件

统一命名规则：录制会自动按时间戳生成批次号目录，所有数据落在 `AI-信息采集/<批次号>/<模块路径>/` 下。

- **批次目录**：`{output}/{批次号}/`（批次号由工具自动生成，例如 `20260606-153022`）
- **功能目录**：`{output}/{批次号}/{模块路径}/`
- **图片**：`{output}/{批次号}/{模块路径}/img/screenshot_NNN.png`
- **JSON**：`{output}/{批次号}/{模块路径}/json/android_NNN.json`

完整目录示意（android 项目根下三个统一命名的根目录并列）：

```
android/                              ← android 项目根目录
├── AI-信息采集/                       ← --output 默认值
│   └── 20260606-153022/              ← 自动生成的批次号
│       └── 电商/购物车/               ← 用户填入的模块路径
│           ├── img/screenshot_001.png
│           └── json/
│               ├── android_001.json
│               └── android_002.json
├── AI-测试点分析/                     ← testpoint 写入
└── AI-测试用例/                       ← case-generator 写入
```

## JSON 文件内容

```json
{
  "content": "<dumpsys window 或 uiautomator dump 输出的 UI 层次 XML>",
  "img": "img/screenshot_001.png",
  "module": "电商-购物车",
  "func": "结算",
  "desc": "",
  "interface_desc": "AI 视觉分析-界面整体描述",
  "layout_desc": "AI 视觉分析-布局描述",
  "elements_desc": "AI 视觉分析-元素描述列表"
}
```

> JSON schema 与 `bigbear-web-record` 的 `dom_NN.json` 完全一致，下游 `bigbear-web-case-generator` / `bigbear-device-case-generator` 可直接消费。`content` 字段填入设备当前 UI 层次 XML（来自 `uiautomator dump`）。

## 参数说明

| 参数                  | 说明                                                       | 默认值         |
| --------------------- | ---------------------------------------------------------- | -------------- |
| `--platform`        | 固定为 `android`                                         | **必填** |
| `--device-id`       | 设备序列号（`adb devices -l` 的第一列）                  | 第一台设备     |
| `--output`, `-o`  | 输出根目录（注意！除非用户明确指定，不要配置 output）      | `./AI-信息采集`          |
| `--host`            | 内置 HTTP 服务监听地址                                     | `127.0.0.1`  |
| `--port`            | 内置 HTTP 服务端口                                         | `8765`       |
| `--fps`             | 实时投屏帧率（1-30），默认 `2`，仅当用户明确要求调整时传 | `2`          |
| `--enable-vision`   | 启用多模态 AI 截图分析（默认开启，除非用户明确说不开启）   | **true** |
| `--verbose`, `-v` | DEBUG 日志                                                 | false          |
| `--no-browser`      | 不自动打开浏览器                                           | false          |

## 环境变量

```bash
# 视觉 AI 分析（默认开启，以下三项必填；只有用户明确说不开启时才不需要）
VISION_API_KEY=your_api_key_here
VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen3.6-flash-2026-04-16
```

## 环境要求

- **Python 3.9+**
- **Node.js >= 18**（通过 `npx` 调用 `@midscene/android@1`）
- **Android Platform Tools**（提供 `adb`，可执行 `adb devices -l`）
- **Android 设备 / 模拟器**：
  - USB 连接并开启 **USB 调试**
  - 或模拟器 `emulator-5554` 等
  - 设备需处于 `device` 状态（不是 `unauthorized` / `offline`）
- `playwright install chromium`（midscene 内部依赖）

## 常见问题

| 问题                                   | 排查                                                                           |
| -------------------------------------- | ------------------------------------------------------------------------------ |
| `adb: command not found`             | 安装 Android Platform Tools 并加入 PATH                                        |
| `device unauthorized`                | 设备弹窗点"允许 USB 调试"，重新插拔                                            |
| `device offline`                     | `adb kill-server && adb start-server` 后重连                                 |
| `midscene take_screenshot timed out` | 检查设备屏幕是否熄灭/锁屏，先 `adb shell input keyevent KEYCODE_WAKEUP` 解锁 |
| 多台设备时启动报错                     | 显式传 `--device-id <serial>`                                                |

## 工作原理

- `list_devices`：`adb devices -l` 解析 `serial / state / model`
- `connect`：`npx @midscene/android@1 connect --deviceId <serial>`
- 实时投屏：周期 `npx @midscene/android@1 take_screenshot` → base64 → WebSocket
- SNAP：触发 `take_screenshot` + `uiautomator dump` → 落 PNG + JSON
- 可选：调用多模态大模型做 `interface_desc` / `layout_desc` / `elements_desc` 三段式分析
