import asyncio
import base64
import time
from pathlib import Path

import pytest
from bigbear_device_record.capture.stream import StreamWorker
from tests.conftest import MockDeviceConnector


@pytest.mark.asyncio
async def test_live_mode_emits_base64_frames():
    connector = MockDeviceConnector()
    received: list[dict] = []
    async def on_frame(payload: dict):
        received.append(payload)
    worker = StreamWorker(connector=connector, fps=20, on_frame=on_frame)
    await worker.start()
    await asyncio.sleep(0.3)  # 给几个 tick
    await worker.stop()
    assert len(received) >= 3
    assert "data" in received[0]
    # base64 解码后必须是合法 PNG
    png_bytes = base64.b64decode(received[0]["data"])
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_snapshot_mode_emits_no_frames():
    connector = MockDeviceConnector()
    received: list[dict] = []
    async def on_frame(payload: dict):
        received.append(payload)
    worker = StreamWorker(connector=connector, fps=20, on_frame=on_frame)
    await worker.start()
    await worker.set_mode("snapshot")
    await asyncio.sleep(0.2)
    await worker.stop()
    assert received == []


@pytest.mark.asyncio
async def test_mode_can_toggle_back_to_live():
    connector = MockDeviceConnector()
    received: list[dict] = []
    async def on_frame(payload: dict):
        received.append(payload)
    worker = StreamWorker(connector=connector, fps=20, on_frame=on_frame)
    await worker.start()
    await worker.set_mode("snapshot")
    await asyncio.sleep(0.1)
    n_after_stop = len(received)
    await worker.set_mode("live")
    await asyncio.sleep(0.2)
    await worker.stop()
    assert len(received) > n_after_stop


@pytest.mark.asyncio
async def test_capture_failure_emits_error_payload():
    connector = MockDeviceConnector()
    errors: list[dict] = []
    async def on_frame(payload: dict):
        pass
    async def on_error(payload: dict):
        errors.append(payload)
    worker = StreamWorker(connector=connector, fps=20, on_frame=on_frame, on_error=on_error)
    await worker.start()
    connector.fail_next_capture = True
    await asyncio.sleep(0.15)
    await worker.stop()
    assert any("error" in e.get("type", "") or "message" in e for e in errors)


@pytest.mark.asyncio
async def test_in_flight_drops_frame():
    """connector.capture_screenshot 慢于 1/fps 时,本帧应被丢弃,不排队。"""
    connector = MockDeviceConnector()
    captured_count = 0

    async def on_frame(payload):
        nonlocal captured_count
        captured_count += 1

    # 1.0 秒超时
    worker = StreamWorker(connector=connector, fps=10, on_frame=on_frame)
    # 替换 capture_screenshot 为慢版本
    # capture_screenshot 协议上是同步的（DeviceConnector 基类），
    # stream.py 走 asyncio.to_thread() 把它丢到线程池；所以要 sleep 用 time.sleep
    def slow_capture():
        time.sleep(0.5)
        return b"\x89PNG_fake"
    connector.capture_screenshot = slow_capture

    await worker.start()
    await asyncio.sleep(1.2)  # 跑 1.2 秒
    await worker.stop()

    # fps=10 → 期望 ~12 帧,但 capture 慢 0.5s → 实际最多 2-3 帧
    # _in_flight 应保证最多 2-3 帧捕获
    assert captured_count <= 4, f"too many frames captured: {captured_count}"
    assert captured_count >= 1, "should have captured at least one frame"


@pytest.mark.asyncio
async def test_snap_path_unaffected_by_in_flight(tmp_path: Path):
    """SNAP 走独立 capture,不应受 _in_flight 守卫影响。"""
    connector = MockDeviceConnector()

    from bigbear_device_record.capture.recorder import DeviceRecorder
    from bigbear_device_record.capture.storage import Storage
    storage = Storage(str(tmp_path))
    recorder = DeviceRecorder(
        connector=connector, storage=storage, platform="mock", fps=1,
    )
    # 直接调 take_snapshot,不走 StreamWorker
    result = await recorder.take_snapshot(
        module="m", func="f", desc="d", enable_vision=False,
    )
    assert result["type"] == "snapshot_done"
