// bigbear-device-record 前端逻辑
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);

  const els = {
    connStatus: $('conn-status'),
    deviceInfo: $('device-info'),
    frame: $('frame'),
    placeholder: $('placeholder'),
    modeLive: $('mode-live'),
    modeSnap: $('mode-snap'),
    fpsMinus: $('fps-minus'),
    fpsPlus: $('fps-plus'),
    fpsVal: $('fps-val'),
    inModule: $('in-module'),
    inFunc: $('in-func'),
    inDesc: $('in-desc'),
    btnSnap: $('btn-snap'),
    count: $('count'),
    chkVision: $('chk-vision'),
    btnRefresh: $('btn-refresh'),
    logs: $('logs'),
  };

  let ws = null;
  let fps = 2;
  let lastFrameAt = 0;
  let reconnectTimer = null;

  function log(msg, cls) {
    const div = document.createElement('div');
    if (cls) div.className = cls;
    div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    els.logs.appendChild(div);
    els.logs.scrollTop = els.logs.scrollHeight;
    // 限制日志条数
    while (els.logs.children.length > 50) els.logs.removeChild(els.logs.firstChild);
  }

  function setStatus(text, cls) {
    els.connStatus.textContent = '●  ' + text;
    els.connStatus.className = 'status ' + (cls || '');
  }

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => {
      setStatus('已连接', 'connected');
      log('WebSocket 已连接', 'ok');
    };
    ws.onclose = () => {
      setStatus('未连接', 'error');
      log('WebSocket 断开，3s 后重试', 'err');
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connect, 3000);
    };
    ws.onerror = (e) => log('WebSocket 错误', 'err');
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      handleMessage(msg);
    };
  }

  function handleMessage(msg) {
    switch (msg.type) {
      case 'hello':
        fps = msg.fps || 2;
        els.fpsVal.textContent = fps;
        els.deviceInfo.textContent = `${msg.platform}  ${(msg.dimensions||[]).join('×')}`;
        if (msg.enable_vision) els.chkVision.checked = true;
        log(`hello: platform=${msg.platform}, fps=${fps}, enable_vision=${msg.enable_vision||false}`, 'ok');
        break;
      case 'frame':
        // 节流：上一帧未渲染完则丢弃
        if (lastFrameAt && Date.now() - lastFrameAt < 50) break;
        lastFrameAt = Date.now();
        els.frame.src = 'data:image/png;base64,' + msg.data;
        els.placeholder.style.display = 'none';
        break;
      case 'state':
        fps = msg.fps || fps;
        els.fpsVal.textContent = fps;
        els.count.textContent = msg.snapshot_count || 0;
        if (msg.mode === 'live') {
          els.modeLive.classList.add('active');
          els.modeSnap.classList.remove('active');
        } else {
          els.modeSnap.classList.add('active');
          els.modeLive.classList.remove('active');
        }
        break;
      case 'snapshot_done':
        els.count.textContent = msg.count;
        els.btnSnap.disabled = false;
        els.btnSnap.textContent = '📸 SNAP';
        log(`snapshot saved: ${msg.filename} (#${msg.count})`, 'ok');
        break;
      case 'vision_result':
        log(`vision: ${msg.interface_desc || ''}`, 'ok');
        break;
      case 'error':
        log('error: ' + msg.message, 'err');
        els.btnSnap.disabled = false;
        els.btnSnap.textContent = '📸 SNAP';
        break;
      case 'pong':
        break;
      default:
        console.log('unknown msg', msg);
    }
  }

  function send(obj) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      log('WebSocket 未连接', 'err');
      return;
    }
    ws.send(JSON.stringify(obj));
  }

  // 事件绑定
  els.modeLive.addEventListener('click', () => send({ type: 'set_mode', mode: 'live' }));
  els.modeSnap.addEventListener('click', () => send({ type: 'set_mode', mode: 'snapshot' }));

  els.fpsMinus.addEventListener('click', () => {
    fps = Math.max(1, fps - 1);
    send({ type: 'set_fps', fps });
  });
  els.fpsPlus.addEventListener('click', () => {
    fps = Math.min(30, fps + 1);
    send({ type: 'set_fps', fps });
  });

  els.btnSnap.addEventListener('click', () => {
    els.btnSnap.disabled = true;
    els.btnSnap.textContent = '⏳ 采集中...';
    send({
      type: 'snapshot',
      module: els.inModule.value || '',
      func: els.inFunc.value || '',
      desc: els.inDesc.value || '',
      enable_vision: els.chkVision.checked,
    });
  });

  els.btnRefresh.addEventListener('click', () => location.reload());

  // 心跳
  setInterval(() => send({ type: 'ping' }), 30000);

  // 启动
  connect();
})();
