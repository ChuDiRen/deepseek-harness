"""mitmweb Web UI 控制面板包装层。

启动一个轻量 HTTP 服务器（默认端口 9090），代理请求到 mitmweb (8089)，
在 HTML 响应中注入一个浮动"🛑 停止录制"按钮。

设计目的：mitmweb 是 Electron 应用，关闭浏览器 tab 不等于关闭主进程，
所以不能依赖"关 tab = 停止录制"。改为在 mitmweb 页面里直接注入按钮，
按钮 POST 到本包装层的 /__recorder_stop__ 端点，触发 CLI 优雅退出。
"""
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional
from urllib import error as urlerr
from urllib import request as urlreq

# 按钮注入 JS（外链 script 内容，不含 <script> 标签）
# 必须在 <head> 里通过 <script src="..."> 引用，否则 mitmweb 的 React 应用会清空内联 script
RECORDER_INJECT_JS = r"""
(function() {
    if (window.__recorderStopInjected) return;
    window.__recorderStopInjected = true;

    function ensureButton() {
        if (document.getElementById('__recorder_stop_btn__')) return;
        var btn = document.createElement('button');
        btn.id = '__recorder_stop_btn__';
        btn.innerText = '🛑 停止录制';
        btn.style.cssText = [
            'position:fixed', 'bottom:20px', 'right:20px',
            'z-index:2147483647',
            'padding:12px 20px',
            'background:#e53935', 'color:#fff',
            'border:none', 'border-radius:6px',
            'font-size:14px', 'font-weight:600',
            'box-shadow:0 4px 12px rgba(0,0,0,.3)',
            'cursor:pointer', 'font-family:system-ui,sans-serif'
        ].join(';');
        btn.onmouseover = function() { btn.style.background = '#c62828'; };
        btn.onmouseout  = function() { btn.style.background = '#e53935'; };
        btn.onclick = function() {
            btn.disabled = true;
            btn.innerText = '⏳ 正在停止...';
            fetch('/__recorder_stop__', { method: 'POST' })
                .then(function(r) {
                    if (r.ok) {
                        btn.innerText = '✅ 已停止，可以关闭页面';
                    } else {
                        btn.innerText = '❌ 停止失败';
                        btn.disabled = false;
                    }
                })
                .catch(function() {
                    btn.innerText = '❌ 网络错误';
                    btn.disabled = false;
                });
        };
        document.body.appendChild(btn);
    }

    function boot() {
        if (document.body) {
            ensureButton();
        } else {
            document.addEventListener('DOMContentLoaded', ensureButton);
        }
        // SPA 路由切换后重新注入
        var observer = new MutationObserver(function() { ensureButton(); });
        observer.observe(document.documentElement, { childList: true, subtree: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
"""


class _ProxyHandler(BaseHTTPRequestHandler):
    """处理两类请求：
    - POST /__recorder_stop__  → 触发 on_stop 回调
    - 其他                    → 代理到 mitmweb_port，在 HTML 响应中注入 JS
    """

    # 由 ControlPanel 在 start() 时填充。注意：必须在 do_POST 里用 _ProxyHandler.on_stop()
    # 调用类属性，否则 self.on_stop 会被 Python 当成 bound method 自动传 self。
    on_stop: Callable[[], None] = lambda: None
    mitmweb_port: int = 8089

    def log_message(self, format, *args):
        # 静默默认 access log（debug 模式可重写）
        pass

    # ---------- POST /__recorder_stop__ ----------

    def _clean_path(self) -> str:
        """去掉 query string，返回纯路径部分。"""
        return self.path.split("?", 1)[0]

    def do_POST(self):
        if self._clean_path() == "/__recorder_stop__":
            try:
                # 用类属性调用，避免 self.on_stop 被当成 bound method 传 self
                _ProxyHandler.on_stop()
            except Exception:
                pass
            self._send_json(200, {"status": "stopping"})
        else:
            self._proxy_request()

    # ---------- GET / 其他 ----------

    def do_GET(self):
        path = self._clean_path()
        # /__recorder_inject.js → 返回外链 JS（由 <script src=...> 加载）
        if path == "/__recorder_inject.js":
            body = RECORDER_INJECT_JS.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
            return
        # /__recorder_status__ → 返回当前录制状态（可选）
        if path == "/__recorder_status__":
            self._send_json(200, {"status": "recording"})
            return
        self._proxy_request()

    # ---------- 工具方法 ----------

    def _send_json(self, code: int, payload: dict):
        import json
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _proxy_request(self):
        """转发请求到 mitmweb，HTML 响应注入按钮 JS。"""
        target = f"http://127.0.0.1:{self.mitmweb_port}{self.path}"
        # 转发 query string
        if self.path.startswith("/"):
            # 重建完整 URL（含 query string）
            full = self.path
        else:
            full = "/" + self.path

        try:
            req = urlreq.Request(f"http://127.0.0.1:{self.mitmweb_port}{full}")
            # 透传少量安全 headers
            for h in ("User-Agent", "Accept", "Accept-Language"):
                v = self.headers.get(h)
                if v:
                    req.add_header(h, v)

            with urlreq.urlopen(req, timeout=10) as resp:
                body = resp.read()
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")

                self.send_response(status)
                # 透传 headers（排除 hop-by-hop）
                for h, v in resp.headers.items():
                    hl = h.lower()
                    if hl in ("transfer-encoding", "connection", "content-length"):
                        continue
                    self.send_header(h, v)

                # HTML 响应注入 JS
                if "text/html" in content_type and body:
                    body = self._inject(body)

                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urlerr.HTTPError as e:
            try:
                body = e.read()
                self.send_response(e.code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_error(502, f"mitmweb error: {e}")
        except Exception as e:
            self.send_error(502, f"proxy error: {e}")

    def _inject(self, body: bytes) -> bytes:
        """在 HTML 响应的 <head> 里注入 <script src="/__recorder_inject.js">。

        注意：必须是外链 script，不能用内联 <script>。
        mitmweb 是 React SPA，启动后用 React 渲染会清空 body 的内联 script 标签。
        外链 script 在 head 里加载，浏览器会主动 fetch + 执行，与 mitmweb 的 app.js 同等待遇。
        """
        try:
            html = body.decode("utf-8", errors="replace")
        except Exception:
            return body

        # 在 </head> 前插入外链 script 标签（自闭合）
        inject_tag = '<script src="/__recorder_inject.js"></script>'
        if "</head>" in html:
            html = html.replace("</head>", inject_tag + "</head>", 1)
        elif "<body" in html:
            # 兜底：在 <body> 后立即插入
            html = re.sub(r"(<body[^>]*>)", r"\1" + inject_tag, html, count=1)
        else:
            html = inject_tag + html

        return html.encode("utf-8")


class ControlPanel:
    """包装层 HTTP 服务器。"""

    def __init__(self, mitmweb_port: int, on_stop: Callable[[], None]):
        self.mitmweb_port = mitmweb_port
        self.on_stop = on_stop
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, port: int = 9090) -> bool:
        """启动包装层。返回是否成功。"""
        # 把回调注入 handler 类（避免每个实例继承）
        _ProxyHandler.mitmweb_port = self.mitmweb_port
        _ProxyHandler.on_stop = self.on_stop

        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", port), _ProxyHandler)
        except OSError as e:
            return False

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="recorder-control-panel",
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass

    @property
    def port(self) -> int:
        return self._server.server_address[1] if self._server else 0