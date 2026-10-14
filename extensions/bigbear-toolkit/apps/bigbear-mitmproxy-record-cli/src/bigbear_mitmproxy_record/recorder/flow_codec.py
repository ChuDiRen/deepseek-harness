"""mitmproxy HTTPFlow → raw dict 转换器。

输出 schema 与 bigbear-api-record 完全一致（参见
apps/bigbear-web-record-cli/src/bigbear_web_record/recorder/interceptor.py:107-135
的 save_flows_to_file），保证 inspect_recording.py 直接复用。

每条记录结构：
{
    "request": {
        "id": str,
        "method": str,
        "url": str,             # mitmproxy 已解密，HTTPS URL 直接可读
        "headers": dict,
        "body": str | None,
        "timestamp": float,
    },
    "response": {
        "status": int,           # 错误流为 0
        "headers": dict,
        "body": str,
        "timestamp": float,
    },
}
"""
import base64
import time
from typing import Optional

from mitmproxy import http


# 二进制 Content-Type 前缀 → 走 base64
_BINARY_CONTENT_PREFIXES = (
    "image/",
    "video/",
    "audio/",
    "application/octet-stream",
    "application/pdf",
    "font/",
)


def _content_to_str(content: Optional[bytes], headers: dict) -> Optional[str]:
    """bytes body → 字符串。

    文本：直接 utf-8 解码。
    二进制（image/video/audio/octet-stream/pdf/font）：`"base64:" + base64.b64encode(...)`。
    """
    if content is None:
        return None
    if not content:
        return ""

    ctype = (
        headers.get("content-type")
        or headers.get("Content-Type")
        or ""
    ).lower()

    if any(ctype.startswith(p) for p in _BINARY_CONTENT_PREFIXES):
        return "base64:" + base64.b64encode(content).decode("ascii")

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return "base64:" + base64.b64encode(content).decode("ascii")


def _headers_to_dict(headers) -> dict:
    """mitmproxy Headers → 普通 dict（key 统一小写，避免 Content-Type/content-type 不匹配）。

    mitmproxy 的 Headers 对象本身是 case-insensitive，但展开成普通 dict 后就
    变成 case-sensitive 了。如果原 header 是 `Content-Type`，dict 里就是
    `{"Content-Type": ...}`，访问 `.get("content-type")` 会返回 None。
    统一小写化键可以彻底避免这个问题。
    """
    if headers is None:
        return {}
    try:
        return {k.lower(): v for k, v in headers.items()}
    except Exception:
        return dict(headers) if headers else {}


def _get_content_bytes(flow, is_request: bool) -> Optional[bytes]:
    """从 flow 中取 body 字节，自动解压 Content-Encoding（gzip/deflate/br）。

    mitmproxy 的 raw_content 是未解压的字节；content 是解压后的字节。
    我们要的是解压后的字节，否则 UTF-8 解码会失败被误判为二进制。
    """
    if is_request:
        return flow.request.content if flow.request.content else flow.request.raw_content
    else:
        if flow.response is None:
            return None
        return flow.response.content if flow.response.content else flow.response.raw_content


def flow_to_raw_dict(
    flow: "http.HTTPFlow",
    start_ts: Optional[float] = None,
    errored: bool = False,
    error_msg: str = "",
) -> dict:
    """把一个 HTTPFlow 转成与 bigbear-api-record 完全兼容的 raw dict。"""
    req = flow.request
    req_headers = _headers_to_dict(req.headers)
    req_raw = _get_content_bytes(flow, is_request=True)
    req_body = _content_to_str(req_raw, req_headers) if req_raw else None

    request_block = {
        "id": str(id(flow)),
        "method": req.method,
        "url": req.pretty_url,
        "headers": req_headers,
        "body": req_body,
        "timestamp": start_ts if start_ts is not None else time.time(),
    }

    if errored or flow.response is None:
        response_block = {
            "status": 0,
            "headers": {},
            "body": f"error: {error_msg or (str(flow.error) if flow.error else 'unknown')}",
            "timestamp": time.time(),
        }
    else:
        resp = flow.response
        resp_headers = _headers_to_dict(resp.headers)
        resp_raw = _get_content_bytes(flow, is_request=False)
        resp_body = _content_to_str(resp_raw, resp_headers) if resp_raw else ""

        response_block = {
            "status": resp.status_code,
            "headers": resp_headers,
            "body": resp_body,
            "timestamp": time.time(),
        }

    return {"request": request_block, "response": response_block}