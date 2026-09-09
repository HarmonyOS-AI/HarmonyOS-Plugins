// HarmonyOS Previewer engine -> browser bridge (no external deps; Node >= 21 for global WebSocket).
//
// The orchestrator owns each device's engine lifecycle and hands the bridge that engine's target via
// setEngine(deviceId, {port, sid, device}); the bridge connects to that frame WebSocket, strips the
// JPEG framing, and serves the latest frame + build status to a browser. Direct handoff (vs. scanning
// `ps`) keeps the bridge decoupled from process listing and robust across rebuilds: a per-device
// `generation` counter invalidates the reconnect loop of any superseded engine.
//
// One HTTP server serves N devices (config.devices — one Previewer engine process per configured
// size/profile, since the engine reads its resolution once at launch and never re-reads it — see
// engine.mjs). Routes are namespaced per device (`/devices/:id/...`); the unprefixed legacy routes
// (`/status`, `/frame.jpg`, `/inspector`, `/input`, `/resize`, `/mjpeg`) keep working unchanged as
// aliases for the first configured device, so every pre-multi-device caller (drive.mjs without
// --device, host preview tools reading /status) needs no changes.
//
// A device's size is not fixed for the life of the run: `/devices/:id/resize` drives the engine's own
// ResolutionSwitch command in place (no rebuild, no reconnect), and the bridge tracks the resulting
// geometry so pointer coordinates keep scaling correctly and the size survives the engine restarts a
// rebuild causes.
import http from 'node:http';
import { VIEWER_HTML } from './viewer-page.mjs';
import { eventToCommands } from './input.mjs';
import { checkGeometry, SIZE_LIMITS } from './device-profile.mjs';
import { SERVICE_ID } from './registry.mjs';

const SOI = Buffer.from([0xff, 0xd8, 0xff]);
const EOI = Buffer.from([0xff, 0xd9]);
const ts = () => new Date().toISOString().slice(11, 19);

function extractJpeg(buf) {
  const s = buf.indexOf(SOI);
  if (s < 0) return null;
  const e = buf.indexOf(EOI, s + 3);
  return e > s ? buf.subarray(s, e + 2) : null;
}

// [width, height] straight out of the JPEG's SOF header. A resize lands in the engine before it
// lands in the pixels (~200ms later), so this is the only way a caller can tell "the frame I'm
// holding is already the new size" apart from "it's still the old one" — `drive.mjs resize` waits
// on it so a `shot` right after a resize can't capture the previous geometry.
function jpegDimensions(buf) {
  let i = 2;
  while (i + 9 < buf.length) {
    if (buf[i] !== 0xff) { i++; continue; }
    const marker = buf[i + 1];
    // SOFn carries the dimensions; 0xc4/0xc8/0xcc are DHT/JPG/DAC, which do not.
    if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
      return [buf.readUInt16BE(i + 7), buf.readUInt16BE(i + 5)];
    }
    if (marker === 0xd8 || (marker >= 0xd0 && marker <= 0xd9)) { i += 2; continue; }
    i += 2 + buf.readUInt16BE(i + 2);
  }
  return null;
}

export function createBridge(config, status, hooks = {}, log = (...a) => console.log(ts(), '[bridge]', ...a)) {
  const deviceIds = config.devices.map((d) => d.id);
  const defaultId = deviceIds[0];

  // Per-device session: everything that used to be a single set of closure variables (target/send/
  // ws/connected/lastFrame/…) is now one of these per configured size, keyed by device id.
  function newSession(d) {
    return {
      id: d.id,
      // launch* is the geometry the engine process is started with; resolution/density is what it
      // is showing *now*. They differ once someone resizes at runtime (ResolutionSwitch) — and
      // since a rebuild relaunches the engine back at its launch geometry, that difference is
      // exactly the signal to replay the resize on the new process (see setEngine/connect).
      launchResolution: d.resolution,
      launchDensity: d.density,
      resolution: [...d.resolution],
      density: d.density,
      pendingResize: false,
      target: null,          // { port, sid, device } — set via setEngine
      send: null,            // current engine's command sender
      getInspectorTree: null,
      getLastEngineError: null,
      ws: null,
      connected: false,
      lastFrame: null,
      lastFrameAt: 0,
      frameResolution: null, // geometry of the pixels actually held, from the JPEG header
      generation: 0,         // bumped on every setEngine; stale closures bail when it changes
      reconnectTimer: null,
      kickTimer: null,
      clients: new Set(),    // /mjpeg subscribers for this device
    };
  }
  const sessions = new Map(deviceIds.map((id, i) => [id, newSession(config.devices[i])]));

  // Browser-viewer liveness -> auto-release. This stays global (one browser tab looking at the whole
  // multi-panel page, not one per device): each open viewer holds an SSE /alive connection, so a
  // closed tab fires req.on('close') immediately. When the last viewer leaves we release the whole
  // preview (onIdle, which tears down every device's engine) after a short grace. Armed only after a
  // browser has actually connected (`everViewed`), so the documented headless curl flow — which never
  // opens /alive — is never torn down underneath the user.
  const onIdle = typeof hooks.onIdle === 'function' ? hooks.onIdle : null;
  const autoRelease = config.autoRelease !== false;
  const graceMs = Number.isFinite(config.releaseGraceMs) ? config.releaseGraceMs : 10000;
  const viewers = new Set();
  let everViewed = false;
  let releaseTimer = null;

  function maybeScheduleRelease() {
    if (!autoRelease || !onIdle || !everViewed || viewers.size > 0 || releaseTimer) return;
    releaseTimer = setTimeout(() => {
      releaseTimer = null;
      if (viewers.size === 0) { log(`no viewer for ${graceMs}ms — releasing preview`); onIdle(); }
    }, graceMs);
  }

  function pushToClients(session, jpeg) {
    for (const res of session.clients) {
      try {
        res.write(`--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ${jpeg.length}\r\n\r\n`);
        res.write(jpeg);
        res.write('\r\n');
      } catch { session.clients.delete(res); }
    }
  }

  function connect(session, gen) {
    if (gen !== session.generation || !session.target) return;
    const url = `ws://127.0.0.1:${session.target.port}/${session.target.sid}`;
    let socket;
    try { socket = new WebSocket(url); } catch { scheduleReconnect(session, gen); return; }
    session.ws = socket;
    socket.binaryType = 'arraybuffer';

    // A freshly forked engine is silent until it renders; reconnect if no frame primes quickly.
    let primed = false;
    clearTimeout(session.kickTimer);
    session.kickTimer = setTimeout(() => { if (!primed) { try { socket.close(); } catch {} } }, 1500);

    socket.onmessage = (ev) => {
      if (gen !== session.generation) return;
      const jpeg = extractJpeg(Buffer.from(ev.data));
      if (!jpeg) return;
      if (!primed) {
        primed = true; session.connected = true; clearTimeout(session.kickTimer);
        log(`[${session.id}] first frame (${jpeg.length}B)`);
        // A rendered frame proves the engine is up and its command pipe connected, which is the
        // earliest safe moment to re-apply a runtime resize the last engine had (see newSession).
        if (session.pendingResize) {
          session.pendingResize = false;
          const [w, h] = session.resolution;
          if (applyResize(session, { width: w, height: h, density: session.density })) {
            log(`[${session.id}] re-applied ${w}x${h}@${session.density}dpi after engine restart`);
          } else {
            log(`[${session.id}] could not re-apply ${w}x${h} — engine kept its launch size`);
            session.resolution = [...session.launchResolution];
            session.density = session.launchDensity;
          }
        }
      }
      session.lastFrame = jpeg;
      session.lastFrameAt = Date.now();
      session.frameResolution = jpegDimensions(jpeg) ?? session.frameResolution;
      pushToClients(session, jpeg);
    };
    const retry = () => {
      if (gen !== session.generation) return;
      session.connected = false;
      session.ws = null;
      scheduleReconnect(session, gen);
    };
    socket.onclose = retry;
    socket.onerror = retry;
  }

  function scheduleReconnect(session, gen) {
    clearTimeout(session.reconnectTimer);
    session.reconnectTimer = setTimeout(() => connect(session, gen), 700);
  }

  function setEngine(deviceId, next) {
    const session = sessions.get(deviceId);
    if (!session) { log(`setEngine: unknown device "${deviceId}" (known: ${deviceIds.join(', ')})`); return; }
    session.generation++;
    session.target = next;
    session.send = typeof next.send === 'function' ? next.send : null;
    session.getInspectorTree = typeof next.getInspectorTree === 'function' ? next.getInspectorTree : null;
    session.getLastEngineError = typeof next.getLastEngineError === 'function' ? next.getLastEngineError : null;
    session.connected = false;
    // A fresh engine process always starts at its launch geometry, so a runtime resize has to be
    // replayed once it renders. Reconnects to the *same* engine keep their size, but replaying is
    // idempotent, so it costs nothing to be safe here.
    session.pendingResize = session.resolution[0] !== session.launchResolution[0]
      || session.resolution[1] !== session.launchResolution[1]
      || session.density !== session.launchDensity;
    if (session.ws) { try { session.ws.onmessage = session.ws.onclose = session.ws.onerror = null; session.ws.close(); } catch {} session.ws = null; }
    log(`[${deviceId}] engine target :${next.port} (device=${next.device})`);
    connect(session, session.generation);
  }

  // Sends the engine's own in-place resolution change (ResolutionSwitch). Returns false when the
  // command pipe isn't connected — the caller decides whether that's a 503 or a dropped replay.
  function applyResize(session, geometry) {
    if (!session.send) return false;
    const [cmd] = eventToCommands({ t: 'resize', ...geometry }, session.resolution);
    return !!cmd && session.send(cmd);
  }

  // MJPEG keepalive: re-push each device's last frame so single-frame streams still render and stay
  // alive.
  const keepalive = setInterval(() => {
    for (const session of sessions.values()) {
      if (session.lastFrame && session.clients.size) pushToClients(session, session.lastFrame);
    }
  }, 1000);

  // /alive keepalive: a periodic comment keeps the SSE stream warm and surfaces half-open sockets
  // (a failed write closes the response, firing its 'close' handler so the viewer count stays true).
  const viewerPing = setInterval(() => {
    for (const res of viewers) { try { res.write(': ping\n\n'); } catch { try { res.end(); } catch {} } }
  }, 5000);

  // One device's status, in the shape both /devices entries and the legacy /status top level share.
  function deviceStatus(session) {
    return {
      id: session.id,
      device: session.target?.device ?? session.id,
      // Live geometry: `resolution`/`density` follow runtime resizes, launchResolution/launchDensity
      // stay at what the engine process was started with.
      resolution: session.resolution,
      density: session.density,
      launchResolution: session.launchResolution,
      launchDensity: session.launchDensity,
      // What the frame currently in hand actually measures — lags `resolution` by the ~200ms the
      // engine needs to re-render after a resize.
      frameResolution: session.frameResolution,
      port: session.target?.port ?? null,
      engineConnected: session.connected,
      hasFrame: !!session.lastFrame,
      interactive: typeof session.send === 'function',
      frameAgeMs: session.lastFrame ? Date.now() - session.lastFrameAt : null,
      // Engine's own runtime-error channel (ACE onError, relayed as an unsolicited FastPreviewMsg
      // pipe push — see engine.mjs). null in the common case; set when a page built fine but errored
      // or blanked at runtime, complementing PREVIEW_ENGINE_LOG=1 stdout scraping.
      engineError: session.getLastEngineError ? session.getLastEngineError() : null,
    };
  }

  function sendInput(session, req, res) {
    // Browser input → engine commands (tap/swipe/key/back) over that device's command pipe.
    // Coordinates arrive normalized (0..1) and are scaled to that device's px by input.mjs.
    let body = '';
    req.on('data', (d) => { body += d; if (body.length > 1e4) req.destroy(); });
    req.on('end', () => {
      let sent = 0;
      try {
        const cmds = eventToCommands(JSON.parse(body), session.resolution);
        if (session.send) for (const c of cmds) { if (session.send(c)) sent++; }
      } catch { /* malformed body → no-op */ }
      res.writeHead(session.send ? 200 : 503, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify({ sent }));
    });
  }

  // Runtime size change for one panel — the engine keeps running, so there's no rebuild and no
  // reconnect; the frame simply comes back at the new geometry. This is what the viewer's drag
  // handle and `drive.mjs resize` both go through.
  function resizeDevice(session, req, res) {
    let body = '';
    req.on('data', (d) => { body += d; if (body.length > 1e4) req.destroy(); });
    req.on('end', () => {
      const reply = (code, payload) => {
        res.writeHead(code, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        res.end(JSON.stringify(payload));
      };
      let geometry;
      try {
        const parsed = JSON.parse(body);
        geometry = {
          width: Math.round(Number(parsed.width)),
          height: Math.round(Number(parsed.height)),
          density: Math.round(Number(parsed.density ?? session.density)),
        };
      } catch { return reply(400, { error: 'body must be JSON {width, height, density?}' }); }

      // The runtime command tops out lower than the launch parameter does (see device-profile.mjs).
      const problem = checkGeometry(geometry, { maxSize: SIZE_LIMITS.maxResizeSize });
      if (problem) return reply(400, { error: problem });
      if (!session.send) return reply(503, { error: 'engine command pipe not connected' });
      if (!applyResize(session, geometry)) return reply(503, { error: 'engine dropped the resize command' });

      session.resolution = [geometry.width, geometry.height];
      session.density = geometry.density;
      log(`[${session.id}] resized to ${geometry.width}x${geometry.height}@${geometry.density}dpi`);
      return reply(200, deviceStatus(session));
    });
  }

  function sendInspector(session, res) {
    // ArkUI's own component tree for this device, straight from its engine's "inspector" command.
    // Only populated when that engine is running a PreviewBuild bundle; gated on a rendered frame — an
    // "inspector" command sent before the app has loaded segfaults the engine (observed on SDK
    // 26.0.0), so callers get a 503 until the first frame proves the app is up.
    if (!session.getInspectorTree || !session.lastFrame) {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'engine not ready' }));
      return;
    }
    session.getInspectorTree().then((tree) => {
      if (!tree) {
        res.writeHead(503, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        res.end(JSON.stringify({ error: 'no tree available' }));
        return;
      }
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify(tree));
    });
  }

  function sendFrame(session, res) {
    if (!session.lastFrame) { res.writeHead(503); res.end('no frame yet'); return; }
    res.writeHead(200, { 'Content-Type': 'image/jpeg', 'Cache-Control': 'no-store' });
    res.end(session.lastFrame);
  }

  function sendMjpeg(session, req, res) {
    res.writeHead(200, {
      'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
      'Cache-Control': 'no-cache, no-store', Connection: 'close', Pragma: 'no-cache',
    });
    session.clients.add(res);
    if (session.lastFrame) pushToClients(session, session.lastFrame);
    req.on('close', () => session.clients.delete(res));
  }

  const server = http.createServer((req, res) => {
    const route = req.url.split('?')[0];
    const parts = route.split('/').filter(Boolean); // '/devices/tablet/frame.jpg' -> ['devices','tablet','frame.jpg']

    if (route === '/' || route === '/index.html') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(VIEWER_HTML);
      return;
    }

    if (route === '/devices') {
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify(deviceIds.map((id) => deviceStatus(sessions.get(id)))));
      return;
    }

    // Per-device namespace: /devices/:id/{frame.jpg,inspector,input,mjpeg}
    if (parts[0] === 'devices' && parts[1]) {
      const id = decodeURIComponent(parts[1]);
      const session = sessions.get(id);
      if (!session) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: `unknown device "${id}" (known: ${deviceIds.join(', ')})` }));
        return;
      }
      const sub = '/' + parts.slice(2).join('/');
      if (sub === '/frame.jpg') return sendFrame(session, res);
      if (sub === '/inspector') return sendInspector(session, res);
      if (sub === '/input' && req.method === 'POST') return sendInput(session, req, res);
      if (sub === '/resize' && req.method === 'POST') return resizeDevice(session, req, res);
      if (sub === '/mjpeg') return sendMjpeg(session, req, res);
      res.writeHead(404); res.end('not found');
      return;
    }

    if (route === '/status') {
      const bs = status.get();
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify({
        // Lets a caller probing this port confirm it reached *our* preview and not some other
        // service that happens to be listening (registry.probe).
        service: SERVICE_ID,
        // Legacy top-level fields mirror the default (first configured) device — unchanged shape for
        // every pre-multi-device consumer. `devices` is the additive full breakdown.
        ...deviceStatus(sessions.get(defaultId)),
        devices: deviceIds.map((id) => deviceStatus(sessions.get(id))),
        build: bs?.state ?? null,
        buildError: bs?.error ?? null,
        buildAgeMs: bs?.ts ? Date.now() - bs.ts : null,
        // Ordering pair for "has the latest edit been built?": a build whose start is at or after
        // the newest watched change means the current artifacts include that change.
        buildStartedAgoMs: bs?.startedAt ? Date.now() - bs.startedAt : null,
        lastChangeAgeMs: status.lastChangeAt?.() ? Date.now() - status.lastChangeAt() : null,
      }));
      return;
    }

    // Unprefixed legacy routes alias the default device.
    const defaultSession = sessions.get(defaultId);
    if (route === '/input' && req.method === 'POST') return sendInput(defaultSession, req, res);
    if (route === '/resize' && req.method === 'POST') return resizeDevice(defaultSession, req, res);
    if (route === '/inspector') return sendInspector(defaultSession, res);
    if (route === '/mjpeg') return sendMjpeg(defaultSession, req, res);
    if (route === '/frame.jpg') return sendFrame(defaultSession, res);

    if (route === '/alive') {
      // Browser-liveness channel: the viewer holds this SSE stream open for its whole lifetime, so
      // closing the tab drops the socket and req.on('close') fires at once. A reload briefly closes
      // then reopens — the grace timer (cleared on any new viewer) tolerates that.
      res.writeHead(200, {
        'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache, no-store',
        Connection: 'keep-alive',
      });
      res.write(': connected\n\n');
      viewers.add(res);
      everViewed = true;
      if (releaseTimer) { clearTimeout(releaseTimer); releaseTimer = null; }
      req.on('close', () => { viewers.delete(res); maybeScheduleRelease(); });
      return;
    }

    res.writeHead(404); res.end('not found');
  });

  return {
    setEngine,
    listen: (port, cb) => server.listen(port, '127.0.0.1', cb),
    close: () => {
      for (const session of sessions.values()) {
        session.generation++;
        clearTimeout(session.reconnectTimer);
        clearTimeout(session.kickTimer);
        try { session.ws?.close(); } catch {}
        for (const res of session.clients) { try { res.end(); } catch {} }
      }
      clearInterval(keepalive);
      clearInterval(viewerPing);
      clearTimeout(releaseTimer);
      for (const res of viewers) { try { res.end(); } catch {} }
      server.close();
    },
  };
}
