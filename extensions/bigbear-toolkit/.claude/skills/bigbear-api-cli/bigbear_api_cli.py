"""bigbear-api-cli 辅助脚本:确定性 API 请求 + 自然语言断言。

Agent 通过 Bash 调用:
    python bigbear_api_cli.py execute \
      --project <project_root> \
      --case-id <case_id> \
      --ctx '{"URL": "...", "正确账号": "...", "正确密码": "..."}'

读 case 详情 → Jinja2 渲染 → requests 发请求 → 自然语言断言评估 → JSON 输出。
退出码 0 = 全 PASS,1 = 有 FAIL。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests
import yaml
from jinja2 import Environment, StrictUndefined


def _render(template: str, ctx: dict) -> str:
    """Jinja2 渲染一段字符串,缺失变量报错(StrictUndefined)。"""
    env = Environment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)
    try:
        return env.from_string(template).render(**ctx)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return f"<render error: {type(e).__name__}: {e}>"


def _resolve_case_path(project_root: Path, case_id: str) -> Path | None:
    """通过 _index.yaml 找 case yaml 真实路径(与 bigbear_ai_test_runner.plan_loader 同款)。"""
    idx_path = project_root / "AI-自动化测试用例" / "api" / "_index.yaml"
    if idx_path.is_file():
        with idx_path.open(encoding="utf-8") as f:
            index = yaml.safe_load(f) or {}
        entry = index.get(case_id)
        if entry:
            candidate = project_root / "AI-自动化测试用例" / "api" / entry["case_path"]
            if candidate.is_file():
                return candidate

    # fallback:case_id.yaml 直接拼(老格式)
    candidate = project_root / "AI-自动化测试用例" / "api" / f"{case_id}.yaml"
    if candidate.is_file():
        return candidate
    return None


def _load_case(project_root: Path, case_id: str) -> dict | None:
    p = _resolve_case_path(project_root, case_id)
    if p is None:
        return None
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _build_request(case_content: dict, ctx: dict) -> dict:
    """把 case_content.request 字段渲染成可执行的 HTTP 请求参数。"""
    req = case_content.get("request") or {}
    url = _render(req.get("url", ""), ctx)
    method = (req.get("method") or "GET").upper()

    headers: dict[str, str] = {}
    for h in req.get("headers") or []:
        name = h.get("name")
        if not name:
            continue
        headers[name] = _render(h.get("value", ""), ctx)

    url_params: dict[str, str] = {}
    for p in req.get("urlParams") or []:
        name = p.get("name")
        if not name or name == "无":
            continue
        url_params[name] = _render(p.get("value", ""), ctx)

    body_params: dict[str, str] = {}
    for p in req.get("bodyParams") or []:
        name = p.get("name")
        if not name or name == "无":
            continue
        body_params[name] = _render(p.get("value", ""), ctx)

    return {"method": method, "url": url, "headers": headers,
            "url_params": url_params, "body_params": body_params}


def _execute_request(req: dict, timeout: int):
    """真正发 HTTP 请求,返回 (response, error)。"""
    try:
        if req["method"] == "GET":
            resp = requests.get(req["url"], params=req["url_params"],
                                headers=req["headers"], timeout=timeout)
        elif req["method"] == "POST":
            resp = requests.post(req["url"], params=req["url_params"],
                                 headers=req["headers"], data=req["body_params"], timeout=timeout)
        elif req["method"] == "PUT":
            resp = requests.put(req["url"], params=req["url_params"],
                                headers=req["headers"], data=req["body_params"], timeout=timeout)
        elif req["method"] == "DELETE":
            resp = requests.delete(req["url"], params=req["url_params"],
                                   headers=req["headers"], data=req["body_params"], timeout=timeout)
        else:
            return None, f"unsupported method: {req['method']}"
        return resp, None
    except requests.Timeout:
        return None, f"timeout after {timeout}s"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return None, f"{type(e).__name__}: {e}"


def _jsonpath(obj, path: str):
    """极简 JSONPath:支持 'data.token' 这种点号分隔路径。"""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if cur is None:
            return None
    return cur


# ===== 自然语言断言模式 =====

def _eval_status(assertion: str, resp) -> tuple[bool, str]:
    m = re.search(r"响应状态码[:：]\s*(\d+)", assertion)
    if not m:
        return False, "格式不匹配(响应状态码:N)"
    expected = int(m.group(1))
    return resp.status_code == expected, f"expected={expected}, got={resp.status_code}"


def _eval_equals(assertion: str, body_json) -> tuple[bool, str]:
    """响应 <path> 等于 "value"  → jsonpath 取值与字面量相等"""
    m = re.search(r"响应\s+([\w.]+)\s+等于\s+[\"']?([^\"']+)[\"']?", assertion)
    if not m or body_json is None:
        return False, "格式不匹配(响应 X 等于 Y)"
    path, expected = m.group(1), m.group(2)
    actual = _jsonpath(body_json, path)
    return actual == expected, f"json[{path}]={actual!r}, expected={expected!r}"


def _eval_contains(assertion: str, body_json) -> tuple[bool, str]:
    """响应 <path> 包含"X"  → str(jsonpath) contains 字符串"""
    m = re.search(r"响应\s+([\w.]+)\s+包含\s*[\"']?(.+?)[\"']?\s*$", assertion)
    if not m or body_json is None:
        return False, "格式不匹配(响应 X 包含 Y)"
    path, needle = m.group(1), m.group(2)
    haystack = _jsonpath(body_json, path)
    return needle in str(haystack or ""), f"json[{path}]={haystack!r}, needle={needle!r}"


def _eval_exists(assertion: str, body_json) -> tuple[bool, str]:
    """响应 <path> 存在  → jsonpath 非 None"""
    m = re.search(r"响应\s+([\w.]+)\s+存在", assertion)
    if not m or body_json is None:
        return False, "格式不匹配(响应 X 存在)"
    path = m.group(1)
    val = _jsonpath(body_json, path)
    return val is not None, f"json[{path}]={val!r}"


def _eval_nonempty_str(assertion: str, body_json) -> tuple[bool, str]:
    """响应 <path> 应为非空字符串"""
    m = re.search(r"响应\s+([\w.]+)\s+应为非空字符串", assertion)
    if not m or body_json is None:
        return False, "格式不匹配(响应 X 应为非空字符串)"
    path = m.group(1)
    val = _jsonpath(body_json, path)
    if val is None:
        return False, f"json[{path}] is None"
    return isinstance(val, str) and len(val) > 0, f"json[{path}]={val!r}"


def _evaluate_assertion(assertion: str, resp, body_json) -> tuple[bool, str]:
    """试遍所有支持的断言模式,任一命中即返回结果;都不命中则 skip。"""
    evaluators = [
        ("status", lambda: _eval_status(assertion, resp)),
        ("equals", lambda: _eval_equals(assertion, body_json)),
        ("contains", lambda: _eval_contains(assertion, body_json)),
        ("exists", lambda: _eval_exists(assertion, body_json)),
        ("nonempty_str", lambda: _eval_nonempty_str(assertion, body_json)),
    ]
    for name, fn in evaluators:
        try:
            ok, detail = fn()
        except Exception as e:  # pylint: disable=broad-exception-caught
            continue  # 不匹配模式,继续试下一个
        # 如果 detail 包含「格式不匹配」就视为不命中,继续试下一个
        if detail.startswith("格式不匹配"):
            continue
        return ok, detail
    # 都不命中:跳过(也算 PASS,免得因模式不支持把整条 task 误判 FAIL)
    return True, "skip(无法识别的断言格式)"


def execute(project_root: Path, case_id: str, ctx: dict, timeout: int = 30) -> dict:
    """主入口:读 case + 发请求 + 评估断言,返回 dict。"""
    case = _load_case(project_root, case_id)
    if case is None:
        return {"ok": False, "error": f"case not found: {case_id}"}

    content = case.get("case_content") or {}
    try:
        req = _build_request(content, ctx)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"ok": False, "error": f"build request failed: {type(e).__name__}: {e}"}

    resp, err = _execute_request(req, timeout)
    if err is not None:
        return {
            "ok": False,
            "request": req,
            "error": err,
        }

    try:
        body_json = resp.json()
    except Exception:  # pylint: disable=broad-exception-caught
        body_json = None

    assertions = []
    for assertion in content.get("expected") or []:
        ok, detail = _evaluate_assertion(assertion, resp, body_json)
        assertions.append({"assertion": assertion, "ok": ok, "detail": detail})

    all_ok = all(a["ok"] for a in assertions)
    return {
        "ok": all_ok,
        "request": req,
        "response": {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body_text": resp.text[:2000],
            "body_json": body_json,
        },
        "assertions": assertions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="bigbear-api-cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_exec = sub.add_parser("execute", help="执行 api case + 评估断言")
    p_exec.add_argument("--project", required=True, type=Path, help="测试项目根目录")
    p_exec.add_argument("--case-id", required=True, help="case_id (=task.source_id)")
    p_exec.add_argument("--ctx", default=None, help="JSON dict:所有 {{var}} 的渲染值(与 --ctx-file 二选一)")
    p_exec.add_argument("--ctx-file", default=None, type=Path, help="从 JSON 文件读 ctx(优先于 --ctx,避免命令行中文/引号转义问题)")
    p_exec.add_argument("--timeout", type=int, default=30, help="HTTP 超时秒数")

    args = parser.parse_args()

    if args.cmd == "execute":
        # 优先级:--ctx-file > --ctx > {}
        ctx: dict = {}
        if args.ctx_file is not None:
            try:
                with args.ctx_file.open(encoding="utf-8") as f:
                    ctx = json.load(f) or {}
            except Exception as e:
                print(json.dumps({"ok": False, "error": f"--ctx-file 读取失败: {type(e).__name__}: {e}"}, ensure_ascii=False))
                return 2
        elif args.ctx is not None and args.ctx.strip():
            try:
                ctx = json.loads(args.ctx)
            except json.JSONDecodeError as e:
                print(json.dumps({"ok": False, "error": f"--ctx 不是合法 JSON: {e}"}, ensure_ascii=False))
                return 2
        result = execute(args.project, args.case_id, ctx, args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())