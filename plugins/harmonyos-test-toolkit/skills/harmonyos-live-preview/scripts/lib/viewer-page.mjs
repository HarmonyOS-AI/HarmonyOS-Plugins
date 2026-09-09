// Static browser viewer served at `/`. Renders one panel per configured device (discovered from
// GET /devices — one Previewer engine per configured size, see engine.mjs/bridge.mjs), overlays
// build state + ArkTS errors, and — the interactive part — forwards each panel's pointer/keyboard
// input to *that panel's* engine via POST /devices/:id/input (which input.mjs turns into
// MousePress/MouseMove/MouseRelease/KeyPress/BackClicked). Panels lay out in a wrapping flex row so
// multiple sizes sit side by side (narrow windows wrap), mirroring DevEco's multi-device preview.
//
// Frame transport stays poll-based on /devices/:id/frame.jpg (always the latest complete JPEG, no
// MJPEG "needs the next boundary to finalize" stall), but polling is adaptive per panel: ~90ms for a
// short window after any input on that panel so taps/scrolls feel live, ~350ms when idle. Build state
// is shared across all panels (one PreviewBuild serves every device) and polled once via /status,
// which also carries each device's own status (engineConnected/hasFrame/port/engineError) in its
// `devices` array — so there's exactly one status poll per tick, not one per panel. Coordinates are
// sent normalized (0..1) over each panel's own rendered frame; the bridge scales them to that
// device's px, so the mapping is exact as long as the screen box matches the device aspect ratio.
//
// A panel's size is not fixed for the life of the run: dragging its `.grip` corner posts to
// /devices/:id/resize (the engine's own in-place ResolutionSwitch — no rebuild, no reconnect), and
// every panel also follows the geometry reported by /status, so a resize done elsewhere (drive.mjs,
// a second open tab) shows up here too. Everything derived from the geometry — the screen box, the
// $rect basis of the a11y overlay, the displayed px/vp label — is recomputed in setGeometry().
//
// On top of each panel's pixel frame, its own #a11y mirrors that device's inspector tree (GET
// /devices/:id/inspector) as a real DOM tree positioned over the image — one element per ArkUI
// component, sized/positioned from its $rect, carrying its type/text/accessibility attrs. It's
// invisible (transparent) but present in the DOM/accessibility tree and individually hoverable/
// selectable (each node is pointer-events:auto; only the container itself stays pointer-events:none,
// so empty gaps between components still fall through to the image), so anything reading the page's
// structure — accessibility snapshots, text extraction, DOM queries, or a human using the browser's
// own "inspect element" picker — can select the actual component instead of just a flat screenshot.
// Taps still reach the image's input-forwarding handlers regardless of which element they landed on,
// since those are bound on the screen container and pointer events bubble up to it either way. The
// tree is only rebuilt when it actually changes (a cheap string-equality check against the last
// /inspector response) — rebuilding on every poll would otherwise replace every node's DOM identity
// ~once a second, which is enough to make an in-progress click/hover/selection in DevTools miss its
// target mid-interaction.
export const VIEWER_HTML = `<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HarmonyOS ArkUI Live Preview</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; min-height:100vh; display:flex; flex-direction:column; align-items:center;
    gap:14px; padding:20px 0 32px; background:#0f1115; color:#e6e8ee;
    font:14px/1.5 ui-sans-serif,-apple-system,"PingFang SC",sans-serif; }
  .bar { display:flex; gap:10px; align-items:center; font-size:13px; color:#9aa3b2; }
  .dot { width:8px; height:8px; border-radius:50%; background:#6b7280; transition:.3s; flex:none; }
  .dot.live { background:#22c55e; box-shadow:0 0 8px #22c55e; }
  .dot.wait { background:#f0b429; }
  .dot.err { background:#ef4444; box-shadow:0 0 8px #ef4444; }
  .dot.build { background:#3b82f6; box-shadow:0 0 8px #3b82f6; }
  #panels { display:flex; flex-wrap:wrap; gap:28px; justify-content:center; padding:0 16px; }
  .panel { display:flex; flex-direction:column; align-items:center; gap:10px; }
  .phone { position:relative; padding:12px; border-radius:44px; background:#1b1e26;
    box-shadow:0 20px 60px rgba(0,0,0,.5), inset 0 0 0 1px #2a2f3a; }
  .screen { border-radius:32px;
    overflow:hidden; background:#fff; position:relative; touch-action:none; cursor:default; outline:none; }
  .grip { position:absolute; right:-4px; bottom:-4px; width:26px; height:26px; border-radius:9px;
    background:#2a2f3a; border:1px solid #3b4250; color:#9aa3b2; cursor:nwse-resize;
    touch-action:none; display:flex; align-items:center; justify-content:center; font-size:11px;
    user-select:none; }
  .grip:hover, .grip.on { border-color:#3b82f6; color:#e6e8ee; }
  .size { color:#9aa3b2; }
  .size.on { color:#3b82f6; }
  .screen.kb { box-shadow:0 0 0 3px #22c55e; }
  .screen img { width:100%; height:100%; object-fit:fill; display:block; -webkit-user-drag:none; user-select:none; }
  .a11y { position:absolute; inset:0; pointer-events:none; overflow:hidden; }
  .a11y div { position:absolute; overflow:hidden; color:transparent; font-size:10px; line-height:1;
    pointer-events:auto; }
  .ph { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
    color:#9aa3b2; font-size:13px; text-align:center; padding:0 24px; }
  .err { position:absolute; left:0; right:0; bottom:0; max-height:55%; overflow:auto;
    background:rgba(127,29,29,.96); color:#fecaca; font:12px/1.45 ui-monospace,Menlo,monospace;
    padding:12px 14px; white-space:pre-wrap; display:none; border-top:2px solid #ef4444; }
  .err b { color:#fff; display:block; margin-bottom:6px; font-family:ui-sans-serif; }
  #building { display:none; background:#1d4ed8; color:#fff; font-size:12px; padding:3px 12px; border-radius:999px; }
  .tools { display:flex; gap:8px; align-items:center; }
  .tools button { background:#1b1e26; color:#e6e8ee; border:1px solid #2a2f3a; border-radius:10px;
    padding:6px 14px; font-size:13px; cursor:pointer; }
  .tools button:hover { border-color:#3b82f6; }
  .tools button.on { border-color:#22c55e; color:#22c55e; }
  code { color:#c8cddb; background:#1b1e26; padding:2px 6px; border-radius:6px; }
</style></head><body>
  <div class="bar"><span class="dot" id="gdot"></span><span id="gstatus">连接中…</span><span id="building"></span></div>
  <div id="panels"></div>
  <div class="bar">点按 / 拖动 / 滑动屏幕即可交互 · 拖右下角 <code>⇲</code> 改设备尺寸 · 改 <code>.ets</code> 保存自动重建 · 零 DevEco</div>
<script>
  const panelsEl = document.getElementById('panels'), gdot = document.getElementById('gdot'),
        gstatus = document.getElementById('gstatus'), buildingEl = document.getElementById('building');

  // One panel per configured device — DOM + its own input/frame/inspector state, all scoped in the
  // closures below (mirrors what used to be module-level consts back when there was exactly one
  // panel). applyStatus() is called from the single shared /status poll below; pollFrame/pollInspector
  // run their own per-panel loops since image bytes and the component tree can't ride along in the
  // JSON status response.
  function createPanel(device) {
    const prefix = '/devices/' + encodeURIComponent(device.id);
    const root = document.createElement('div'); root.className = 'panel';

    const bar = document.createElement('div'); bar.className = 'bar';
    const dot = document.createElement('span'); dot.className = 'dot';
    const label = document.createElement('span');
    const sizeEl = document.createElement('span'); sizeEl.className = 'size';
    bar.append(dot, label, sizeEl);

    const phone = document.createElement('div'); phone.className = 'phone';
    const screen = document.createElement('div'); screen.className = 'screen'; screen.tabIndex = 0;
    const img = document.createElement('img'); img.alt = ''; img.draggable = false;
    const a11y = document.createElement('div'); a11y.className = 'a11y';
    const ph = document.createElement('div'); ph.className = 'ph'; ph.textContent = '连接中…';
    const errEl = document.createElement('div'); errEl.className = 'err';
    const grip = document.createElement('div'); grip.className = 'grip'; grip.textContent = '⇲';
    grip.title = '拖动改变这块面板的设备尺寸（引擎原地改，不重建）';
    screen.append(img, a11y, ph, errEl);
    phone.append(screen, grip);

    const tools = document.createElement('div'); tools.className = 'tools';
    const backBtn = document.createElement('button'); backBtn.title = '系统返回'; backBtn.textContent = '← 返回';
    const kbBtn = document.createElement('button'); kbBtn.title = '点击后可用电脑键盘向聚焦输入框打字'; kbBtn.textContent = '⌨ 键盘：关';
    tools.append(backBtn, kbBtn);

    root.append(bar, phone, tools);
    panelsEl.appendChild(root);

    // ---- geometry: device px ⇄ on-screen px ------------------------------
    // rw/rh/dpi是这块面板“当前”的设备几何——它会变（拖 .grip 改尺寸、或别的客户端改了尺寸后从
    // /status 同步回来），所以凡是依赖它的地方（截图框比例、inspector 的 $rect 基准、坐标归一化的
    // 分母在服务端）都要跟着重算。scale 是设备像素 ÷ 屏幕显示像素，纯展示用：保证再大的设备也不
    // 会把页面撑出视口。
    let rw = device.resolution[0], rh = device.resolution[1], dpi = device.density || 480;
    let scale = 1;
    const MIN_PX = 50, MAX_PX = 3000; // 与引擎 ResolutionSwitch 的合法区间一致
    const clampPx = (v) => Math.min(MAX_PX, Math.max(MIN_PX, Math.round(v)));

    function fitScale(w, h) {
      const maxW = 380, maxH = Math.max(320, window.innerHeight * 0.66);
      return Math.max(w / maxW, h / maxH, 1); // 只缩不放
    }
    function applyDisplaySize(w, h, s) {
      screen.style.width = Math.round(w / s) + 'px';
      screen.style.height = Math.round(h / s) + 'px';
    }
    function renderSize(pending) {
      const vp = (px) => Math.round(px / (dpi / 160));
      sizeEl.textContent = pending
        ? '· ' + pending.w + '×' + pending.h + ' @' + dpi + 'dpi'
        : '· ' + rw + '×' + rh + ' @' + dpi + 'dpi · ' + vp(rw) + '×' + vp(rh) + 'vp';
      sizeEl.classList.toggle('on', !!pending);
    }
    function setGeometry(w, h, d) {
      const changed = w !== rw || h !== rh || d !== dpi;
      rw = w; rh = h; dpi = d;
      scale = fitScale(rw, rh);
      applyDisplaySize(rw, rh, scale);
      // $rect 是以帧分辨率为基准的绝对坐标，尺寸变了整棵叠加层都得按新基准重建。
      if (changed) lastInspectorText = '';
      renderSize();
    }

    // 拖右下角改尺寸：拖动过程只改本地显示（引擎不受打扰），松手才发一次 /resize。
    let resizing = null;
    grip.addEventListener('pointerdown', (e) => {
      e.preventDefault(); e.stopPropagation();
      try { grip.setPointerCapture(e.pointerId); } catch {}
      resizing = { x: e.clientX, y: e.clientY, w: rw, h: rh, scale, target: { w: rw, h: rh } };
      grip.classList.add('on');
    });
    grip.addEventListener('pointermove', (e) => {
      if (!resizing) return;
      const w = clampPx(resizing.w + (e.clientX - resizing.x) * resizing.scale);
      const h = clampPx(resizing.h + (e.clientY - resizing.y) * resizing.scale);
      resizing.target = { w, h };
      applyDisplaySize(w, h, resizing.scale);
      renderSize({ w, h });
    });
    async function endResize() {
      if (!resizing) return;
      const { w, h } = resizing.target;
      resizing = null;
      grip.classList.remove('on');
      if (w === rw && h === rh) { setGeometry(rw, rh, dpi); return; }
      try {
        const r = await fetch(prefix + '/resize', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ width: w, height: h, density: dpi }),
        });
        if (r.ok) {
          const s = await r.json();
          setGeometry(s.resolution[0], s.resolution[1], s.density);
          bumpFast(); // 新尺寸的第一帧尽快取回来
          return;
        }
      } catch {}
      setGeometry(rw, rh, dpi); // 引擎没接受 → 回到它真正在显示的尺寸
    }
    grip.addEventListener('pointerup', endResize);
    grip.addEventListener('pointercancel', endResize);

    // ---- input → POST prefix/input --------------------------------------
    let kbOn = false, dragging = false, lastMoveAt = 0, fastUntil = 0;
    const bumpFast = () => { fastUntil = Date.now() + 1200; };
    const post = (msg) => { fetch(prefix + '/input', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(msg) }).catch(() => {}); bumpFast(); };
    function norm(e) {
      const r = img.getBoundingClientRect();
      const x = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
      const y = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
      return { x, y };
    }
    screen.addEventListener('pointerdown', (e) => {
      e.preventDefault(); screen.focus(); dragging = true;
      try { screen.setPointerCapture(e.pointerId); } catch {}
      const p = norm(e); post({ t: 'p', phase: 'down', x: p.x, y: p.y });
    });
    screen.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const now = Date.now(); if (now - lastMoveAt < 40) return; lastMoveAt = now;
      const p = norm(e); post({ t: 'p', phase: 'move', x: p.x, y: p.y });
    });
    const endDrag = (e) => { if (!dragging) return; dragging = false; const p = norm(e); post({ t: 'p', phase: 'up', x: p.x, y: p.y }); };
    screen.addEventListener('pointerup', endDrag);
    screen.addEventListener('pointercancel', endDrag);

    backBtn.addEventListener('click', () => post({ t: 'back' }));
    kbBtn.addEventListener('click', () => { kbOn = !kbOn; kbBtn.classList.toggle('on', kbOn); kbBtn.textContent = '⌨ 键盘：' + (kbOn ? '开' : '关'); if (kbOn) screen.focus(); });
    screen.addEventListener('keydown', (e) => {
      if (!kbOn) return;
      if (['Backspace', 'Tab', 'Enter', ' '].includes(e.key)) e.preventDefault();
      post({ t: 'key', key: e.key, code: e.code });
    });
    screen.addEventListener('blur', () => { if (kbOn) { kbOn = false; kbBtn.classList.remove('on'); kbBtn.textContent = '⌨ 键盘：关'; } });
    screen.addEventListener('focus', () => screen.classList.toggle('kb', kbOn));

    // ---- inspector tree → real DOM nodes over the frame ------------------
    const textAttrOf = (attrs) => {
      if (!attrs) return '';
      for (const k of ['content', 'text', 'placeholder', 'value']) {
        if (typeof attrs[k] === 'string' && attrs[k]) return attrs[k];
      }
      return '';
    };
    const a11yLabelOf = (attrs) => {
      if (!attrs) return '';
      for (const k of ['accessibilityText', 'accessibilityDescription']) {
        if (typeof attrs[k] === 'string' && attrs[k]) return attrs[k];
      }
      return '';
    };
    // $rect is in *global* frame coordinates (every node's x/y is relative to the whole screen, not
    // its parent) — but the DOM mirrors the component tree via real nesting, and CSS resolves a
    // percentage top/left against the nearest positioned ancestor (its immediate DOM parent here), not
    // the frame. So each node's percentage must be computed relative to its own parent's rect, not the
    // frame resolution — otherwise a nested node's offset gets applied twice.
    function buildA11yNode(n, parentRect) {
      const el = document.createElement('div');
      if (n.$type) el.setAttribute('data-arkui-type', n.$type);
      if (n.$debugLine) { try { el.setAttribute('data-debug-line', JSON.parse(n.$debugLine).$line || ''); } catch {} }
      let rect = parentRect;
      if (n.$rect) {
        const [x, y, w, h] = n.$rect.split(',').map(Number);
        rect = { x, y, w, h };
        const { x: px, y: py, w: pw, h: ph } = parentRect;
        if (pw && ph) {
          el.style.left = ((x - px) / pw * 100) + '%'; el.style.top = ((y - py) / ph * 100) + '%';
          el.style.width = (w / pw * 100) + '%'; el.style.height = (h / ph * 100) + '%';
        }
      }
      const text = textAttrOf(n.$attrs), label = a11yLabelOf(n.$attrs) || text;
      if (label) el.setAttribute('aria-label', label);
      if (text) el.textContent = text;
      (n.$children || []).forEach((c) => el.appendChild(buildA11yNode(c, rect)));
      return el;
    }
    let inspectorBusy = false, lastInspectorText = '';
    async function pollInspector() {
      if (!inspectorBusy) {
        inspectorBusy = true;
        try {
          const r = await fetch(prefix + '/inspector', { cache: 'no-store' });
          if (r.ok) {
            const text = await r.text();
            if (text !== lastInspectorText) {
              lastInspectorText = text;
              const tree = JSON.parse(text);
              a11y.innerHTML = '';
              // The synthetic top-level "root" node carries no $rect (only bare width/height fields),
              // so as an absolutely-positioned element it collapses to 0×0. Skip it and anchor its
              // real children straight to .a11y (whose box is the full frame, i.e. the same
              // coordinate origin $rect itself uses: 0,0,resolution).
              const frameRect = { x: 0, y: 0, w: rw, h: rh };
              (tree?.$children || []).forEach((c) => a11y.appendChild(buildA11yNode(c, frameRect)));
            }
          }
        } catch {} finally { inspectorBusy = false; }
      }
      setTimeout(pollInspector, 1200);
    }

    // ---- adaptive frame poll ----------------------------------------------
    async function pollFrame() {
      try {
        const r = await fetch(prefix + '/frame.jpg?t=' + Date.now(), { cache: 'no-store' });
        if (r.ok) {
          const url = URL.createObjectURL(await r.blob());
          const old = img.src; img.src = url; if (old.startsWith('blob:')) URL.revokeObjectURL(old);
          img.style.display = 'block'; ph.style.display = 'none';
        }
      } catch {}
      setTimeout(pollFrame, Date.now() < fastUntil ? 90 : 350);
    }

    // ---- status (driven by the shared /status poll, not a per-panel fetch) ----
    function applyStatus(s) {
      label.textContent = device.id;
      // 尺寸可能是被别人改的（drive.mjs resize、另一个打开着的 viewer），服务端状态是唯一真源——
      // 除非此刻本地正在拖动，否则一律跟随它。
      if (!resizing && Array.isArray(s.resolution)
        && (s.resolution[0] !== rw || s.resolution[1] !== rh || (s.density && s.density !== dpi))) {
        setGeometry(s.resolution[0], s.resolution[1], s.density || dpi);
      }
      kbBtn.style.display = s.interactive ? '' : 'none';
      backBtn.style.display = s.interactive ? '' : 'none';
      if (s.engineError) {
        errEl.style.display = 'block';
        errEl.innerHTML = '<b>⚠ 引擎运行时错误</b>' + String(s.engineError).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
      } else {
        errEl.style.display = 'none';
      }
      let text;
      if (s.engineConnected && s.hasFrame) { dot.className = 'dot live'; text = '在线 · 可交互 · :' + s.port; }
      else if (s.engineConnected) { dot.className = 'dot wait'; text = '等待首帧…'; }
      else { dot.className = 'dot wait'; text = '等待引擎…'; }
      if (!s.hasFrame) { ph.textContent = text; ph.style.display = 'flex'; }
    }

    setGeometry(rw, rh, dpi);
    pollFrame(); pollInspector();
    return { applyStatus, refit: () => { scale = fitScale(rw, rh); applyDisplaySize(rw, rh, scale); } };
  }

  // ---- bootstrap: discover configured devices, then start polling loops ----
  const panels = new Map(); // deviceId -> { applyStatus }

  async function pollStatus() {
    try {
      const s = await (await fetch('/status', { cache: 'no-store' })).json();
      buildingEl.style.display = s.build === 'building' ? 'inline-block' : 'none';
      buildingEl.textContent = '构建中…';
      if (s.build === 'error') {
        gdot.className = 'dot err';
        gstatus.textContent = '构建失败 · ' + (s.buildError || '').split('\\n')[0];
      } else if (s.build === 'building') {
        gdot.className = 'dot build'; gstatus.textContent = '构建中…';
      } else {
        gdot.className = 'dot live'; gstatus.textContent = panels.size + ' 台设备';
      }
      for (const d of s.devices || []) { panels.get(d.id)?.applyStatus(d); }
    } catch {
      gdot.className = 'dot'; gstatus.textContent = '桥接未运行';
    }
  }

  async function boot() {
    let devices;
    try { devices = await (await fetch('/devices', { cache: 'no-store' })).json(); }
    catch { gstatus.textContent = '桥接未运行 · 重试中…'; setTimeout(boot, 1000); return; }
    for (const d of devices) panels.set(d.id, createPanel(d));
    pollStatus();
    setInterval(pollStatus, 400);
    // 窗口变大/变小时只重算展示缩放，设备几何本身不动。
    window.addEventListener('resize', () => { for (const p of panels.values()) p.refit(); });
  }
  boot();

  // ---- liveness: hold an SSE channel so the server releases the whole preview when this tab closes ----
  // The browser keeps /alive open for the page's lifetime; closing the tab drops it and the server
  // tears down every device's engine after a short grace. EventSource auto-reconnects across a
  // reload, so the grace window absorbs that without releasing.
  try { new EventSource('/alive'); } catch {}
</script></body></html>`;
