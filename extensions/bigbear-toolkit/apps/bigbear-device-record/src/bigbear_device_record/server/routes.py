"""REST endpoints:
- GET  /api/devices?platform=pc            → 设备列表
- POST /api/snapshot                        → 触发一次截图（WS 不可用时降级）
- GET  /api/output/tree                     → 列出已采集的 batches
"""
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..device.manager import DeviceManager
from ..device.pc import ComputerConnector


router = APIRouter(prefix="/api")


@router.get("/devices")
async def list_devices(platform: str = "pc"):
    if platform == "pc":
        from ..device.pc import ComputerConnector
        devices = ComputerConnector().list_devices()
    else:
        # 其他平台：构造 manager 走对应 connector（会抛 NotImplementedError，捕获后返回空列表）
        try:
            mgr = DeviceManager(platform=platform)
            devices = mgr.list_devices()
        except NotImplementedError:
            devices = []
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"devices": [d.__dict__ for d in devices]}


class SnapshotRequest(BaseModel):
    module: str = ""
    func: str = ""
    desc: str = ""
    enable_vision: bool = False


@router.post("/snapshot")
async def take_snapshot(req: SnapshotRequest, request: Request):
    recorder = request.app.state.recorder
    if recorder is None:
        raise HTTPException(status_code=503, detail="recorder not initialized")
    result = await recorder.take_snapshot(
        module=req.module, func=req.func, desc=req.desc, enable_vision=req.enable_vision
    )
    return result


@router.get("/output/tree")
async def output_tree(request: Request):
    """列出已采集的批次树。

    目录布局：<output_dir>/<batch_id>/<module_path>/{img, json}
    遍历顶层 batch 目录，统计每个 module 子目录的 img/json 文件数。
    """
    output_dir = Path(request.app.state.output_dir)
    if not output_dir.exists():
        return {"tree": []}
    tree = []
    for batch_dir in sorted([d for d in output_dir.iterdir() if d.is_dir()]):
        for module_dir in sorted([d for d in batch_dir.iterdir() if d.is_dir()]):
            img_dir = module_dir / "img"
            json_dir = module_dir / "json"
            tree.append({
                "path": str(module_dir.relative_to(output_dir)),
                "img_count": len(list(img_dir.glob("*.png"))) if img_dir.is_dir() else 0,
                "json_count": len(list(json_dir.glob("*.json"))) if json_dir.is_dir() else 0,
            })
    return {"tree": tree}
