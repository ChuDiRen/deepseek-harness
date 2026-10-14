# BigBear Android CLI 安装与升级

> **提示**：仅在需要安装或升级时查看此文档。正常运行不需要查阅此文件。

## 前置依赖：adb

本工具依赖 **adb**（Android Debug Bridge）。`bigbear-android-cli` 不附带 adb，需要单独安装：

### 安装 adb

**方式一：Android SDK Platform Tools（推荐）**
- 下载：https://developer.android.com/studio/releases/platform-tools
- 解压后将 `platform-tools/` 加入系统 PATH

**方式二：通过包管理器**
```bash
# macOS
brew install android-platform-tools

# Ubuntu/Debian
sudo apt install adb

# Windows (Chocolatey)
choco install adb

# Windows (Scoop)
scoop install adb
```

**验证安装：**
```bash
adb --version  # 应输出版本号
adb devices     # 应能看到已连接的设备
```

### 设备连接

1. 在 Android 设备上启用**开发者选项 → USB 调试**
2. USB 连接电脑，首次连接时在手机上点击"允许 USB 调试"
3. 运行 `adb devices` 确认设备出现在列表中

> **多设备场景**：多台设备同时连接时，建议通过 `-s <serial>` 指定目标设备，或设置 `ANDROID_DEFAULT_DEVICE` 环境变量。

## pip 镜像源配置（可选，提升下载速度）

推荐配置 pip 镜像源，创建或编辑 `~/.pip/pip.conf`（Linux/Mac）或 `%USERPROFILE%\pip\pip.ini`（Windows）：

```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
trusted-host = pypi.tuna.tsinghua.edu.cn
```

**说明**：`bigbear-android-cli` 发布在私有源，依赖包（如 loguru、openai、Pillow）需从主源获取。建议同时配置主源和私有源（见下方命令）。

## bigbear-android-cli 安装与升级

**首次安装：**
```bash
pip install bigbear-android-cli -i https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url http://public:publicpublic@pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
```

**升级到最新版本：**
```bash
pip install --upgrade bigbear-android-cli -i https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
```

**安装指定版本：**
```bash
pip install bigbear-android-cli==1.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
```

> **说明**：`-i` 指定主源（清华/腾讯/阿里云等），`--extra-index-url` 添加私有源。pip 会优先从主源查找依赖，私有源找不到的包会回退到主源。

**检查当前版本：**
```bash
bigbear-android-cli --version
```

> **重要提示**：CLI 程序升级后，必须执行 `pip install --upgrade` 才能使新版本生效。仅升级 pyproject.toml 中的版本号不会自动更新已安装的程序。

## 本地源码安装（开发模式）

如果从本地源码安装：

```bash
cd bigbear-android-cli
pip install -e .
```

或安装开发依赖（含 pytest）：

```bash
pip install -e ".[dev]"
pytest tests/      # 运行 77 个单元测试
```

## 配置

复制 `.env.example` 为 `.env` 并填入 AI API 密钥：

```bash
cp .env.example .env
```

```env
ANDROID_AI_API_KEY=your_api_key_here
ANDROID_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ANDROID_AI_MODEL=qwen-vl-max
```

支持的视觉模型：
- **qwen-vl-max**（推荐）：阿里云 DashScope，稳定性好
- **astron-code-latest**：讯飞 MaaS（OpenAI 兼容模式），偶发 Engine Busy 错误
- 任意 OpenAI 兼容的视觉模型均可

`.env` 加载规则：CLI 继承系统环境变量，并且只读取执行命令时当前工作目录下的 `.env`。系统环境变量优先于 `.env` 中的同名变量；不会搜索用户目录、安装目录、父目录或其他工作区目录。

## 依赖项

- `loguru` - 日志
- `openai` - AI API 调用（兼容模式）
- `Pillow` - 图像处理
- `python-dotenv` - 环境变量管理
- `pyperclip` - 剪贴板支持（中文输入备选）

外部依赖：
- `adb`（Android SDK Platform Tools）- 必需

## Windows 中文输出

在 Windows 上运行前建议设置环境变量以正确显示中文：

```bash
set PYTHONIOENCODING=utf-8
bigbear-android-cli devices
```

或创建一个批处理文件 `bigbear-android.bat`：

```bat
@echo off
set PYTHONIOENCODING=utf-8
bigbear-android-cli %*
```

## 验证安装

完整验证清单：

```bash
# 1. adb 可用
adb devices

# 2. CLI 可用
bigbear-android-cli --version

# 3. 设备连接成功
bigbear-android-cli devices

# 4. 屏幕信息获取
bigbear-android-cli start

# 5. 截图测试
bigbear-android-cli screenshot test.png

# 6. AI 点击测试（需 AI API KEY 已配置）
bigbear-android-cli click "屏幕中央的某个按钮"

# 7. AI 获取内容测试
bigbear-android-cli get "屏幕中央区域的内容"
```

## 常见问题

### Q: `adb not found` 错误？
A: adb 未安装或不在 PATH。安装 Android SDK Platform Tools 后将 `platform-tools` 加入 PATH，或设置 `ANDROID_ADB_PATH` 环境变量指向 adb 完整路径。

### Q: `Engine Busy` 错误？
A: 讯飞 MaaS 服务端问题。AI 自动重试 3 次后退出。建议改用 `qwen-vl-max`（阿里云 DashScope）。

### Q: 中文输入乱码？
A: 工具对非 ASCII 字符强制走"剪贴板+PASTE"路径（不用拼音 IME）。若设备 Android < 10 或 App 禁用剪贴板读取，会立即报错退出（exit code 1），**不**兜底为 `input text`（避免乱码误判为成功）。解决方案：
1. 升级设备 Android ≥ 10（API 29+）
2. 或安装 ADBKeyboard，改用其广播接口输入
3. 或检查目标 App 是否禁用剪贴板读取（金融类常见）

### Q: 多设备时操作错乱？
A: 必须用 `-s <serial>` 指定目标设备。运行 `bigbear-android-cli devices` 查看可用设备序列号。

### Q: 双指缩放无效？
A: 这是"近似"实现——通过并行两个 `adb shell input swipe` 模拟。少数机型/系统可能识别为两次单指。地图类 App 通常支持良好。