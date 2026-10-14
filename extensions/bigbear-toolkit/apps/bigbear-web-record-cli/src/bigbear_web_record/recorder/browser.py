import asyncio
import json
import subprocess
import os
import base64
import shutil
import sys
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page
from typing import Optional, List
from .interceptor import NetworkInterceptor, NetworkRequest, NetworkResponse
from ..debug import debug, info, warn, error, step


def _resolve_windows_command(command: str, args: list):
    """Resolve command for Windows platform compatibility."""
    if sys.platform != "win32":
        return command, list(args)

    path = Path(command)
    if path.is_absolute():
        if path.suffix.lower() in {".exe", ".bat"}:
            return command, list(args)
        return "cmd", ["/c", command, *args]

    resolved = shutil.which(command)
    if not resolved:
        return "cmd", ["/c", command, *args]
    resolved_path = Path(resolved)
    if resolved_path.suffix.lower() in {".exe", ".bat"}:
        return resolved, list(args)
    return "cmd", ["/c", command, *args]

# 多模态AI分析接口
def analyze_screenshot_with_vision(screenshot_path: str, api_key: str, base_url: str, model: str = "qwen3.6-flash-2026-04-16") -> Optional[dict]:
    """使用多模态大模型分析截图，返回界面描述、布局描述、元素描述"""
    try:
        from openai import OpenAI
    except ImportError:
        warn("openai SDK not installed, run: pip install openai")
        return None

    try:
        import base64
        with open(screenshot_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        client = OpenAI(api_key=api_key, base_url=base_url)

        prompt = """请分析这张页面截图，返回一个纯JSON对象，不要包含任何其他文字、代码块标记或解释。

JSON格式：
{
  "interface_desc": "界面整体描述（一段话）",
  "layout_desc": "布局描述",
  "elements_desc": "元素描述列表"
}

只返回JSON，不要有其他内容。"""

        completion = client.chat.completions.create(
            model=model,
            max_tokens=10240,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                {"type": "text", "text": prompt}
            ]}]
        )

        result_text = json.loads(completion.model_dump_json())['choices'][0]['message']['content']
        # 尝试提取JSON部分
        if "```json" in result_text:
            start = result_text.find("```json") + 7
            end = result_text.find("```", start)
            result_text = result_text[start:end].strip()
        elif "```" in result_text:
            start = result_text.find("```") + 3
            end = result_text.find("```", start)
            result_text = result_text[start:end].strip()

        # 清理可能的不完整JSON，尝试找到有效的JSON对象
        result_text = result_text.strip()
        try:
            return json.loads(result_text)
        except json.JSONDecodeError as e:
            # 尝试提取 JSON 对象
            import re
            # 查找第一个 { 到最后一个 } 之间的内容
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    return json.loads(result_text[start_idx:end_idx+1])
                except:
                    pass
            error(f"Failed to parse vision result: {e}")
            return None
    except Exception as e:
        error(f"Vision analysis failed: {type(e).__name__}: {e}")
        return None

class BrowserRecorder:
    def __init__(self, url: str, output_dir: str = ".", vision_api_key: Optional[str] = None, vision_base_url: Optional[str] = None, vision_model: str = "qwen3.6-flash-2026-04-16"):
        self.url = url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.interceptor = NetworkInterceptor()
        self.playwright = None
        self._done_event: Optional[asyncio.Event] = None
        self.output_dir = output_dir
        self._snapshot_count = 0
        self._recording = False
        self._record_count = 0
        self.enhanced_info = ""
        self.vision_api_key = vision_api_key or os.environ.get("WEB_VISION_API_KEY")
        self.vision_base_url = vision_base_url or os.environ.get("WEB_VISION_BASE_URL")
        self.vision_model = vision_model
        self.vision_enabled = bool(self.vision_api_key and self.vision_base_url)
        self.cdp_port = 9222  # 默认值，会在 start() 中被覆盖
        self._batch_dir: Optional[str] = None  # 本次运行的批次目录（<output_dir>/<batch_id>），惰性创建后整次运行复用

    async def _handle_request(self, request):
        if not self._recording:
            return
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            pd = request.post_data
            if pd:
                if isinstance(pd, str):
                    body = pd
                elif isinstance(pd, bytes):
                    body = pd.decode('utf-8', errors='replace')
                else:
                    body = str(pd)
        req = NetworkRequest(
            id=str(id(request)),
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            body=body,
            timestamp=request.timing.get("startTime", 0) if hasattr(request, "timing") else 0
        )
        self.interceptor.on_request(req)

    async def _handle_response(self, response):
        body = None
        try:
            body = await response.text()
        except Exception:
            pass

        resp = NetworkResponse(
            request_id=str(id(response.request)),
            status=response.status,
            headers=dict(response.headers),
            body=body,
            timestamp=response.timing.get("responseStart", 0) if hasattr(response, "timing") else 0
        )
        self.interceptor.on_response(resp)

    async def _on_page_close(self):
        """Handle page close (user manually closed tab/window)"""
        if self._done_event and not self._done_event.is_set():
            self._done_event.set()

    async def _on_context_close(self):
        """Handle context close (user manually closed browser)"""
        if self._done_event and not self._done_event.is_set():
            self._done_event.set()

    def _resolve_module_subpath(self) -> str:
        """从 enhanced_info 中解析模块子路径，例如 "人事管理-企业员工" -> "人事管理/企业员工"。

        无模块信息时返回"默认模块"，避免落到批次根目录。
        """
        if not self.enhanced_info:
            return "默认模块"
        try:
            info_obj = json.loads(self.enhanced_info)
            module = (info_obj.get("module", "") or "").strip()
        except json.JSONDecodeError:
            return "默认模块"
        if not module:
            return "默认模块"
        return module.replace("-", "/").replace("\\", "/")

    def _resolve_session_dir(self, module_subpath: str = "") -> str:
        """返回当前运行的会话输出目录，结构：<output_dir>/<batch_id>/<module_subpath>。

        批次目录在同一 recorder 实例内惰性创建并复用；模块子目录按需创建。
        """
        if self._batch_dir is None:
            from datetime import datetime
            batch_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            self._batch_dir = os.path.join(self.output_dir, batch_id)
            os.makedirs(self._batch_dir, exist_ok=True)

        session_dir = os.path.join(self._batch_dir, module_subpath) if module_subpath else self._batch_dir
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    async def _capture_snapshot(self):
        """Capture DOM snapshot and screenshot via Playwright"""
        self._snapshot_count += 1

        # 新结构：<output_dir>/<batch_id>/<module_subpath>/{img, json}
        module_subpath = self._resolve_module_subpath()
        snapshot_base_dir = self._resolve_session_dir(module_subpath)

        # Create img and json subfolders
        img_dir = os.path.join(snapshot_base_dir, "img")
        json_dir = os.path.join(snapshot_base_dir, "json")
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)

        dom_file = os.path.join(json_dir, f"dom_{self._snapshot_count}.json")
        screenshot_file = os.path.join(img_dir, f"screenshot_{self._snapshot_count}.png")

        # Use Playwright to capture full-page screenshot
        if self.page:
            try:
                await self.page.screenshot(path=screenshot_file, full_page=True)
                if os.path.exists(screenshot_file):
                    debug(f"Screenshot saved: {screenshot_file}")
            except Exception as e:
                error(f"Failed to capture screenshot: {e}")

        # Capture DOM snapshot via playwright-cli
        try:
            step("Capturing DOM snapshot...")
            playwright_cli_cmd = "playwright-cli" # shutil.which("playwright-cli") or r"D:\u01\nvm\nodejs\playwright-cli.cmd"


            env = {**os.environ, 'PYTHONUTF8': '1'}

            # Step 1: attach to CDP
            cmd, args = _resolve_windows_command(playwright_cli_cmd, ["attach", f"--cdp=http://localhost:{self.cdp_port}"])
            debug(f"attach cmd: {cmd}")
            debug(f"attach args: {args}")
            attach_result = subprocess.run(
                [cmd, *args],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace',
                env=env
            )
            debug(f"attach.returncode: {attach_result.returncode}")
            debug(f"attach.stdout: {attach_result.stdout[:200] if attach_result.stdout else 'None'}")
            debug(f"attach.stderr: {attach_result.stderr[:200] if attach_result.stderr else 'None'}")

            # Step 2: snapshot
            cmd, args = _resolve_windows_command(playwright_cli_cmd, ["snapshot"])
            result = subprocess.run(
                [cmd, *args],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace',
                env=env
            )

            debug(f"snapshot.returncode: {result.returncode}")
            debug(f"snapshot.stdout length: {len(result.stdout) if result.stdout else 0}")
            debug(f"snapshot.stderr: {result.stderr[:200] if result.stderr else 'None'}")

            if result.returncode == 0 and result.stdout:
                dom_data = {
                    "content": result.stdout,
                    "img": f"img/screenshot_{self._snapshot_count}.png"
                }
                if self.enhanced_info:
                    try:
                        info_obj = json.loads(self.enhanced_info)
                        dom_data["module"] = (info_obj.get("module", "") or "").strip() or "默认模块"
                        dom_data["func"] = info_obj.get("func", "")
                        dom_data["desc"] = info_obj.get("desc", "")
                    except json.JSONDecodeError:
                        dom_data["module"] = "默认模块"
                        dom_data["desc"] = self.enhanced_info
                with open(dom_file, "w", encoding="utf-8") as f:
                    json.dump(dom_data, f, ensure_ascii=False, indent=2)
                debug(f"DOM snapshot saved: {dom_file}")

                # Vision多模态分析截图
                if self.vision_enabled and os.path.exists(screenshot_file):
                    step("Vision AI analyzing screenshot...")
                    vision_result = analyze_screenshot_with_vision(screenshot_file, self.vision_api_key, self.vision_base_url, self.vision_model)
                    if vision_result:
                        dom_data["interface_desc"] = vision_result.get("interface_desc", "")
                        dom_data["layout_desc"] = vision_result.get("layout_desc", "")
                        dom_data["elements_desc"] = vision_result.get("elements_desc", "")
                        with open(dom_file, "w", encoding="utf-8") as f:
                            json.dump(dom_data, f, ensure_ascii=False, indent=2)
                        step("Vision analysis result saved")
                    else:
                        step("Vision analysis failed, skipping...")
            else:
                warn(f"playwright-cli snapshot returned non-zero exit code: {result.returncode}")
        except subprocess.TimeoutExpired:
            error("playwright-cli command timed out after 30 seconds")
        except FileNotFoundError as e:
            error(f"playwright-cli command not found: {e}")
        except Exception as e:
            error(f"Failed to capture DOM: {type(e).__name__}: {e}")

    async def _on_recording_done(self):
        """Called when user clicks the mark button - capture DOM and screenshot synchronously"""
        await self._capture_snapshot()
        self.enhanced_info = ""  # Clear after snapshot is captured
        # Notify page that capture is done
        if self.page:
            await self.page.evaluate("window.__pcr_capture_done && window.__pcr_capture_done()")

    def start_recording(self):
        """Start recording network traffic. Called from JS."""
        self._recording = True
        self._record_count += 1

    def _get_record_output_dir(self) -> str:
        """返回当前录制（rawNN.json）的输出目录。

        新结构：<output_dir>/<batch_id>/<module_subpath>
        同一 recorder 实例内 batch_id 复用；module_subpath 取自 enhanced_info。
        """
        module_subpath = self._resolve_module_subpath()
        return self._resolve_session_dir(module_subpath)

    def stop_recording_and_save(self) -> tuple:
        """Stop recording and save flows to raw_NN.json. Returns (count, record_index)."""
        if not self._recording:
            return (0, 0)
        self._recording = False
        if self._record_count <= 0:
            return (0, 0)
        record_index = self._record_count
        filename = f"raw{record_index:02d}.json"
        output_dir = self._get_record_output_dir()
        output_path = os.path.join(output_dir, filename)
        count = self.interceptor.save_flows_to_file(output_path)
        self.interceptor.clear()
        return (count, record_index)

    def save_current_recording(self) -> tuple:
        """Save whatever is in the current recording buffer. Called on browser close."""
        if self._recording and self._record_count > 0:
            record_index = self._record_count
            filename = f"raw{record_index:02d}.json"
            output_dir = self._get_record_output_dir()
            output_path = os.path.join(output_dir, filename)
            count = self.interceptor.save_flows_to_file(output_path)
            self.interceptor.clear()
            return (count, record_index)
        return (0, 0)

    def get_recording_state(self) -> dict:
        """Get current recording state for UI sync. Called from JS on page load."""
        state = {
            "is_recording": self._recording,
            "record_count": self._record_count
        }
        debug(f"get_recording_state returning: {state}")
        return state

    def set_enhanced_info(self, info: str):
        """Set enhanced info for the current snapshot. Called from JS."""
        self.enhanced_info = info
        debug(f"Enhanced info set: {info}")

    def clear_enhanced_info(self):
        """Clear enhanced info. Called from JS before capturing snapshot."""
        self.enhanced_info = ""
        debug("Enhanced info cleared")

    async def start(self, cdp_port: int = 9222):
        self.playwright = await async_playwright().start()
        debug(f"Launching browser with cdp_port={cdp_port}")
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                f"--remote-debugging-port={cdp_port}",
            ]
        )
        self.cdp_port = cdp_port
        context = await self.browser.new_context()
        self.page = await context.new_page()

        # Create event for recording completion
        self._done_event = asyncio.Event()

        # Register interceptors
        self.page.on("request", self._handle_request)
        self.page.on("response", self._handle_response)

        # Register close handlers (user manually closed browser/tab)
        self.page.on("close", self._on_page_close)
        context.on("close", self._on_context_close)

        # Add init script to inject floating ball on EVERY page navigation
        # This runs BEFORE page content loads, so we use load event to inject
        init_script = '''
(function() {
    // Only create ball in top-level window, not in iframes
    if (window !== window.top) return;

    window.__pcr_click_done = window.__pcr_click_done || null;
    window.__pcr_start_recording = window.__pcr_start_recording || null;
    window.__pcr_stop_recording = window.__pcr_stop_recording || null;

    function createBall() {
        var container = document.createElement('div');
        container.id = 'pcr-floating-ball';
        container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:999999;display:flex;gap:5px;';

        // Module input
        var moduleInput = document.createElement('input');
        moduleInput.id = 'pcr-module-input';
        moduleInput.type = 'text';
        moduleInput.placeholder = '模块如:1-2-3';
        moduleInput.style.cssText = 'height:36px;padding:0 12px;background:#fff;border:2px solid #2196F3;border-radius:18px;cursor:text;display:flex;align-items:center;justify-content:center;font-family:Arial,sans-serif;font-size:12px;color:#333;user-select:text;white-space:nowrap;width:100px;';

        // Function point input
        var funcInput = document.createElement('input');
        funcInput.id = 'pcr-func-input';
        funcInput.type = 'text';
        funcInput.placeholder = '功能点...';
        funcInput.style.cssText = 'height:36px;padding:0 12px;background:#fff;border:2px solid #FF9800;border-radius:18px;cursor:text;display:flex;align-items:center;justify-content:center;font-family:Arial,sans-serif;font-size:12px;color:#333;user-select:text;white-space:nowrap;width:100px;';

        // Description input
        var descInput = document.createElement('input');
        descInput.id = 'pcr-desc-input';
        descInput.type = 'text';
        descInput.placeholder = '描述...';
        descInput.style.cssText = 'height:36px;padding:0 12px;background:#fff;border:2px solid #4CAF50;border-radius:18px;cursor:text;display:flex;align-items:center;justify-content:center;font-family:Arial,sans-serif;font-size:12px;color:#333;user-select:text;white-space:nowrap;width:120px;';

        // SNAP button
        var snapBtn = document.createElement('div');
        snapBtn.id = 'pcr-snap-btn';
        snapBtn.textContent = 'SNAP';
        snapBtn.style.cssText = 'height:36px;padding:0 16px;background:#4CAF50;border-radius:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 10px rgba(0,0,0,0.3);font-family:Arial,sans-serif;font-size:12px;color:white;user-select:none;font-weight:bold;white-space:nowrap;';

        var isDragging = false;
        var hasMoved = false;
        var startX, startY, initX, initY;

        container.addEventListener('mousedown', function(e) {
            if (e.target === container) return;
            isDragging = true;
            hasMoved = false;
            startX = e.clientX;
            startY = e.clientY;
            var rect = container.getBoundingClientRect();
            initX = rect.left;
            initY = rect.top;
            container.style.cursor = 'move';
        });

        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            var dx = e.clientX - startX;
            var dy = e.clientY - startY;
            if (Math.abs(dx) > 5 || Math.abs(dy) > 5) hasMoved = true;
            var x = initX + dx;
            var y = initY + dy;
            x = Math.max(0, Math.min(x, window.innerWidth - container.offsetWidth));
            y = Math.max(0, Math.min(y, window.innerHeight - container.offsetHeight));
            container.style.left = x + 'px';
            container.style.top = y + 'px';
            container.style.right = 'auto';
        });

        document.addEventListener('mouseup', function() {
            isDragging = false;
            container.style.cursor = 'default';
        });

        // SNAP button click - combine module, function point, and description
        snapBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (hasMoved) return;
            var moduleText = moduleInput.value || "";
            var funcText = funcInput.value || "";
            var descText = descInput.value || "";

            // Combine all three fields as JSON
            var combinedInfo = JSON.stringify({
                module: moduleText,
                func: funcText,
                desc: descText
            });

            if (window.__pcr_set_enhanced_info) {
                window.__pcr_set_enhanced_info(combinedInfo);
            }
            container.style.display = 'none';

            if (window.__pcr_click_done) {
                window.__pcr_click_done();
            }
        });

        window.__pcr_capture_done = function() {
            container.style.display = 'flex';
        };

        container.appendChild(moduleInput);
        container.appendChild(funcInput);
        container.appendChild(descInput);
        container.appendChild(snapBtn);
        return container;
    }

    async function ensureBall() {
        var existingBall = document.getElementById('pcr-floating-ball');
        if (existingBall) {
            // Ball already exists from previous navigation - sync state if possible
            console.log('[PCR] Ball exists, attempting state sync...');
            if (window.__pcr_get_state && window.__pcr_sync_state) {
                try {
                    // exposed functions return promises, must await
                    var state = await window.__pcr_get_state();
                    console.log('[PCR] Got state from Python:', JSON.stringify(state));
                    await window.__pcr_sync_state(state);
                    console.log('[PCR] State synced successfully');
                } catch(e) {
                    console.log('[PCR] State sync failed:', e.message);
                }
            } else {
                console.log('[PCR] Exposed functions not ready yet');
            }
            return;
        }
        if (!document.body) return;
        console.log('[PCR] Creating new ball');
        document.body.appendChild(createBall());
    }

    // Wait for page load complete before injecting
    window.addEventListener('load', function() {
        console.log('[PCR] Page load event fired');
        ensureBall();

        // Sync recording state from Python on page load (for SPA navigation)
        // Retry a few times since exposed functions may not be ready immediately
        async function trySyncState() {
            console.log('[PCR] trySyncState called');
            if (window.__pcr_get_state && window.__pcr_sync_state) {
                try {
                    // exposed functions return promises, must await
                    var state = await window.__pcr_get_state();
                    console.log('[PCR] Got state from Python:', JSON.stringify(state));
                    await window.__pcr_sync_state(state);
                } catch(e) {
                    console.log('[PCR] State sync error:', e.message);
                }
            } else {
                console.log('[PCR] Functions not available:', {
                    get_state: !!window.__pcr_get_state,
                    sync_state: !!window.__pcr_sync_state
                });
            }
        }
        trySyncState();
        setTimeout(trySyncState, 100);
        setTimeout(trySyncState, 300);
        setTimeout(trySyncState, 500);

        // MutationObserver to keep ball alive on DOM changes
        var observer = new MutationObserver(function(mutations) {
            ensureBall();
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });

        // Listen for history changes (SPA navigation)
        var originalPushState = window.history.pushState;
        window.history.pushState = function() {
            originalPushState.apply(this, arguments);
            setTimeout(function() { ensureBall(); }, 300);
            setTimeout(function() { trySyncState(); }, 500);
        };
        var originalReplaceState = window.history.replaceState;
        window.history.replaceState = function() {
            originalReplaceState.apply(this, arguments);
            setTimeout(function() { ensureBall(); }, 300);
            setTimeout(function() { trySyncState(); }, 500);
        };
        window.addEventListener('popstate', function() {
            setTimeout(function() { ensureBall(); }, 300);
            setTimeout(function() { trySyncState(); }, 500);
        });
    });
})();
'''
        await context.add_init_script(init_script)

        # Expose functions for floating ball to call - this must be AFTER add_init_script
        # because init_script references window.__pcr_click_done, __pcr_start_recording, __pcr_stop_recording
        await self.page.expose_function("__pcr_click_done", self._on_recording_done)
        await self.page.expose_function("__pcr_start_recording", self.start_recording)
        await self.page.expose_function("__pcr_stop_recording", self.stop_recording_and_save)
        await self.page.expose_function("__pcr_save_current", self.save_current_recording)
        await self.page.expose_function("__pcr_set_enhanced_info", self.set_enhanced_info)
        await self.page.expose_function("__pcr_clear_enhanced_info", self.clear_enhanced_info)
        await self.page.expose_function("__pcr_get_state", self.get_recording_state)

        # Navigate to target URL
        await self.page.goto(self.url)
        await self.page.wait_for_load_state("networkidle")

        # Wait for done event
        await self._done_event.wait()

        # Shutdown
        await self.shutdown()

    async def shutdown(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

def start_recording(url: str):
    recorder = BrowserRecorder(url)
    asyncio.run(recorder.start())
