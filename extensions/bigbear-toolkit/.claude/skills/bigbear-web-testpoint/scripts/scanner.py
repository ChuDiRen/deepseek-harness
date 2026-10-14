# -*- coding: utf-8 -*-
"""Scan AI-信息采集 capture batches and summarize DOM JSON inputs.

统一目录约定（三个根目录同级，按平台划分独立项目根）::

    <项目根>/
      AI-信息采集/<批次号>/<模块路径>/
        json/dom_X.json
        img/screenshot_X.png
      AI-测试点分析/<模块路径>/<功能名>.md
      AI-测试点分析/全局通用功能/00_全局通用模块.md
      AI-测试用例/<模块路径>/<功能名>_测试用例.md

skill 默认在项目根目录运行(项目根 = 当前工作目录,其下并列 AI-信息采集/、AI-测试点分析/、AI-测试用例/),scanner.py 会先在当前目录找 AI-信息采集/,
找不到再向上一级父目录找,所以调用方不用关心相对路径。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


CAPTURE_ROOT_NAME = "AI-信息采集"
TESTPOINT_ROOT_NAME = "AI-测试点分析"
TESTCASE_ROOT_NAME = "AI-测试用例"
COMMON_FEATURE_DIR_NAME = "全局通用功能"
COMMON_MODULE_FILE_NAME = "00_全局通用模块.md"


def read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": f"{type(exc).__name__}: {exc}"}


def first_line_value(content: str, prefix: str) -> str:
    for line in content.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def safe_name(value: str, fallback: str) -> str:
    value = (value or "").strip()
    if not value:
        return fallback
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", "", value)
    return value[:80] or fallback


def resolve_project_root(start: Path) -> Path:
    """Find the parent that contains AI-信息采集/.

    Prefer `start` itself; if no capture dir there, try `start.parent`. This
    handles the common case where the skill runs from inside AI-测试点分析/.
    """
    start = start.resolve()
    if (start / CAPTURE_ROOT_NAME).is_dir():
        return start
    parent = start.parent
    if (parent / CAPTURE_ROOT_NAME).is_dir():
        return parent
    raise FileNotFoundError(
        f"未找到 {CAPTURE_ROOT_NAME}/ 目录。已检查: {start / CAPTURE_ROOT_NAME}, {parent / CAPTURE_ROOT_NAME}"
    )


def iter_batch_dirs(capture_root: Path) -> Iterable[Path]:
    """Yield direct child directories of AI-信息采集/ — these are batch ids."""
    if not capture_root.is_dir():
        return
    for child in sorted(capture_root.iterdir(), key=lambda p: p.name):
        if child.is_dir():
            yield child


def iter_feature_runs(batch_dir: Path) -> Iterable[Path]:
    """Yield every feature directory under a batch — anywhere that contains a json/ subdir.

    The feature directory is the parent of the json/ directory; its path relative
    to the batch dir is the <模块路径> used for output.
    """
    for json_dir in sorted(batch_dir.rglob("json")):
        if not json_dir.is_dir():
            continue
        feature_dir = json_dir.parent
        if feature_dir == batch_dir:
            # 兼容: 采集数据直接放在批次号根目录, 没有模块层
            yield feature_dir
        else:
            yield feature_dir


def list_batches(start_path: str) -> Dict[str, Any]:
    start = Path(start_path).resolve()
    project_root = resolve_project_root(start)
    capture_root = project_root / CAPTURE_ROOT_NAME
    testpoint_root = project_root / TESTPOINT_ROOT_NAME
    common_output_dir = testpoint_root / COMMON_FEATURE_DIR_NAME

    batches: List[Dict[str, Any]] = []
    for batch_dir in iter_batch_dirs(capture_root):
        feature_summaries: List[Dict[str, Any]] = []
        total_json = 0
        total_img = 0
        for feature_dir in iter_feature_runs(batch_dir):
            feature_rel = feature_dir.relative_to(batch_dir)
            json_dir = feature_dir / "json"
            img_dir = feature_dir / "img"
            json_count = len(list(json_dir.glob("*.json"))) if json_dir.is_dir() else 0
            image_count = len(list(img_dir.glob("*"))) if img_dir.is_dir() else 0
            total_json += json_count
            total_img += image_count
            feature_summaries.append(
                {
                    "feature_rel": feature_rel.as_posix(),
                    "feature_dir": str(feature_dir),
                    "json_count": json_count,
                    "image_count": image_count,
                    "output_dir": str(testpoint_root / feature_rel),
                }
            )
        batches.append(
            {
                "batch": batch_dir.name,
                "batch_dir": str(batch_dir),
                "feature_count": len(feature_summaries),
                "json_count": total_json,
                "image_count": total_img,
                "features": feature_summaries,
                "common_output_dir": str(common_output_dir),
                "common_module_file": str(common_output_dir / COMMON_MODULE_FILE_NAME),
            }
        )

    batches.sort(key=lambda item: item["batch"])
    return {
        "project_root": str(project_root),
        "capture_root": str(capture_root),
        "testpoint_root": str(testpoint_root),
        "common_output_dir": str(common_output_dir),
        "batch_count": len(batches),
        "batches": batches,
    }


def summarize_json(json_path: Path, feature_dir: Path, feature_rel: Path, project_root: Path) -> Dict[str, Any]:
    data = read_json(json_path)
    content = str(data.get("content") or data.get("raw_content") or "")
    img = str(data.get("img") or "")
    img_path = feature_dir / img if img else None

    module = str(data.get("module") or "").strip()
    if not module:
        # 模块路径 = 功能路径除最后一段; 只有一段时整段都视为模块
        parts = feature_rel.parts[:-1] or feature_rel.parts
        module = "/".join(parts)

    func = str(data.get("func") or "").strip()
    if not func:
        func = first_line_value(content, "- Page Title:") or feature_rel.name or json_path.stem

    return {
        "json_file": str(json_path),
        "json_rel": str(json_path.relative_to(project_root)) if project_root in json_path.parents else str(json_path),
        "img": img,
        "img_file": str(img_path) if img_path else "",
        "img_exists": bool(img_path and img_path.exists()),
        "module": module,
        "func": func,
        "safe_module": safe_name(module, "未命名模块"),
        "safe_func": safe_name(func, json_path.stem),
        "desc": str(data.get("desc") or ""),
        "page_url": first_line_value(content, "- Page URL:"),
        "page_title": first_line_value(content, "- Page Title:"),
        "has_error": "__error__" in data,
        "error": data.get("__error__", ""),
    }


def scan_project(start_path: str, batch: str) -> Dict[str, Any]:
    start = Path(start_path).resolve()
    project_root = resolve_project_root(start)
    capture_root = project_root / CAPTURE_ROOT_NAME
    testpoint_root = project_root / TESTPOINT_ROOT_NAME
    common_output_dir = testpoint_root / COMMON_FEATURE_DIR_NAME
    batch_dir = capture_root / batch

    captures: List[Dict[str, Any]] = []
    if batch_dir.is_dir():
        for feature_dir in iter_feature_runs(batch_dir):
            feature_rel = feature_dir.relative_to(batch_dir)
            output_dir = testpoint_root / feature_rel
            json_dir = feature_dir / "json"
            img_dir = feature_dir / "img"
            json_files = sorted(json_dir.glob("*.json")) if json_dir.is_dir() else []
            items = [summarize_json(p, feature_dir, feature_rel, project_root) for p in json_files]
            funcs = sorted({item["func"] for item in items if item["func"]})
            modules = sorted({item["module"] for item in items if item["module"]})

            captures.append(
                {
                    "batch": batch,
                    "feature_name": feature_rel.name,
                    "feature_dir": str(feature_dir),
                    "feature_rel": feature_rel.as_posix(),
                    "capture_dir": str(capture_root),
                    "run_dir": str(feature_dir),
                    "run_name": feature_rel.as_posix(),
                    "json_dir": str(json_dir),
                    "img_dir": str(img_dir),
                    "output_dir": str(output_dir),
                    "common_output_dir": str(common_output_dir),
                    "common_module_file": str(common_output_dir / COMMON_MODULE_FILE_NAME),
                    "existing_output_dirs": [str(output_dir)] if output_dir.is_dir() else [],
                    "json_count": len(json_files),
                    "image_count": len(list(img_dir.glob("*"))) if img_dir.is_dir() else 0,
                    "modules": modules,
                    "funcs": funcs,
                    "json_files": items,
                }
            )

    captures.sort(key=lambda item: item["feature_rel"])
    total_json = sum(item["json_count"] for item in captures)
    total_pages = sum(len(item["funcs"]) for item in captures)

    return {
        "project_root": str(project_root),
        "capture_root": str(capture_root),
        "testpoint_root": str(testpoint_root),
        "common_output_dir": str(common_output_dir),
        "batch": batch,
        "batch_dir": str(batch_dir),
        "batch_exists": batch_dir.is_dir(),
        "capture_count": len(captures),
        "total_json": total_json,
        "total_funcs": total_pages,
        "captures": captures,
    }


def print_batches(result: Dict[str, Any]) -> None:
    print(f"项目根目录: {result['project_root']}")
    print(f"采集根目录: {result['capture_root']}")
    print(f"测试点根目录: {result['testpoint_root']}")
    print(f"发现可用批次: {result['batch_count']}")
    print("请用 --batch <批次号> 指定本次要分析的批次，扫描器不会默认展开所有 DOM。")
    print()
    for index, item in enumerate(result["batches"], 1):
        print(f"{index}. 批次: {item['batch']}")
        print(f"   功能数: {item['feature_count']}, JSON: {item['json_count']}, 截图: {item['image_count']}")
        for feat in item["features"]:
            print(f"   - {feat['feature_rel']} (json={feat['json_count']}, img={feat['image_count']})")
            print(f"     输出: {feat['output_dir']}")


def print_human(result: Dict[str, Any]) -> None:
    print(f"项目根目录: {result['project_root']}")
    print(f"采集根目录: {result['capture_root']}")
    print(f"测试点根目录: {result['testpoint_root']}")
    print(f"指定批次: {result['batch']}")
    print(f"批次目录: {result['batch_dir']} ({'存在' if result['batch_exists'] else '不存在'})")
    print(f"匹配功能数: {result['capture_count']}")
    print(f"DOM JSON 数量: {result['total_json']}")
    print(f"功能数量: {result['total_funcs']}")
    print()

    if not result["captures"]:
        print("未找到指定批次或该批次下无功能。请先运行 --list-batches 查看可用批次号。")
        return

    for index, capture in enumerate(result["captures"], 1):
        print(f"{index}. {capture['feature_rel']}")
        print(f"   JSON: {capture['json_count']}, 截图: {capture['image_count']}")
        print(f"   输出目录: {capture['output_dir']}")
        print(f"   公共模块: {capture['common_module_file']}")
        if capture["modules"]:
            print(f"   模块: {', '.join(capture['modules'])}")
        if capture["funcs"]:
            print(f"   功能: {', '.join(capture['funcs'])}")
        for item in capture["json_files"]:
            status = "OK" if not item["has_error"] and item["img_exists"] else "CHECK"
            print(f"   - [{status}] {item['json_rel']} -> {item['module']} / {item['func']}")
            if item["page_url"]:
                print(f"     URL: {item['page_url']}")
            if item["has_error"]:
                print(f"     ERROR: {item['error']}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan one AI-信息采集 capture batch. Auto-locates AI-信息采集/ in cwd or parent."
    )
    parser.add_argument(
        "start",
        nargs="?",
        default=".",
        help="起点目录,默认当前目录(项目根目录,其下并列 AI-信息采集/)。会自动向上一级兼容查找 AI-信息采集/",
    )
    parser.add_argument("--batch", help="Required batch id, for example 20260602-215450")
    parser.add_argument(
        "--list-batches",
        action="store_true",
        help="List available batches without reading DOM details",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    if args.list_batches or not args.batch:
        result = list_batches(args.start)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_batches(result)
        return

    result = scan_project(args.start, args.batch)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)


if __name__ == "__main__":
    main()
