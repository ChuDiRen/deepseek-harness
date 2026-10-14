"""FastAPI app factory.
create_app(output_dir, static_dir, recorder=None) → FastAPI instance
"""
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..capture.recorder import DeviceRecorder


def _minimal_index_html() -> str:
    """当 static/index.html 不存在时使用的占位页面。"""
    return """<!DOCTYPE html>
<html><head><title>bigbear-device-record</title></head>
<body><h1>bigbear-device-record</h1>
<p>Static files not bundled. Run with proper static_dir or after installing package.</p>
</body></html>"""


def create_app(
    *,
    output_dir: str,
    static_dir: Optional[str] = None,
    recorder: Optional[DeviceRecorder] = None,
) -> FastAPI:
    app = FastAPI(title="bigbear-device-record")
    app.state.output_dir = output_dir
    app.state.recorder = recorder
    app.state.ws_clients: set = set()

    # 静态资源（如果 static_dir 提供）
    if static_dir and Path(static_dir).exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        index_html_path = Path(static_dir) / "index.html"
        if index_html_path.exists():
            @app.get("/", response_class=HTMLResponse)
            async def root():
                return index_html_path.read_text(encoding="utf-8")
        else:
            @app.get("/", response_class=HTMLResponse)
            async def root():
                return _minimal_index_html()
    else:
        @app.get("/", response_class=HTMLResponse)
        async def root():
            return _minimal_index_html()

    # 输出文件预览（如果目录存在）
    output_path = Path(output_dir)
    if output_path.exists():
        app.mount("/output", StaticFiles(directory=str(output_path)), name="output")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    from .routes import router
    app.include_router(router)
    from .ws import router as ws_router
    app.include_router(ws_router)
    return app
