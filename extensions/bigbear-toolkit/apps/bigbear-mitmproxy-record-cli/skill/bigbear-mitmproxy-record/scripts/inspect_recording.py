#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_recording.py
快速检测 bigbear-api-record 录制结果（raw{NN}.json）。

不读取完整 body，只解析请求/响应结构以快速输出摘要：
  - 接口总数
  - 每个接口的 [方法] URL + 状态码
  - 按文件 / 按方法的分布
  - 文件大小

用法:
  python inspect_recording.py <path> [<path> ...]

参数 path 可以是:
  - 单个 raw{NN}.json 文件
  - 包含 raw*.json 的目录（自动扫描）
  - 包含多个日期-序号子目录的根目录（递归扫描 raw*.json）
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


# raw 录制文件默认输出根目录
DEFAULT_OUTPUT_DIR = "./AI-信息采集"


def iter_raw_files(paths: Iterable[Path]) -> Iterable[Path]:
    """把所有入参（文件/目录）展开成一组 raw*.json 路径。"""
    for p in paths:
        p = p.resolve()
        if p.is_file():
            if p.suffix.lower() == ".json" and p.name.startswith("raw"):
                yield p
            else:
                print(f"  [跳过] 非 raw 文件: {p}", file=sys.stderr)
        elif p.is_dir():
            # 优先：目录下直接的 raw*.json
            direct = sorted(p.glob("raw*.json"))
            if direct:
                yield from direct
            else:
                # 兜底：递归查找（如 日期-序号/子目录 结构）
                yield from sorted(p.rglob("raw*.json"))
        else:
            print(f"  [跳过] 路径不存在: {p}", file=sys.stderr)


def summarize_file(path: Path) -> dict:
    """快速解析一个 raw 文件，返回摘要信息。"""
    size = path.stat().st_size
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "path": path,
            "size": size,
            "count": 0,
            "entries": [],
            "methods": Counter(),
            "statuses": Counter(),
            "error": f"JSON 解析失败: {e}",
        }

    entries = []
    methods: Counter = Counter()
    statuses: Counter = Counter()

    for item in data if isinstance(data, list) else [data]:
        req = item.get("request", {}) or {}
        resp = item.get("response", {}) or {}
        method = (req.get("method") or "?").upper()
        url = req.get("url") or "(no url)"
        status = resp.get("status")
        methods[method] += 1
        statuses[status] += 1
        entries.append((method, url, status))

    return {
        "path": path,
        "size": size,
        "count": len(entries),
        "entries": entries,
        "methods": methods,
        "statuses": statuses,
        "error": None,
    }


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return f"{n:.1f}TB"


def print_summary(summaries: list[dict]) -> None:
    if not summaries:
        print("未找到任何 raw*.json 文件。")
        return

    total_count = sum(s["count"] for s in summaries)
    total_methods: Counter = Counter()
    total_statuses: Counter = Counter()

    for s in summaries:
        total_methods.update(s["methods"])
        total_statuses.update(s["statuses"])

    print("=" * 72)
    print(f" 录制文件数: {len(summaries)}   接口总数: {total_count}")
    print("=" * 72)

    for s in summaries:
        rel = s["path"]
        print(f"\n📄 {rel.name}  ({human_size(s['size'])})  —  {s['count']} 个接口")
        if s["error"]:
            print(f"   ⚠️  {s['error']}")
            continue
        for i, (method, url, status) in enumerate(s["entries"], 1):
            status_str = f"{status}" if status is not None else "—"
            print(f"   {i:>2}. [{method:<6}] [{status_str:>3}] {url}")

    print("\n" + "-" * 72)
    print(" 汇总")
    print("-" * 72)
    print(f"  按方法: {dict(total_methods)}")
    print(f"  按状态: {dict(total_statuses)}")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="快速检测 bigbear-api-record 录制结果（raw{NN}.json）。",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help=(
            "raw{NN}.json 文件 / 包含 raw*.json 的目录。"
            f"不传则默认扫描 {DEFAULT_OUTPUT_DIR}/ 下的最新一次录制目录。"
        ),
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_DIR,
        help=f"默认输出根目录（当 paths 为空时使用），默认 {DEFAULT_OUTPUT_DIR}",
    )
    args = parser.parse_args()

    paths = list(args.paths) if args.paths else [Path(args.output_root)]
    files = list(iter_raw_files(paths))
    summaries = [summarize_file(f) for f in files]
    print_summary(summaries)
    return 0 if summaries and all(not s["error"] for s in summaries) else 1


if __name__ == "__main__":
    sys.exit(main())
