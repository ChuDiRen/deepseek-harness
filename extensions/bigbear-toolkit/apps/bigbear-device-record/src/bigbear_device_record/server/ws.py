"""WebSocket endpoint at /ws.
握手后：
1. 发送 hello 消息（platform/dimensions/fps）
2. 自动启动 StreamWorker（live 模式）
3. 接收 client 命令（snapshot / set_mode / set_fps / ping）
4. 转发 frame / error / state / snapshot_done 给所有 client
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from ..capture.recorder import DeviceRecorder

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    app = websocket.app
    recorder: Optional[DeviceRecorder] = app.state.recorder
    clients: set = app.state.ws_clients
    clients.add(websocket)
    logger.info("WS client connected, total=%d", len(clients))

    try:
        # 1. 发送 hello
        if recorder:
            try:
                w, h = recorder.connector.get_dimensions()
            except Exception:
                w, h = 0, 0
            hello = {
                "type": "hello",
                "platform": recorder.platform,
                "device": {"id": getattr(recorder.connector, "_connected_to", "") or "local-pc",
                           "name": "device"},
                "dimensions": [w, h],
                "fps": recorder._fps,
                "enable_vision": bool(recorder._vision_config),
            }
        else:
            hello = {"type": "hello", "platform": "unknown", "dimensions": [0, 0], "fps": 0}
        await websocket.send_json(hello)

        if recorder:
            # 2. 启动 streaming
            async def forward(payload):
                if websocket.client_state.name != "CONNECTED":
                    return
                try:
                    await websocket.send_json(payload)
                except Exception:
                    pass
            # 替换 on_event 为 send_to_this_ws
            recorder.on_event = forward
            await recorder.start_streaming()
            # 启动时推一个 state
            await websocket.send_json(await recorder.get_state())

        # 3. 收命令循环
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "invalid json"})
                continue
            await _handle_command(websocket, recorder, msg)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("WS error: %s", e)
    finally:
        clients.discard(websocket)
        logger.info("WS client disconnected, remaining=%d", len(clients))


async def _handle_command(ws: WebSocket, recorder: Optional[DeviceRecorder], msg: dict):
    mtype = msg.get("type")
    if mtype == "ping":
        await ws.send_json({"type": "pong"})
    elif mtype == "snapshot":
        if recorder is None:
            await ws.send_json({"type": "error", "message": "recorder not ready"})
            return
        result = await recorder.take_snapshot(
            module=msg.get("module", ""),
            func=msg.get("func", ""),
            desc=msg.get("desc", ""),
            enable_vision=msg.get("enable_vision", False),
        )
        await ws.send_json(result)
        # 推 state 让前端更新计数
        await ws.send_json(await recorder.get_state())
    elif mtype == "set_mode":
        if recorder:
            await recorder.set_mode(msg.get("mode", "live"))
            await ws.send_json(await recorder.get_state())
    elif mtype == "set_fps":
        if recorder:
            await recorder.set_fps(int(msg.get("fps", 2)))
            await ws.send_json(await recorder.get_state())
    else:
        await ws.send_json({"type": "error", "message": f"unknown type: {mtype}"})
