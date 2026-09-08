#!/usr/bin/env node
// Exercises the REAL scripts/lib/bridge.mjs (not the HTTP mock) against two fake "engines" — minimal
// hand-rolled WebSocket servers (no `ws` package; this skill has zero npm deps) that each push one
// JPEG-framed binary message per device, mirroring what engine.mjs's -lws socket does. This validates
// the part the HTTP-level mock (mock-bridge.mjs) can't reach: createBridge's per-device session Map,
// its WebSocket connect/generation logic, and setEngine(id, next) wiring — using the production code,
// not a re-implementation of it.
import http from 'node:http';
import crypto from 'node:crypto';
import { createBridge } from '../../../../../../plugins/harmonyos-ui-toolkit/skills/harmonyos-live-preview/scripts/lib/bridge.mjs';
import { createStatus } from '../../../../../../plugins/harmonyos-ui-toolkit/skills/harmonyos-live-preview/scripts/lib/status.mjs';

const WS_MAGIC = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';
const JPEG = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3, 4, 0xff, 0xd9]);

// Minimal WS server: accepts the handshake, then on demand sends one unmasked binary frame (server->
// client frames aren't masked per RFC6455) carrying a JPEG. Small enough to hand-roll instead of
// pulling in a dependency.
function startFakeEngine(port) {
  let clientSocket = null;
  const server = http.createServer((req, res) => { res.writeHead(404); res.end(); });
  server.on('upgrade', (req, socket) => {
    const key = req.headers['sec-websocket-key'];
    const accept = crypto.createHash('sha1').update(key + WS_MAGIC).digest('base64');
    socket.write(
      'HTTP/1.1 101 Switching Protocols\r\n' +
      'Upgrade: websocket\r\n' +
      'Connection: Upgrade\r\n' +
      `Sec-WebSocket-Accept: ${accept}\r\n\r\n`,
    );
    clientSocket = socket;
  });
  server.listen(port, '127.0.0.1');
  function sendFrame() {
    if (!clientSocket) return false;
    const len = JPEG.length;
    const header = len < 126 ? Buffer.from([0x82, len]) : null; // 0x82 = FIN+binary opcode
    if (!header) throw new Error('test frame too big for the 1-byte length path');
    try { clientSocket.write(Buffer.concat([header, JPEG])); return true; } catch { return false; }
  }
  return { sendFrame, close: () => { try { clientSocket?.destroy(); } catch {} server.close(); } };
}

let passed = 0, failed = 0;
const check = (name, cond, detail = '') => {
  if (cond) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.log(`  ✗ ${name}  ${detail}`); }
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const HTTP_PORT = 18901;
const base = `http://127.0.0.1:${HTTP_PORT}`;
const getJson = async (path) => (await fetch(`${base}${path}`)).json();

const config = {
  devices: [
    { id: 'phone', resolution: [1080, 2340] },
    { id: 'tablet', resolution: [2048, 1280] },
  ],
  autoRelease: false,
  releaseGraceMs: 10000,
};
const status = createStatus();
status.set({ state: 'ok', startedAt: Date.now() });

const bridge = createBridge(config, status, {}, () => {}); // silence logs
await new Promise((resolve) => bridge.listen(HTTP_PORT, resolve));

const phoneEngine = startFakeEngine(41300);
const tabletEngine = startFakeEngine(41301);

try {
  console.log('before setEngine — devices known but not connected:');
  let list = await getJson('/devices');
  check('lists both device ids', list.map((d) => d.id).join(',') === 'phone,tablet', JSON.stringify(list));
  check('neither connected yet', list.every((d) => !d.engineConnected && !d.hasFrame), JSON.stringify(list));

  console.log('setEngine + fake frame push:');
  bridge.setEngine('phone', { port: 41300, sid: 'x', device: 'phone', send: () => true, getInspectorTree: async () => ({ $type: 'root' }) });
  bridge.setEngine('tablet', { port: 41301, sid: 'y', device: 'tablet', send: () => true, getInspectorTree: async () => ({ $type: 'root' }) });
  await sleep(300); // let the WS handshake land
  check('phone engine sent a frame', phoneEngine.sendFrame());
  check('tablet engine sent a frame', tabletEngine.sendFrame());
  await sleep(300); // let the bridge's onmessage fire

  list = await getJson('/devices');
  const phone = list.find((d) => d.id === 'phone'), tablet = list.find((d) => d.id === 'tablet');
  check('phone connected + has frame', phone.engineConnected && phone.hasFrame, JSON.stringify(phone));
  check('tablet connected + has frame', tablet.engineConnected && tablet.hasFrame, JSON.stringify(tablet));
  check('resolutions kept separate', phone.resolution.join('x') === '1080x2340' && tablet.resolution.join('x') === '2048x1280');

  console.log('/status mirrors default device (phone) at the top level:');
  const st = await getJson('/status');
  check('top-level engineConnected mirrors phone', st.engineConnected === true && st.resolution.join('x') === '1080x2340', JSON.stringify(st));
  check('devices[] present with both', st.devices.length === 2);

  console.log('legacy unprefixed routes alias phone (the default device):');
  const legacyFrame = await fetch(`${base}/frame.jpg`);
  const namespacedFrame = await fetch(`${base}/devices/phone/frame.jpg`);
  check('legacy /frame.jpg == /devices/phone/frame.jpg', legacyFrame.status === 200 && namespacedFrame.status === 200 &&
    Buffer.from(await legacyFrame.arrayBuffer()).equals(Buffer.from(await namespacedFrame.arrayBuffer())));

  console.log('tablet frame is independent of phone (namespacing not crossed):');
  const tabletFrame = await fetch(`${base}/devices/tablet/frame.jpg`);
  check('tablet route serves 200', tabletFrame.status === 200);

  console.log('unknown device id -> 404 with known-devices hint:');
  const bad = await fetch(`${base}/devices/watch/frame.jpg`);
  const badBody = await bad.json();
  check('404', bad.status === 404);
  check('mentions known devices', badBody.error.includes('phone') && badBody.error.includes('tablet'), badBody.error);

  console.log('reconnect generation: relaunching a device does not affect the other:');
  bridge.setEngine('tablet', { port: 41301, sid: 'y2', device: 'tablet', send: () => true, getInspectorTree: async () => ({ $type: 'root' }) });
  await sleep(200);
  list = await getJson('/devices');
  check('tablet dropped to not-yet-reconnected', list.find((d) => d.id === 'tablet').engineConnected === false, JSON.stringify(list));
  check('phone untouched by tablet relaunch', list.find((d) => d.id === 'phone').engineConnected === true, JSON.stringify(list));
} finally {
  bridge.close();
  phoneEngine.close();
  tabletEngine.close();
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
