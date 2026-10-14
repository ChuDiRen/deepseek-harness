# bigbear-mitmproxy-record

华测 mitmproxy 网络录制工具 - 通过系统代理录制桌面应用 / APP / 手机 H5 的 HTTP/HTTPS 流量，
输出与 `bigbear-api-record` 完全兼容的 `raw{NN}.json`。

## 适用场景

- **桌面应用**（Electron / Qt / .NET / Java Swing）接口录制
- **手机 H5 / APP** 接口录制（手机 Wi-Fi 设置代理到电脑 IP）
- **非浏览器 HTTP 客户端**（CLI 工具、SDK、爬虫）抓包分析
- Playwright CDP 录制（`bigbear-api-record` / `bigbear-web-record`）无法附着的所有场景

## 不适用

- 纯 Web SPA 抓 XHR → 用 `bigbear-api-record`
- 要 DOM/截图 → 用 `bigbear-web-record`
- PC 桌面画面采集 → 用 `bigbear-pc-record`

## 安装

```bash
# 清华源 + 华测私有源（项目惯例）
pip install bigbear-mitmproxy-record \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ \
    --trusted-host pypi.hctestedu.com

# 开发模式
pip install -e .[dev]
```

## 使用

```bash
# 主流程：启动录制
bigbear-mitmproxy-record record

# 桌面应用/APP：不打开引导浏览器
bigbear-mitmproxy-record record --no-browser

# 自定义端口
bigbear-mitmproxy-record record --port 8888 --web-port 8889

# 仅安装 CA 证书
bigbear-mitmproxy-record install-ca

# 环境检查
bigbear-mitmproxy-record check

# 停止后台录制
bigbear-mitmproxy-record stop

# 帮助
bigbear-mitmproxy-record --help
```

## 工作原理

- mitmproxy 作为**中间人代理**：客户端 ↔ mitmproxy ↔ 真实服务器
- HTTPS 通过 mitmproxy 的 CA 伪造证书实现透明解密
- mitmweb 内置 Web UI（端口 8081）提供实时查看
- 关闭 Web UI 标签页 = 自动停止录制（默认行为）
- 输出与 `bigbear-api-record` 完全兼容，可直接复用 `inspect_recording.py` 检测