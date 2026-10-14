# -*- coding: utf-8 -*-
"""
HTML 报告渲染器：
  输入：<batch_dir>（含 batch_result.json）或直接传 batch_result.json 路径
  输出：<batch_dir>/report.html（单文件，浏览器直接打开）

用法：
  python render_html_report.py <batch_dir>
  python render_html_report.py <path_to_batch_result.json> --output <out_html>
"""

import argparse
import json
import sys
from pathlib import Path

from jinja2 import Template


def _script_safe_json(obj) -> str:
    """把对象序列化成 JSON 字符串，额外把 </ 转成 <\\/ 防止浏览器提前终止 <script> 块"""
    s = json.dumps(obj, ensure_ascii=False)
    return s.replace("</", "<\\/")


def render(batch_dir: Path, output: Path) -> None:
    # 1. 找 batch_result.json
    candidates = [
        batch_dir / "batch_result.json",
        Path(batch_dir) if str(batch_dir).endswith(".json") else None,
    ]
    batch_json_path = next((p for p in candidates if p and p.exists()), None)
    if not batch_json_path:
        print(f"[错误] 找不到 batch_result.json: {batch_dir}", file=sys.stderr)
        sys.exit(1)

    with open(batch_json_path, "r", encoding="utf-8-sig") as f:
        try:
            batch = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[错误] batch_result.json 不是合法 JSON: {e}", file=sys.stderr)
            print(f"       路径: {batch_json_path}", file=sys.stderr)
            print(f"       提示：先跑 bigbear-run-test-plan 或 run_test_plan.py refresh 重新生成", file=sys.stderr)
            sys.exit(1)

    # 2. 找模板
    template_path = Path(__file__).parent / "report_template.html"
    if not template_path.exists():
        print(f"[错误] 找不到模板: {template_path}", file=sys.stderr)
        sys.exit(1)

    tpl_text = template_path.read_text(encoding="utf-8")
    tpl = Template(tpl_text)

    # 3. 渲染
    html = tpl.render(
        batch=batch,
        batch_id=batch.get("batch_id", ""),
        plan_id=batch.get("plan_id", ""),
        plan_name=batch.get("plan_name", ""),
        summary=batch.get("summary", {}),
        flows=batch.get("flows", []),
        started_at=batch.get("started_at"),
        finished_at=batch.get("finished_at"),
        duration_ms=batch.get("duration_ms"),
        batch_json=_script_safe_json(batch),
    )

    # 4. 原子写
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    import os
    os.replace(tmp, output)

    size_kb = output.stat().st_size / 1024
    print(f"[OK] 已生成 {output} ({size_kb:.1f} KB)")
    print(f"     打开方式：双击文件 或 file://{output}")


def main():
    parser = argparse.ArgumentParser(description="HTML 报告渲染器")
    parser.add_argument("batch_dir", help="批次目录（含 batch_result.json）或 batch_result.json 自身路径")
    parser.add_argument("--output", "-o", default=None, help="输出 html 路径，默认 <batch_dir>/report.html")
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)
    if not batch_dir.exists():
        print(f"[错误] 路径不存在: {batch_dir}", file=sys.stderr)
        sys.exit(1)

    if batch_dir.is_file() and not str(batch_dir).endswith(".json"):
        # 传了一个文件但不是 .json
        print(f"[错误] 仅支持目录或 batch_result.json 文件，收到: {batch_dir}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output = Path(args.output)
    else:
        if batch_dir.is_file() and batch_dir.suffix == ".json":
            output = batch_dir.parent / "report.html"
        else:
            output = batch_dir / "report.html"

    render(batch_dir, output)


if __name__ == "__main__":
    main()
