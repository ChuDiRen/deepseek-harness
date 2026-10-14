# BigBear Web CLI

基于 Playwright CDP 和 AI 视觉大模型的浏览器控制 CLI 工具。

## 功能

- 🌐 **打开网址** - 打开指定 URL
- 👆 **AI点击** - 通过 AI 视觉识别元素并点击
- ⌨️ **AI输入** - 通过 AI 视觉定位元素并输入文本
- 📜 **滚动** - 上下左右滚动页面

## 安装

### 方式一：安装为全局命令 (推荐)

```bash
cd bigbear_web_cli
pip install -e .

# 安装 Playwright 浏览器 (只需执行一次)
playwright install chromium
```

安装后即可全局使用 `bigbear-web-cli` 命令：

```bash
bigbear-web-cli --port 9222 navigate https://www.example.com
bigbear-web-cli click "登录按钮"
bigbear-web-cli input "搜索框" "关键词"
bigbear-web-cli scroll down
```

### 方式二：直接运行

```bash
cd bigbear_web_cli
pip install -r requirements.txt

python main.py --port 9222 navigate https://www.example.com
```

## 配置

复制 `.env.example` 为 `.env` 并配置您的 AI API：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
AI_API_KEY=your_api_key_here
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL=qwen3.6-flash-2026-04-16
```

## 使用方法

### 常用命令

**打开网址**
```bash
bigbear-web-cli --port 9222 navigate https://www.example.com -s screenshot.png
```

**AI点击元素**
```bash
bigbear-web-cli --port 9222 click "登录按钮"
bigbear-web-cli --port 9222 click "搜索框" --enhanced "页面顶部的搜索输入框"
```

**AI输入文本**
```bash
bigbear-web-cli --port 9222 input "搜索框" "关键词"
```

**滚动页面**
```bash
bigbear-web-cli --port 9222 scroll down
bigbear-web-cli --port 9222 scroll up -c 5
bigbear-web-cli --port 9222 scroll right --region "右侧列表" -c 3
```

**截图**
```bash
bigbear-web-cli --port 9222 screenshot output.png
```

### 无头模式

添加 `--headless` 参数可在无头模式下运行：

```bash
bigbear-web-cli --headless --port 9222 navigate https://www.example.com
```

## 项目结构

```
bigbear-web-cli_web_cli/
├── __init__.py       # 包初始化
├── main.py           # CLI 入口
├── browser.py        # Playwright CDP 浏览器管理
├── ai_control.py     # AI 视觉控制
├── actions.py        # 基础操作 (点击/输入/滚动)
├── pyproject.toml    # 打包配置
├── requirements.txt  # 依赖列表
├── .env.example      # 配置示例
└── README.md         # 本文件
```

## 工作原理

1. **浏览器连接**：通过 Playwright CDP 连接到 Chrome 浏览器
2. **截图获取**：使用 Playwright 获取浏览器当前页面的截图
3. **AI 识别**：将截图发送给 AI 视觉模型，模型返回元素坐标
4. **操作执行**：使用 Playwright Mouse/Keyboard API 在指定坐标执行点击/输入操作

## Playwright 优势

- ✅ 不需要下载 chromedriver
- ✅ 自带浏览器管理 (playwright install chromium)
- ✅ 原生 CDP 支持，直连浏览器
- ✅ API 简洁，支持截图、点击、键盘输入等

## 参考

参考 `frameworkCode/v_23_0/bigbear-web-cli_framework/keywords/web_keywords.py` 实现
