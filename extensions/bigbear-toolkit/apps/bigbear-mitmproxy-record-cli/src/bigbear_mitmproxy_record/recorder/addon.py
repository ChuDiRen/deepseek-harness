"""mitmproxy addon：RecorderAddon。

订阅 request / response / error / done 钩子，把每个 HTTPFlow 转 raw dict 交给 saver 落盘。

mitmproxy addon 通过 -s addon_entry.py 加载（见 cli.py 中 _write_addon_entry 的生成逻辑）。
addons = [RecorderAddon(saver, ...)] 是 mitmproxy 的约定入口。
"""
import re
import time
from typing import Callable, List, Optional

from mitmproxy import ctx, http

from .flow_codec import flow_to_raw_dict
from .saver import FlowSaver


# URL 路径后缀白名单（静态资源）— 命中即跳过
_STATIC_PATH_SUFFIXES = (
    ".css", ".js", ".mjs", ".map",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".webm", ".ogg", ".wav", ".flv", ".mov", ".avi",
    ".pdf", ".zip", ".rar", ".7z", ".tar", ".gz",
)

# 请求头里常带的静态资源标记
_STATIC_REQ_HEADER_HINTS = (
    ("accept", "image/"),
    ("accept", "text/css"),
    ("accept", "font/"),
    ("accept", "video/"),
    ("accept", "audio/"),
)

# AJAX / XHR 标记：response 是 JSON / XML / 文本，且 request 头带 XHR 标志
_API_RESP_HINTS = (
    "application/json",
    "application/xml",
    "text/xml",
    "application/x-www-form-urlencoded",
    "text/plain",
    "text/javascript",
)
_API_REQ_HEADER_KEYS = (
    "x-requested-with",
    "xhr",
)


def _split_url(url: str) -> "tuple[str, str, str]":
    """极简 URL 拆分：scheme / host+port / path+query。仅用于 host/path 过滤。"""
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        host = parts.netloc.lower()
        path = (parts.path or "").lower()
        full_path = path + ("?" + parts.query if parts.query else "")
        return parts.scheme.lower(), host, full_path
    except Exception:
        s = url.lower()
        return "", "", s


def _is_static_path(path: str) -> bool:
    return path.endswith(_STATIC_PATH_SUFFIXES)


class RecorderAddon:
    """mitmproxy addon：录制 HTTP/HTTPS 请求到 raw{NN}.json。"""

    def __init__(
        self,
        saver: FlowSaver,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        resource_filter: str = "off",
        on_running: Optional[Callable[[], None]] = None,
        on_done: Optional[Callable[[], None]] = None,
    ):
        self.saver = saver
        self.exclude = exclude_patterns or []
        self.include = include_patterns or []
        self.resource_filter = (resource_filter or "off").lower()
        self.on_running = on_running
        self.on_done = on_done

        self._exclude_re = [re.compile(p) for p in self.exclude]
        self._include_re = [re.compile(p) for p in self.include]

    # ---------- 过滤逻辑 ----------

    def _match_url(self, url: str) -> bool:
        """URL 阶段过滤（只用到 path，无 body/headers 也能判）。

        - include 为空：默认全收
        - include 非空：必须命中至少一条
        - exclude 任一命中：丢弃
        """
        if self._include_re and not any(r.search(url) for r in self._include_re):
            return False
        if any(r.search(url) for r in self._exclude_re):
            return False
        if self.resource_filter in ("static", "api-only"):
            _, _, path = _split_url(url)
            if _is_static_path(path):
                return False
        return True

    def _match_response(self, flow: "http.HTTPFlow") -> bool:
        """响应阶段过滤：仅在 resource_filter=api-only 时生效。

        - 响应 Content-Type 命中 AJAX 类型（json/xml/form/text）→ 保留
        - 请求头有 X-Requested-With / XHR → 保留
        - 否则（HTML 页面/二进制流）→ 丢弃
        """
        if self.resource_filter != "api-only":
            return True
        resp = flow.response
        if resp is None:
            # 无响应 = 连接异常；保留（错误流也属于业务问题）
            return True
        ctype = (resp.headers.get("Content-Type") or resp.headers.get("content-type") or "").lower()
        if any(h in ctype for h in _API_RESP_HINTS):
            return True
        # request 头里有 XHR 标志也保留
        try:
            for k in _API_REQ_HEADER_KEYS:
                if flow.request.headers.get(k):
                    return True
        except Exception:
            pass
        # HTML 页面 / 其他静态资源：丢弃
        return False

    # ---------- mitmproxy 钩子 ----------

    def running(self):
        """mitmproxy 主循环启动（Web UI 已就绪）。"""
        ctx.log.info("[bigbear-mitmproxy-record] addon running")
        if self.on_running:
            try:
                self.on_running()
            except Exception:
                pass

    def request(self, flow: http.HTTPFlow):
        """请求阶段：只记录起始时间戳和过滤标记。完整数据在 response 阶段落盘。"""
        url = flow.request.pretty_url
        if not self._match_url(url):
            flow._bigbear_skip = True
            return
        flow._bigbear_start_ts = time.time()

    def response(self, flow: http.HTTPFlow):
        """响应阶段：完整 request + response 都齐了，落盘。"""
        if getattr(flow, "_bigbear_skip", False):
            return
        if not self._match_response(flow):
            flow._bigbear_skip = True
            return
        start_ts = getattr(flow, "_bigbear_start_ts", None)
        record = flow_to_raw_dict(flow, start_ts=start_ts)
        self.saver.add(record)

    def error(self, flow: http.HTTPFlow):
        """请求/响应阶段异常（连接超时、TLS 失败等）。"""
        if getattr(flow, "_bigbear_skip", False):
            return
        start_ts = getattr(flow, "_bigbear_start_ts", None)
        record = flow_to_raw_dict(
            flow,
            start_ts=start_ts,
            errored=True,
            error_msg=str(flow.error) if flow.error else "unknown",
        )
        self.saver.add(record)

    def done(self):
        """mitmproxy 主循环退出，最后一次落盘。"""
        ctx.log.info("[bigbear-mitmproxy-record] addon done, flushing...")
        try:
            self.saver.flush_pending()
        except Exception as e:
            ctx.log.error(f"[bigbear-mitmproxy-record] flush_pending 失败: {e!r}")
        if self.on_done:
            try:
                self.on_done()
            except Exception as e:
                ctx.log.error(f"[bigbear-mitmproxy-record] on_done 回调失败: {e!r}")