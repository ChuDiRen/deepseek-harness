# bigbear-web-record

HTTP API recording tool via Playwright CDP. Record browser network requests and generate Markdown API documentation.

## 安装

```bash
pip install bigbear-web-record
```

或从源码安装：

```bash
cd bigbear-web-record
pip install -e .
```

## 使用方法

### 录制 API 文档

```bash
bigbear-web-record record <url> [--output <dir>]
```

示例：

```bash
bigbear-web-record record https://api.example.com
```

这将执行以下操作：
1. 打开 Chromium 浏览器
2. 导航到指定 URL
3. 注入一个悬浮的录制按钮
4. 捕获所有网络请求/响应
5. 点击录制按钮停止录制
6. 生成 Markdown 格式的 API 文档

### 输出

该工具在指定输出目录生成 `api-docs.md`，包含：

- API 端点列表（方法、URL）
- 请求头和请求体
- 响应状态码和响应体
- API 之间的依赖关系

## 环境变量加载规则

CLI 继承系统环境变量，并且只读取执行命令时当前工作目录下的 `.env`。系统环境变量优先于 `.env` 中的同名变量；`--output` 只控制产物目录，不会改变 `.env` 来源。CLI 不会搜索用户目录、安装目录、父目录、输出目录或其他工作区目录。

## 环境要求

- Python 3.9+
- 已安装 Playwright 浏览器：`playwright install chromium`
- 已安装 playwright-cli 全局安装命令：`npm install -g @playwright/cli@latest`
