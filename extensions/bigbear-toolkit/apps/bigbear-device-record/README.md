# bigbear-device-record

多平台（Android / iOS / HarmonyOS / PC）设备画面采集工具。运行后自动起 Python 服务 + HTML 页面，左侧实时/按需展示设备画面，右侧操作面板（module/func/desc + SNAP）。截图保存为 web-record 兼容的 JSON 格式，下游 `bigbear-web-case-generator` 等工具可直接消费。

## 安装

```bash
pip install bigbear-device-record
```

或从源码：
```bash
cd bigbear-device-record
pip install -e ".[dev]"
```

可选 vision AI 分析：
```bash
pip install -e ".[vision]"
```

## 使用

### PC 模式（即开即用）

```bash
bigbear-device-record record --platform pc
```

### 安卓模式（需先实现 `device/android.py`）

```bash
adb devices   # 确认设备
bigbear-device-record record --platform android --device-id <serial>
```

### iOS / HarmonyOS 模式

类似，需先实现对应 connector。

### 通用参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--platform` | 必填 | android / ios / harmony / pc |
| `--device-id` | 取第一个 | 指定设备 |
| `--output` | `AI-信息采集` | 输出根目录 |
| `--host` | `127.0.0.1` | 服务地址 |
| `--port` | `8765` | 服务端口 |
| `--fps` | `2` | 实时模式帧率（1-60） |
| `--enable-vision` | 关闭 | 启用多模态 AI 截图分析 |
| `--verbose` | 关闭 | DEBUG 日志 |
| `--no-browser` | 关闭 | 不自动打开浏览器 |

### Vision AI

复制 `.env.example` 为当前工作目录下的 `.env`，填入 `DEVICE_VISION_API_KEY` 和 `DEVICE_VISION_BASE_URL`，加 `--enable-vision` 启动。

CLI 继承系统环境变量，并且只读取执行命令时当前工作目录下的 `.env`。系统环境变量优先于 `.env` 中的同名变量；`--output` 只控制产物目录，不会改变 `.env` 来源。CLI 不会搜索用户目录、安装目录、父目录、输出目录或其他工作区目录。

## 输出

```
<output>/
└── <module>/
    └── AI-{PLATFORM}采集/
        └── <batch_id>/
            ├── img/screenshot_001.png
            └── json/{platform}_001.json
```

JSON 字段（与 bigbear-web-record `dom_NN.json` **完全一致**）：
- `content` — 设备 UI 层次文本（PC 端为 `""`）
- `img` — 相对路径
- `module` / `func` / `desc` — 用户在页面填写
- `interface_desc` / `layout_desc` / `elements_desc` — vision 分析结果（可选）

## 平台实现状态

| 平台 | 状态 | 底层工具 | 额外依赖 |
|------|------|----------|----------|
| `pc` | ✅ | `@midscene/computer@1` | Node.js |
| `android` | ✅ | `@midscene/android@1` | Node.js, adb |
| `ios` | ✅ | `@midscene/ios@1` | Node.js, xcrun (macOS) |
| `harmony` | ✅ | `@midscene/harmony@1` | Node.js, hdc |

## 环境要求

- Python 3.9+
- **Node.js >= 18**(`bigbear-device-record` 通过 `npx` 调用 4 个 `@midscene/<platform>@1` 工具)
- 平台原生工具(按需安装):
  - PC: 无额外依赖
  - Android: `adb`(Android Platform Tools)
  - iOS: `xcrun`(随 Xcode Command Line Tools,仅 macOS)
  - HarmonyOS: `hdc`(随 HarmonyOS DevEco Studio)
- PC 端:mss 自动安装,桌面环境

## 部署

参见 `deploy.md`。
