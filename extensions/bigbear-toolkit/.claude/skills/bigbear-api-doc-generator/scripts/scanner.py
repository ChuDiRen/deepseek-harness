# -*- coding: utf-8 -*-
"""Parse a single raw JSON file and summarize each interface entry.

输入：一个 raw JSON 文件（dict 或 list of dicts）
输出：每个接口条目解析后的摘要 dict 列表
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, parse_qsl, unquote


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"__error__": f"{type(exc).__name__}: {exc}"}


def decode_form_body(body: Optional[str]) -> Dict[str, str]:
    if not body:
        return {}
    out: Dict[str, str] = {}
    for pair in body.split("&"):
        if not pair:
            continue
        if "=" in pair:
            k, v = pair.split("=", 1)
        else:
            k, v = pair, ""
        out[unquote(k.replace("+", " "))] = unquote(v.replace("+", " "))
    return out


def split_url(url: str) -> Dict[str, Any]:
    if not url:
        return {"path": "", "query": {}, "full": ""}
    parts = urlsplit(url)
    query: Dict[str, str] = {}
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        query[k] = v
    return {"path": parts.path or "", "query": query, "full": url}


def method_path_key(item: Dict[str, Any]) -> str:
    """METHOD /path 形式的 key（不含 query），用于按 method+path 去重。"""
    method = str(item.get("method") or "").upper()
    path = str(item.get("path") or "")
    return f"{method} {path}"


def summarize_item(entry: Dict[str, Any], seq: int = 0) -> Dict[str, Any]:
    """从一条原始接口条目（{request, response}）解析出标准化摘要。"""
    request = entry.get("request") or {}
    response = entry.get("response") or {}
    url_info = split_url(request.get("url") or "")
    method = str(request.get("method") or "").upper()

    body = request.get("body")
    body_format = "none"
    body_params: Dict[str, str] = {}
    body_raw: Optional[str] = None
    if body is not None:
        if isinstance(body, dict):
            body_format = "JSON"
            body_params = {str(k): str(v) for k, v in body.items()}
            body_raw = json.dumps(body, ensure_ascii=False)
        else:
            text = str(body)
            body_raw = text
            stripped = text.lstrip()
            if stripped.startswith(("{", "[")):
                body_format = "JSON"
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        body_params = {str(k): str(v) for k, v in parsed.items()}
                except Exception:
                    pass
            elif "=" in text:
                body_format = "Form"
                body_params = decode_form_body(text)
            else:
                body_format = "Raw"

    status = response.get("status")
    resp_body = response.get("body")
    resp_content_type = ""
    if isinstance(response.get("headers"), dict):
        resp_content_type = str(response["headers"].get("content-type") or "")

    resp_body_raw: Optional[str] = None
    if resp_body is not None:
        resp_body_raw = resp_body if isinstance(resp_body, str) else json.dumps(resp_body, ensure_ascii=False)

    return {
        "seq": seq,
        "method": method,
        "path": url_info["path"],
        "query": url_info["query"],
        "full_url": url_info["full"],
        "headers": request.get("headers") or {},
        "body_format": body_format,
        "body_params": body_params,
        "body_raw": body_raw,
        "response_status": status,
        "response_headers": response.get("headers") or {},
        "response_content_type": resp_content_type,
        "response_body_raw": resp_body_raw,
        "has_response_body": resp_body_raw is not None and resp_body_raw != "",
        "has_error": "__error__" in entry,
        "error": entry.get("__error__", ""),
    }


def dedupe_by_method_path(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 method+path 去重（不含 query），优先保留 response.body 非空的那条。"""
    best: Dict[str, Dict[str, Any]] = {}
    for item in items:
        key = method_path_key(item)
        if not key.strip():
            continue
        if key in best:
            current = best[key]
            if (not current.get("has_response_body")) and item.get("has_response_body"):
                best[key] = item
            elif current.get("has_response_body") == item.get("has_response_body"):
                if item.get("seq", 0) < current.get("seq", 0):
                    best[key] = item
        else:
            best[key] = item
    return [best[k] for k in sorted(best.keys())]


def load_raw_file(path: Path) -> List[Dict[str, Any]]:
    """读取单个 raw JSON 文件，返回接口条目列表（每个元素 {request, response}）。"""
    data = read_json(path)
    if isinstance(data, dict) and "__error__" in data:
        return [data]
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    if isinstance(data, dict):
        return [data]
    return []
