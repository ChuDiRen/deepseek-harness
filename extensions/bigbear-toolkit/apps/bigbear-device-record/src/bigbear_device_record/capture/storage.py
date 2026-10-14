"""Storage: 输出目录管理。
结构: <output_dir>/<batch_id>/<module_path>/{img, json}
- batch_id 在 Storage 实例内惰性创建并复用（同一次 recorder 运行）
- module_path 由 "1-2-3" / "人事管理-企业员工" 这类字符串转换
- 多 platform 通过文件名 "{platform}_{idx}.json" 在同一 module 目录下区分
JSON schema 与 web-record dom_NN.json 完全对齐：仅 content/img/module/func/desc +
可选 vision 字段。设备专属字段（platform/device_id/...）不写入 JSON。"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


class Storage:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self._batch_dir: Optional[Path] = None  # <output_dir>/<batch_id>，整次运行复用
        # 模块子目录缓存：{module: Path}，首次写入时创建
        self._module_dirs: dict = {}

    def _module_parts(self, module: str) -> list:
        # "人事管理-企业员工" → ["人事管理", "企业员工"]，过滤空段与路径穿越
        return [p for p in re.split(r"[-/\\]", module) if p and p not in (".", "..")]

    def _get_batch_dir(self) -> Path:
        """整次 recorder 运行的批次目录：<output_dir>/<batch_id>，惰性创建后复用。"""
        if self._batch_dir is None:
            batch_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            self._batch_dir = self.output_dir / batch_id
            self._batch_dir.mkdir(parents=True, exist_ok=True)
        return self._batch_dir

    def get_module_dir(self, platform: str, module: str) -> Path:
        """返回 <output_dir>/<batch_id>/<module_path>，按需创建 img/json 子目录。

        platform 仅用于向后兼容的接口形态（实际不影响目录布局，
        多 platform 在同一 module 目录下用文件名区分）。
        """
        if module in self._module_dirs:
            return self._module_dirs[module]
        session_dir = self._get_batch_dir().joinpath(*self._module_parts(module))
        (session_dir / "img").mkdir(parents=True, exist_ok=True)
        (session_dir / "json").mkdir(parents=True, exist_ok=True)
        self._module_dirs[module] = session_dir
        return session_dir

    def _next_index(self, json_dir: Path, prefix: str) -> int:
        existing = list(json_dir.glob(f"{prefix}_*.json"))
        if not existing:
            return 1
        nums = []
        for p in existing:
            m = re.match(rf"{re.escape(prefix)}_(\d+)\.json$", p.name)
            if m:
                nums.append(int(m.group(1)))
        return max(nums) + 1 if nums else 1

    def save_snapshot(
        self,
        *,
        png_bytes: bytes,
        platform: str,
        module: str,
        func: str,
        desc: str,
        device_dump: str,
        device_id: str,
        device_name: str,
        dimensions: Tuple[int, int],
    ) -> Path:
        """保存截图 + JSON，返回 json 文件路径。
        JSON schema 与 web-record dom_NN.json 完全一致；
        设备专属字段不入 JSON。"""
        session_dir = self.get_module_dir(platform, module)
        json_dir = session_dir / "json"
        img_dir = session_dir / "img"
        n = self._next_index(json_dir, platform)
        idx_str = f"{n:03d}"

        img_path = img_dir / f"screenshot_{idx_str}.png"
        img_path.write_bytes(png_bytes)

        json_path = json_dir / f"{platform}_{idx_str}.json"
        data = {
            "content": device_dump,
            "img": f"img/screenshot_{idx_str}.png",
            "module": module,
            "func": func,
            "desc": desc,
        }
        # 原子写：临时文件 + rename
        tmp = json_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, json_path)
        return json_path

    def update_with_vision(self, json_path: Path, vision_result: dict) -> None:
        """读 JSON、合并 vision 字段、原子写回。"""
        data = json.loads(json_path.read_text(encoding="utf-8"))
        for key in ("interface_desc", "layout_desc", "elements_desc"):
            if key in vision_result:
                data[key] = vision_result[key]
        tmp = json_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, json_path)
