# -*- coding: utf-8 -*-
"""api_doc_generator — 将单个 raw JSON 文件转为标准化的 MD 接口文档。

输入：单个 raw JSON 文件路径（如 AI-信息采集/20260609-223046/raw01.json）
输出：AI-接口管理/{与输入同级的子目录}/{seq:03d}_{METHOD}_{path_safe}.md

处理逻辑：解析 raw JSON（dict 或 list）→ 按 method+path 去重 → 每个接口一个 MD
重跑行为：直接覆盖
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# 复用 scanner 的解析能力
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scanner  # noqa: E402


# ---------- 文件名 ----------

def sanitize_filename(name: str) -> str:
    """把任意字符串清洗成可作文件名的形式（保留中英文数字下划线，剔除路径分隔符与控制符）。"""
    if not name:
        return "api"
    bad = '<>:"/\\|?*\0'
    out = "".join("_" if c in bad else c for c in name).strip()
    return out or "api"


def make_default_filename(
    seq: int,
    item: Dict[str, Any],
    used_names: set,
    method_path_already_used: Optional[Set[tuple]] = None,
) -> str:
    """生成默认 MD 文件名：{seq:03d}_{METHOD}_{path_safe}.md，冲突时降级到 __N。

    冲突检测两层：
    1. 文件名冲突（used_names）—— 已生成/已存在的 MD 文件名
    2. (method, path) 冲突（method_path_already_used）—— 同接口的多份样本会自动加 __N 后缀
       （用于续编号场景：多 raw 文件含相同接口，避免互相覆盖）

    第 2 层逻辑：扫描 used_names 中所有匹配 NNN_METHOD_path_safe__N.md 的最大 N，
    从 max+1 开始递增（而不是每次都从 __2 开始）—— 这样多次续编号不会重复 __2。
    """
    method = (item.get("method") or "UNK").upper()
    # path 保留前导斜杠（与 scan_existing_method_path 保持一致）
    raw_path = item.get("path") or ""
    path = raw_path.strip() or "/api"
    path_safe = sanitize_filename(path.lstrip("/").replace("/", "_")) or "api"
    base = f"{seq:03d}_{method}_{path_safe}"
    candidate = f"{base}.md"

    # 第 1 层：纯文件名冲突
    if candidate not in used_names:
        used_name = candidate
    else:
        n = 2
        while f"{base}__{n}.md" in used_names:
            n += 1
        used_name = f"{base}__{n}.md"

    # 第 2 层：(method, path) 已存在 → 强制加 __N 后缀
    if method_path_already_used is not None:
        key = (method, path)
        if key in method_path_already_used:
            # 扫描 used_names 中所有 NNN_METHOD_path_safe__N.md，取最大 N
            suffix_re = re.compile(rf"^\d{{3,}}_{re.escape(method)}_{re.escape(path_safe)}__(\d+)\.md$")
            max_n = 1  # 默认下一个是 __2
            for name in used_names:
                m = suffix_re.match(name)
                if m:
                    n_val = int(m.group(1))
                    if n_val > max_n:
                        max_n = n_val
            n = max_n + 1
            candidate2 = f"{base}__{n}.md"
            while candidate2 in used_names:
                n += 1
                candidate2 = f"{base}__{n}.md"
            used_name = candidate2

    return used_name


def default_name(item: Dict[str, Any]) -> str:
    """默认 MD 标题名：{METHOD} {path}。"""
    method = (item.get("method") or "UNK").upper()
    path = (item.get("path") or "/api").strip()
    return f"{method} {path}" if path else method


def default_desc(method: str, path: str) -> str:
    """接口描述：未提供时统一兜底为 '待补充：{METHOD} {path}'。"""
    if not path:
        return "待补充"
    return f"待补充：{method} {path}"


# ---------- 输出目录推导 ----------

def derive_output_dir(raw_path: Path) -> Path:
    """镜像 AI-信息采集/X/raw.json → AI-接口管理/X/

    - 若 raw_path 在 AI-信息采集/ 下，输出到 AI-接口管理/ 的对应路径
    - 否则输出到 raw_path.parent 下的 AI-接口管理/{raw_filename} 子目录
    """
    parts = raw_path.parts
    if "AI-信息采集" in parts:
        idx = parts.index("AI-信息采集")
        new_parts = list(parts[:idx]) + ["AI-接口管理"] + list(parts[idx + 1:-1])
        return Path(*new_parts) if new_parts else Path("AI-接口管理")
    # 兜底：与 raw 同级
    return raw_path.parent


# ---------- 工具函数 ----------

def gen_api_id() -> str:
    """生成 32 位无横杠 UUID。"""
    return uuid.uuid4().hex


def infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


# ---------- Content-Type / Accept 解析 ----------

def parse_content_type(content_type: str) -> Dict[str, str]:
    if not content_type:
        return {"mime": "", "charset": "", "boundary": "", "raw": ""}
    raw = str(content_type).strip()
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    mime = parts[0].lower() if parts else ""
    charset = ""
    boundary = ""
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            k = k.strip().lower()
            v = v.strip().strip('"').strip("'")
            if k == "charset":
                charset = v
            elif k == "boundary":
                boundary = v
    return {"mime": mime, "charset": charset, "boundary": boundary, "raw": raw}


def mime_to_format_label(mime: str) -> Dict[str, str]:
    if not mime:
        return {"label": "未知", "desc": "未捕获到 Content-Type，无法判断响应体格式"}
    m = mime.lower()
    if m == "application/json" or m.endswith("+json"):
        return {"label": "JSON", "desc": "JSON 格式数据"}
    if m in ("application/xml", "text/xml") or m.endswith("+xml"):
        return {"label": "XML", "desc": "XML 格式数据"}
    if m == "text/html" or m.endswith("+html"):
        return {"label": "HTML", "desc": "HTML 页面"}
    if m == "text/plain":
        return {"label": "Text", "desc": "纯文本数据"}
    if m.startswith("text/"):
        return {"label": "Text", "desc": f"文本数据（{m}）"}
    if m in ("application/javascript", "text/javascript"):
        return {"label": "JavaScript", "desc": "JavaScript 脚本"}
    if m.startswith("image/"):
        return {"label": "Binary", "desc": f"图片二进制（{m}）"}
    if m.startswith("audio/") or m.startswith("video/"):
        return {"label": "Binary", "desc": f"音视频二进制（{m}）"}
    if m == "application/octet-stream":
        return {"label": "Binary", "desc": "二进制流"}
    if m == "application/pdf":
        return {"label": "Binary", "desc": "PDF 二进制"}
    if m == "application/x-www-form-urlencoded":
        return {"label": "Form", "desc": "表单数据（application/x-www-form-urlencoded）"}
    if m.startswith("multipart/"):
        return {"label": "Multipart", "desc": f"多部分表单数据（{m}）"}
    return {"label": m, "desc": f"{m} 类型数据"}


def accept_to_label(accept: str) -> Dict[str, str]:
    if not accept:
        return {"label": "无", "desc": "未设置 Accept 头（无法判断客户端期望的数据类型）", "primary": "", "raw": ""}
    raw = str(accept).strip()
    candidates: List[Dict[str, Any]] = []
    for seg in raw.split(","):
        seg = seg.strip()
        if not seg:
            continue
        mime = seg.split(";", 1)[0].strip()
        q = 1.0
        if ";" in seg:
            for p in seg.split(";")[1:]:
                p = p.strip()
                if p.startswith("q="):
                    try:
                        q = float(p[2:].strip())
                    except Exception:
                        q = 1.0
        candidates.append({"mime": mime, "q": q})
    if not candidates:
        return {"label": "无", "desc": "Accept 头为空", "primary": "", "raw": raw}
    candidates.sort(key=lambda x: -x["q"])
    primary = candidates[0]["mime"]
    info = mime_to_format_label(primary)
    other = [c["mime"] for c in candidates[1:]][:3]
    if other:
        desc = f"客户端期望 {info['label']} 格式（{primary}，q={candidates[0]['q']}），并可接受 {', '.join(other)}"
    else:
        desc = f"客户端期望 {info['label']} 格式（{primary}，q={candidates[0]['q']}）"
    return {"label": info["label"], "desc": desc, "primary": primary, "raw": raw}


def parse_response_params(body_str: Optional[str]) -> List[tuple]:
    if not body_str:
        return []
    try:
        data = json.loads(body_str)
    except Exception:
        return []
    return _walk(data, "")


def _walk(obj: Any, prefix: str) -> List[tuple]:
    result: List[tuple] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            t = infer_type(v)
            result.append((path, t, "待补充"))
            if isinstance(v, (dict, list)) and v:
                result.extend(_walk(v, path))
    elif isinstance(obj, list) and obj:
        result.extend(_walk(obj[0], prefix + "[0]"))
    return result


def has_error_response(item: Dict[str, Any]) -> bool:
    status = item.get("response_status")
    if isinstance(status, int) and status >= 400:
        return True
    body = item.get("response_body_raw")
    if body:
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                code = data.get("code")
                if isinstance(code, int) and code != 0:
                    return True
                error_code = data.get("error_code")
                if isinstance(error_code, int) and error_code != 0:
                    return True
        except Exception:
            pass
    return False


# ---------- Content-Type 过滤 ----------

# 浏览器页面 / 静态资源 / 证书下载等"非业务接口"白名单（响应不是这些 mime 才算 API）
# 默认只保留 application/json 接口，过滤掉 HTML/CSS/JS/图片/证书等
NON_API_MIME_PREFIXES = (
    "text/html", "text/css", "text/javascript",
    "application/javascript", "application/x-javascript",
    "application/ecmascript", "application/x-ecmascript",
    "image/", "audio/", "video/", "font/",
    "application/x-pkcs12", "application/x-pixbuf", "application/x-shockwave-flash",
    "application/pdf", "application/zip", "application/x-tar", "application/x-gzip",
    "application/octet-stream",
)


def extract_mime(content_type: str) -> str:
    """从 Content-Type 中提取主 mime（去掉 charset/boundary 等参数）。"""
    if not content_type:
        return ""
    raw = str(content_type).strip()
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    return parts[0].lower() if parts else ""


def is_non_api_mime(mime: str) -> bool:
    """判断 mime 是否属于"非业务接口"（页面/静态资源）。"""
    if not mime:
        # 响应 Content-Type 缺失时，按"非业务接口"对待（默认保守，过滤掉）
        return True
    m = mime.lower()
    if m in ("text/html", "text/css", "text/javascript",
             "application/javascript", "application/x-javascript",
             "application/ecmascript", "application/x-ecmascript",
             "application/x-pkcs12"):
        return True
    for prefix in NON_API_MIME_PREFIXES:
        if m.startswith(prefix):
            return True
    return False


def filter_by_content_type(
    items: List[Dict[str, Any]],
    include_content_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """按响应 Content-Type 过滤接口。

    - include_content_types=None：使用默认白名单，只保留 application/json / application/xml / text/plain 等接口
    - include_content_types=[]：不过滤（保留全部）
    - include_content_types=["application/json", ...]：只保留响应 Content-Type 主值匹配的接口
    """
    if include_content_types == []:
        # 显式传空列表 → 不过滤
        return items
    if include_content_types is None:
        # 默认白名单：只保留"业务接口"mime（JSON/XML/Text/Form）
        kept = []
        dropped = []
        for it in items:
            mime = extract_mime(it.get("response_content_type") or "")
            if is_non_api_mime(mime):
                dropped.append(it)
            else:
                kept.append(it)
        return kept
    # 自定义白名单
    wanted = {x.lower().strip() for x in include_content_types if x}
    kept = []
    dropped = []
    for it in items:
        mime = extract_mime(it.get("response_content_type") or "")
        if mime in wanted:
            kept.append(it)
        else:
            dropped.append(it)
    return kept


# ---------- 续编号扫描 ----------

_SEQ_PREFIX_RE = re.compile(r"^(\d{3,})_")


def scan_max_seq(out_dir: Path) -> int:
    """扫描 out_dir 中所有以 NNN_ 开头的 MD 文件，返回最大的 N；无则返回 0。"""
    if not out_dir.exists():
        return 0
    max_seq = 0
    for p in out_dir.glob("*.md"):
        m = _SEQ_PREFIX_RE.match(p.name)
        if m:
            try:
                n = int(m.group(1))
                if n > max_seq:
                    max_seq = n
            except ValueError:
                pass
    return max_seq


def scan_existing_names(out_dir: Path) -> Set[str]:
    """扫描 out_dir 中已存在的所有 MD 文件名（含 __N 后缀）。"""
    if not out_dir.exists():
        return set()
    return {p.name for p in out_dir.glob("*.md")}


def scan_existing_method_path(out_dir: Path) -> Set[tuple]:
    """扫描 out_dir 中已存在的 MD 文件，反推 (method, path) 集合。

    用于：续编号场景下，多个 raw 文件可能含相同 (method, path)，避免互相覆盖。
    例如已有 002_POST_user_login.md → 反推 (POST, /user/login)
    """
    if not out_dir.exists():
        return set()
    keys: Set[tuple] = set()
    seq_re = re.compile(r"^(\d{3,})__?\d*_(POST|GET|PUT|DELETE|PATCH|HEAD|OPTIONS)_")
    method_re = re.compile(r"^(POST|GET|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    for p in out_dir.glob("*.md"):
        name = p.stem  # 002_POST_user_login__2
        parts = name.split("_")
        if len(parts) < 2:
            continue
        # 第一段是 seq
        if not parts[0].isdigit():
            continue
        # 第二段是 method
        method = parts[1].upper()
        if not method_re.match(method):
            continue
        # 第三段开始是 path_safe，去掉可能的 __N 后缀
        path_parts = parts[2:]
        # path_safe 中 _ 替代 / ，但 /user/login.html 这种 path 含 . ，保持原样
        path = "/" + "/".join(path_parts)
        keys.add((method, path))
    return keys


# ---------- MD 文档生成 ----------

def render_md(
    item: Dict[str, Any],
    api_id: str,
    name: str,
    desc: Optional[str] = None,
) -> str:
    method = item["method"]
    path = item["path"]
    if not desc:
        desc = default_desc(method, path)
    full_url = item["full_url"]
    url_params = item.get("query", {}) or {}
    headers = item.get("headers", {}) or {}
    body_format = (item.get("body_format") or "none")
    body_params = item.get("body_params", {}) or {}
    resp_status = item.get("response_status")
    resp_content_type = item.get("response_content_type", "")
    resp_body_raw = item.get("response_body_raw")
    has_error = has_error_response(item)

    lines: List[str] = []
    lines.append("---")
    lines.append("convert: apidoc")
    lines.append("---")
    lines.append("")
    lines.append(f"# {name}")
    lines.append("## 一、基本信息")
    lines.append("### 接口ID")
    lines.append(api_id)
    lines.append("### 接口名称")
    lines.append(name)
    lines.append("### 请求方法")
    lines.append(method)
    lines.append("### 请求路径")
    lines.append(path)
    lines.append("### 完整URL示例")
    lines.append(full_url)
    lines.append("### 描述")
    lines.append(desc)
    lines.append("")

    lines.append("## 二、URL参数")
    if url_params:
        lines.append("| 参数名 | 值 | 说明 |")
        lines.append("|--------|-----|------|")
        for k, v in url_params.items():
            lines.append(f"| {k} | {v} | 待补充 |")
    else:
        lines.append("| 参数名 | 值 | 说明 |")
        lines.append("|--------|-----|------|")
        lines.append("| 无 | 无 | 该接口无 URL 参数 |")
    lines.append("")

    lines.append("## 三、请求头参数")
    interesting: Dict[str, str] = {}
    for k, v in headers.items():
        kl = k.lower()
        if kl in ("content-type", "accept", "authorization", "x-requested-with"):
            interesting[k] = v
    if interesting:
        lines.append("| 字段名 | 值 | 说明 |")
        lines.append("|--------|-----|------|")
        for k, v in interesting.items():
            kl = k.lower()
            if kl == "content-type":
                ct = parse_content_type(v)
                ct_info = mime_to_format_label(ct["mime"])
                charset_note = f"，字符集 {ct['charset']}" if ct["charset"] else ""
                explain = f"请求体格式：{ct_info['desc']}{charset_note}"
            elif kl == "accept":
                acc = accept_to_label(v)
                explain = acc["desc"]
            elif kl == "authorization":
                explain = "认证Token"
            elif kl == "x-requested-with":
                explain = "Ajax 标识"
            else:
                explain = ""
            lines.append(f"| {k} | {v} | {explain} |")
    else:
        lines.append("| 字段名 | 值 | 说明 |")
        lines.append("|--------|-----|------|")
        lines.append("| Content-Type | application/x-www-form-urlencoded | 默认表单格式 |")
    lines.append("")

    lines.append("## 四、请求体参数")
    req_content_type_raw = ""
    req_accept_raw = ""
    for hk, hv in (headers or {}).items():
        if hk.lower() == "content-type":
            req_content_type_raw = hv or ""
        elif hk.lower() == "accept":
            req_accept_raw = hv or ""

    if body_format.lower() == "none" or not body_params:
        lines.append("### 4.1 请求体格式")
        lines.append("")
        lines.append("| 类型 | 说明 |")
        lines.append("|------|------|")
        lines.append("| 无 | 该接口无请求体 |")
        if req_accept_raw:
            acc = accept_to_label(req_accept_raw)
            lines.append("")
            lines.append(f"> 客户端 Accept 头：{req_accept_raw} → {acc['desc']}")
        lines.append("")
    else:
        lines.append("### 4.1 请求体格式")
        lines.append("")
        lines.append("| 类型 | 说明 |")
        lines.append("|------|------|")
        req_ct = parse_content_type(req_content_type_raw) if req_content_type_raw else {"mime": "", "charset": "", "raw": ""}
        if req_ct["mime"]:
            ct_info = mime_to_format_label(req_ct["mime"])
            type_label = ct_info["label"]
            type_desc = f"{ct_info['desc']}（来自 Content-Type: {req_ct['raw']}）"
        elif body_format.lower() == "form":
            type_label = "Form"
            type_desc = "application/x-www-form-urlencoded 表单数据（解析器判定，Content-Type 头缺失）"
        elif body_format.lower() == "json":
            type_label = "JSON"
            type_desc = "application/json JSON 格式数据（解析器判定，Content-Type 头缺失）"
        elif body_format.lower() == "raw":
            type_label = "Raw"
            type_desc = "原始文本（解析器判定，Content-Type 头缺失）"
        else:
            type_label = body_format
            type_desc = f"{body_format} 格式数据（解析器判定，Content-Type 头缺失）"
        lines.append(f"| {type_label} | {type_desc} |")
        if req_accept_raw:
            acc = accept_to_label(req_accept_raw)
            lines.append(f"| Accept | {req_accept_raw} | {acc['desc']} |")
        lines.append("")

        lines.append("### 4.2 参数定义")
        lines.append("")
        lines.append("| 参数名 | 必填 | 类型 | 说明 | 生成规则 |")
        lines.append("|--------|------|------|------|----------|")
        for k, v in body_params.items():
            t = infer_type(v)
            lines.append(f"| {k} | 是 | {t} | 待补充 | 实际值 |")
        lines.append("")
        lines.append("### 4.3 请求示例")
        lines.append("")
        if body_format.lower() == "form" or type_label == "Form":
            sample = "&".join(f"{k}={v}" for k, v in body_params.items())
            lines.append("```text")
            lines.append(sample)
            lines.append("```")
        elif type_label == "JSON":
            lines.append("```json")
            lines.append(json.dumps(body_params, ensure_ascii=False, indent=2))
            lines.append("```")
        else:
            sample_raw = item.get("body_raw") or json.dumps(body_params, ensure_ascii=False)
            lines.append("```")
            lines.append(sample_raw)
            lines.append("```")
        lines.append("")

    lines.append("## 五、响应")
    lines.append("### 5.1 正常响应")
    lines.append("#### 5.1.1 正常响应头")
    lines.append("")
    lines.append("| 字段名 | 值 | 说明 |")
    lines.append("|--------|-----|------|")
    if resp_content_type:
        resp_ct = parse_content_type(resp_content_type)
        ct_info = mime_to_format_label(resp_ct["mime"])
        charset_note = f"，字符集 {resp_ct['charset']}" if resp_ct["charset"] else ""
        lines.append(f"| Content-Type | {resp_content_type} | 响应体格式：{ct_info['desc']}{charset_note} |")
    else:
        lines.append("| Content-Type | （未捕获到） | 待补充：录制时未捕获到响应 Content-Type |")
    lines.append("")

    lines.append("#### 5.1.2 正常响应体格式")
    lines.append("")
    lines.append("| 类型 | 说明 |")
    lines.append("|------|------|")
    if resp_content_type:
        resp_ct = parse_content_type(resp_content_type)
        ct_info = mime_to_format_label(resp_ct["mime"])
        lines.append(f"| {ct_info['label']} | {ct_info['desc']}（来自 Content-Type: {resp_ct['raw']}） |")
    elif resp_body_raw:
        body_stripped = (resp_body_raw or "").lstrip()
        if body_stripped.startswith(("{", "[")):
            lines.append("| JSON | JSON 格式数据（按响应体内容判断；Content-Type 头缺失） |")
        elif body_stripped.startswith("<"):
            lines.append("| XML | XML 格式数据（按响应体内容判断；Content-Type 头缺失） |")
        else:
            lines.append("| Text | 文本数据（按响应体内容判断；Content-Type 头缺失） |")
    else:
        lines.append("| 待补充 | 未捕获到响应体与 Content-Type，无法判定 |")
    lines.append("")

    lines.append("#### 5.1.3 正常响应体参数")
    lines.append("")
    resp_params = parse_response_params(resp_body_raw)
    if resp_params:
        lines.append("| 参数路径 | 类型 | 说明 |")
        lines.append("|----------|------|------|")
        for p, t, d in resp_params:
            lines.append(f"| {p} | {t} | {d or '待补充'} |")
    else:
        lines.append("| 参数路径 | 类型 | 说明 |")
        lines.append("|----------|------|------|")
        lines.append("| 无 | 无 | 未捕获到响应体参数 |")
    lines.append("")

    lines.append("#### 5.1.4 正常响应示例")
    lines.append("")
    if resp_body_raw:
        try:
            pretty = json.dumps(json.loads(resp_body_raw), ensure_ascii=False, indent=2)
            lines.append("```json")
            lines.append(pretty)
            lines.append("```")
        except Exception:
            lines.append("```")
            lines.append(resp_body_raw)
            lines.append("```")
    else:
        lines.append("```")
        lines.append("（未捕获到响应体）")
        lines.append("```")
    lines.append("")

    lines.append("### 5.2 异常响应")
    if has_error:
        lines.append("> 本次录制批次中捕获到异常响应数据，已如实记录。")
    else:
        lines.append(
            "> ⚠️ **本次录制批次中未捕获到任何异常响应**，本章为占位结构，请补充异常场景（鉴权失败、参数错误、服务器错误等）后再完善。"
        )
    lines.append("")

    lines.append("#### 5.2.1 异常响应体格式")
    lines.append("")
    if has_error:
        lines.append("| 类型 | 说明 |")
        lines.append("|------|------|")
        if resp_content_type:
            err_ct = parse_content_type(resp_content_type)
            err_ct_info = mime_to_format_label(err_ct["mime"])
            lines.append(f"| {err_ct_info['label']} | 异常响应体格式：{err_ct_info['desc']}（来自 Content-Type: {err_ct['raw']}） |")
        elif resp_body_raw:
            body_stripped = (resp_body_raw or "").lstrip()
            if body_stripped.startswith(("{", "[")):
                lines.append("| JSON | 异常响应体格式：JSON 格式数据（按响应体内容判断；Content-Type 头缺失） |")
            elif body_stripped.startswith("<"):
                lines.append("| XML | 异常响应体格式：XML 格式数据（按响应体内容判断；Content-Type 头缺失） |")
            else:
                lines.append("| Text | 异常响应体格式：文本数据（按响应体内容判断；Content-Type 头缺失） |")
        else:
            lines.append("| 待补充 | 异常响应体格式未捕获到 Content-Type 与 body |")
    else:
        lines.append("| 类型 | 说明 |")
        lines.append("|------|------|")
        lines.append("| 未捕获 | 待补充：录制时未触发异常响应，请人工补充 |")
    lines.append("")

    lines.append("#### 5.2.2 异常响应体参数")
    lines.append("")
    if has_error:
        lines.append("| 参数路径 | 类型 | 说明 |")
        lines.append("|----------|------|------|")
        for p, t, d in resp_params:
            lines.append(f"| {p} | {t} | {d or '待补充'} |")
    else:
        lines.append("| 参数路径 | 类型 | 说明 |")
        lines.append("|----------|------|------|")
        lines.append("| 未捕获 | - | 待补充：从实际异常响应中提取参数定义 |")
    lines.append("")

    lines.append("#### 5.2.3 异常响应示例")
    lines.append("")
    if has_error:
        lines.append("```json")
        try:
            lines.append(json.dumps(json.loads(resp_body_raw), ensure_ascii=False, indent=2))
        except Exception:
            lines.append(resp_body_raw or "// 待补充")
        lines.append("```")
    else:
        lines.append("```json")
        lines.append("// 待补充：请提供真实的异常响应示例")
        lines.append("```")
    lines.append("")

    lines.append("#### 5.2.4 异常响应状态码")
    lines.append("")
    if has_error:
        lines.append("| HTTP状态码 | 触发场景 | 实际响应摘要 |")
        lines.append("| ---------- | -------- | ------------ |")
        scene = "录制批次实际触发" if resp_status and resp_status >= 400 else "业务错误码非 0"
        preview = (resp_body_raw or "")[:60].replace("\n", " ")
        lines.append(f"| {resp_status} | {scene} | {preview}... |")
    else:
        lines.append("| HTTP状态码 | 触发场景 | 实际响应摘要 |")
        lines.append("| ---------- | -------- | ------------ |")
        lines.append("| 待补充 | 待补充 | 待补充 |")
    lines.append("")

    return "\n".join(lines)


# ---------- 主流程 ----------

def run(
    raw_json_path: str,
    output_dir: Optional[str] = None,
    dry_run: bool = False,
    include_content_types: Optional[List[str]] = None,
    include_all: bool = False,
) -> Dict[str, Any]:
    raw_path = Path(raw_json_path).resolve()
    print(f"[INFO] 输入文件: {raw_path}")

    if not raw_path.is_file():
        print(f"[ERROR] 输入文件不存在: {raw_path}", file=sys.stderr)
        return {"error": "input_not_found", "raw_path": str(raw_path)}

    # 1. 读取并解析
    entries = scanner.load_raw_file(raw_path)
    print(f"[INFO] 原始条目: {len(entries)} 条")
    if not entries:
        print(f"[ERROR] 文件 {raw_path} 中没有可解析的接口条目。", file=sys.stderr)
        return {"error": "no_entries", "raw_path": str(raw_path)}

    # 2. 解析为标准化的 items
    items: List[Dict[str, Any]] = []
    for seq, entry in enumerate(entries):
        if "__error__" in entry:
            print(f"[WARN] 条目 #{seq} 解析失败: {entry.get('__error__')}", file=sys.stderr)
            continue
        if not entry.get("request") or not entry.get("response"):
            print(f"[WARN] 条目 #{seq} 缺 request/response，跳过", file=sys.stderr)
            continue
        items.append(scanner.summarize_item(entry, seq))

    # 3. 去重
    items = scanner.dedupe_by_method_path(items)
    print(f"[INFO] 按 method+path 去重后: {len(items)} 个接口")

    # 4. 推导输出目录
    if output_dir:
        out_dir = Path(output_dir).resolve()
    else:
        out_dir = derive_output_dir(raw_path)
    print(f"[INFO] 输出目录: {out_dir}")

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # 5. Content-Type 过滤
    raw_count_before_filter = len(items)
    if include_all:
        filter_mode = "include_all（不过滤）"
        items = filter_by_content_type(items, include_content_types=[])
    elif include_content_types is not None:
        filter_mode = f"自定义白名单 {include_content_types}"
        items = filter_by_content_type(items, include_content_types=include_content_types)
    else:
        filter_mode = "默认（仅保留 application/json / xml / text/plain 等 API 类型，过滤掉 HTML/CSS/JS/图片/证书）"
        items = filter_by_content_type(items, include_content_types=None)
    dropped_count = raw_count_before_filter - len(items)
    print(f"[INFO] Content-Type 过滤: {filter_mode}")
    print(f"[INFO] 过滤后: {len(items)} 个接口（丢弃 {dropped_count} 个非业务接口）")

    # 6. 续编号：扫描输出目录中已有 {seq:03d}_*.md，取最大 seq+1 作为起点
    #    这样多次调用脚本（一个 raw 文件一次）时不会因为都从 001 开始而互相覆盖
    seq_start = scan_max_seq(out_dir) + 1
    existing_names = scan_existing_names(out_dir)
    existing_method_path = scan_existing_method_path(out_dir)
    if seq_start > 1:
        print(f"[INFO] 检测到输出目录已有 {seq_start - 1} 个文件，从 {seq_start:03d} 续编号")
    if existing_method_path:
        print(f"[INFO] 检测到 {len(existing_method_path)} 个已有接口，重复 (method, path) 将自动加 __N 后缀")

    # 7. 生成 MD
    written: List[Dict[str, str]] = []
    skipped: List[Dict[str, str]] = []
    used_names: Set[str] = set(existing_names)  # 续编号场景下，已存在的文件名也占位
    method_path_seen: Set[tuple] = set(existing_method_path)  # 已存在的 (method, path)
    for offset, it in enumerate(items):
        method = it.get("method", "")
        path = it.get("path", "")
        if not method or not path:
            skipped.append({
                "reason": "missing_method_or_path",
                "method": method,
                "path": path,
            })
            continue

        seq = seq_start + offset
        file_name = make_default_filename(seq, it, used_names, method_path_already_used=method_path_seen)
        used_names.add(file_name)
        method_path_seen.add((method, path))
        api_id = gen_api_id()
        name = default_name(it)
        desc = default_desc(method, path)
        md_content = render_md(it, api_id, name, desc=desc)

        if not dry_run:
            (out_dir / file_name).write_text(md_content, encoding="utf-8")

        written.append({
            "file": file_name,
            "method": method,
            "path": path,
            "seq": seq,
            "has_error": has_error_response(it),
            "has_response_body": it.get("has_response_body", False),
        })

    with_error_responses = sum(1 for w in written if w["has_error"])
    no_response_body = sum(1 for w in written if not w["has_response_body"])

    return {
        "raw_path": str(raw_path),
        "out_dir": str(out_dir),
        "entry_count": len(entries),
        "unique_count_before_filter": raw_count_before_filter,
        "dropped_by_content_type": dropped_count,
        "unique_count": len(items),
        "written_count": len(written),
        "skipped_count": len(skipped),
        "with_error_responses": with_error_responses,
        "no_response_body": no_response_body,
        "seq_start": seq_start,
        "seq_end": seq_start + len(items) - 1 if items else seq_start - 1,
        "filter_mode": filter_mode,
        "written": written,
        "skipped": skipped,
        "dry_run": dry_run,
    }


def print_report(report: Dict[str, Any]) -> None:
    if report.get("error"):
        return
    print()
    print("=" * 60)
    print(f"输入文件: {report['raw_path']}")
    print(f"原始条目: {report['entry_count']} 条 → 去重后 {report['unique_count_before_filter']} 个")
    print(f"Content-Type 过滤: {report.get('filter_mode', 'N/A')}")
    print(f"过滤后: {report['unique_count']} 个接口（丢弃 {report['dropped_by_content_type']} 个非业务）")
    print(f"已写入 MD: {report['written_count']} 个（编号 {report.get('seq_start',1):03d} - {report.get('seq_end', report.get('seq_start',1) - 1):03d}）")
    print("=" * 60)

    print(f"\n输出目录: {report['out_dir']}\n")

    print(f"## 接口列表（共 {len(report['written'])} 个）\n")
    for i, w in enumerate(report["written"], 1):
        body_mark = "[有响应体]" if w["has_response_body"] else "[无响应体]"
        err_mark = "[有异常响应]" if w["has_error"] else "[无异常响应]"
        print(f"{i}. {w['file']}  ←  {w['method']} {w['path']}  {body_mark} {err_mark}")

    if report.get("skipped"):
        print(f"\n## 跳过（{len(report['skipped'])} 个）")
        for s in report["skipped"]:
            print(f"  - reason={s['reason']} method={s.get('method','')} path={s.get('path','')}")

    print(f"\n## 验证")
    print(f"- 仅处理指定文件: {report['raw_path']}")
    print(f"- 正常响应体非空接口: {report['written_count'] - report['no_response_body']} 个 / 无响应体: {report['no_response_body']} 个")
    print(f"- 异常响应捕获: {report['with_error_responses']} 个有 / {report['written_count'] - report['with_error_responses']} 个无（无异常的接口 5.2 已写\"未捕获到异常响应\"占位）")
    print(f"- 续编号: 本次写入起始 seq={report.get('seq_start',1):03d}（自动扫描输出目录已有 {report.get('seq_start',1)-1} 个文件）")
    print(f"- 重跑同文件: 直接覆盖（无备份），用户需自行保留历史版本")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="api_doc_generator — 将单个 raw JSON 文件转为 MD 接口文档",
    )
    parser.add_argument("raw_json", help="raw JSON 文件路径，如 AI-信息采集/20260609-223046/raw01.json")
    parser.add_argument(
        "--output-dir",
        help="MD 输出目录（默认镜像：AI-信息采集/X/raw.json → AI-接口管理/X/）",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅生成预览，不写文件")
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="不过滤任何响应 Content-Type（默认会过滤掉 HTML/CSS/JS/图片/证书等非业务接口）",
    )
    parser.add_argument(
        "--include-content-types",
        action="append",
        default=None,
        metavar="MIME",
        help="自定义保留的响应 Content-Type（可多次指定，如 --include-content-types application/json --include-content-types application/xml）。与 --include-all 互斥",
    )
    args = parser.parse_args()

    if args.include_all and args.include_content_types:
        print("[ERROR] --include-all 与 --include-content-types 互斥，只能选一个", file=sys.stderr)
        return 1

    report = run(
        args.raw_json,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        include_content_types=args.include_content_types,
        include_all=args.include_all,
    )
    print_report(report)
    if report.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
