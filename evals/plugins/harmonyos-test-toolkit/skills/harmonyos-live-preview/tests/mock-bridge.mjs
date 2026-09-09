#!/usr/bin/env node
// Mock of the preview bridge's HTTP surface, for end-to-end testing drive.mjs without a
// HarmonyOS toolchain. Reuses the real input.mjs so the event→command translation under
// test is the production one. Extra /debug/* routes let the test script mutate build
// state and read back the commands the "engine" received.
//
// Mirrors the real bridge.mjs's multi-device shape (scripts/lib/bridge.mjs): /status carries both
// the legacy top-level fields (mirroring the default/first device, for pre-multi-device callers) and
// a `devices` array; /devices lists the same array on its own; /devices/:id/{frame.jpg,inspector,
// input} are namespaced per device, and the unprefixed /frame.jpg, /inspector, /input alias the
// default device. Two devices ("phone", "tablet") are registered by default so --device targeting
// and `shot --all` have something real to exercise.
import http from 'node:http';
import { eventToCommands } from '../../../../../../plugins/harmonyos-test-toolkit/skills/harmonyos-live-preview/scripts/lib/input.mjs';
import { checkGeometry, SIZE_LIMITS } from '../../../../../../plugins/harmonyos-test-toolkit/skills/harmonyos-live-preview/scripts/lib/device-profile.mjs';

const port = Number(process.argv[2] ?? 18899);

const TREE = {
  $type: 'root', width: 1080, height: 2340,
  $children: [{
    $type: 'Column', $rect: '0,0,1080,2340', $attrs: {},
    $children: [
      { $type: 'Text', $rect: '100,200,300,80', $attrs: { content: 'Hello World' },
        $debugLine: '{"$line":"entry/src/main/ets/pages/Index.ets(12:9)","$packageName":"entry"}' },
      { $type: 'Button', $rect: '390,1200,300,120', $attrs: { content: '登录' },
        $debugLine: '{"$line":"entry/src/main/ets/pages/Index.ets(20:9)","$packageName":"entry"}' },
      { $type: 'Button', $rect: '[100.00,2000.00],[400.00,2080.00]', $attrs: { content: '登录二' } },
      { $type: 'TextInput', $rect: '100,900,880,120', $attrs: { placeholder: '请输入内容' } },
    ],
  }],
};
const FRAME = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3, 4, 0xff, 0xd9]);

const mockDevice = (id, device, resolution, density, port) => ({
  id, device, resolution, density, port,
  launchResolution: [...resolution], launchDensity: density, frameResolution: [...resolution],
  engineConnected: true, hasFrame: true, interactive: true, frameAgeMs: 100, engineError: null,
  inputs: [], tree: TREE,
});

const devices = new Map([
  ['phone', mockDevice('phone', 'phone', [1080, 2340], 480, 41200)],
  ['tablet', mockDevice('tablet', 'tablet', [2048, 1280], 320, 41201)],
]);
const defaultId = 'phone';

let build = { build: 'ok', buildError: null, buildAgeMs: 5000, buildStartedAgoMs: 6000, lastChangeAgeMs: null };

const deviceStatus = (d) => ({
  id: d.id, device: d.device, resolution: d.resolution, density: d.density,
  launchResolution: d.launchResolution, launchDensity: d.launchDensity,
  frameResolution: d.frameResolution, port: d.port,
  engineConnected: d.engineConnected, hasFrame: d.hasFrame, interactive: d.interactive,
  frameAgeMs: d.frameAgeMs, engineError: d.engineError,
});

function json(res, code, obj) { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); }

function serveDeviceSub(d, sub, req, res) {
  if (sub === '/frame.jpg') {
    if (!d.hasFrame) { res.writeHead(503); res.end('no frame yet'); return; }
    res.writeHead(200, { 'Content-Type': 'image/jpeg' }); res.end(FRAME);
  } else if (sub === '/inspector') {
    json(res, 200, d.tree);
  } else if (sub === '/input' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const cmds = eventToCommands(JSON.parse(body), d.resolution);
      d.inputs.push(...cmds);
      json(res, 200, { sent: cmds.length });
    });
  } else if (sub === '/resize' && req.method === 'POST') {
    // Mirrors the real bridge: same validation, same "geometry updates now, frame catches up
    // later" split. `frameLagMs` (settable via /debug/setDevice) fakes that lag so the CLI's
    // wait-for-the-pixels logic has something to wait on.
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      let geometry;
      try {
        const p = JSON.parse(body);
        geometry = { width: Math.round(+p.width), height: Math.round(+p.height), density: Math.round(+(p.density ?? d.density)) };
      } catch { return json(res, 400, { error: 'body must be JSON {width, height, density?}' }); }
      const problem = checkGeometry(geometry, { maxSize: SIZE_LIMITS.maxResizeSize });
      if (problem) return json(res, 400, { error: problem });
      if (!d.interactive) return json(res, 503, { error: 'engine command pipe not connected' });
      d.resolution = [geometry.width, geometry.height];
      d.density = geometry.density;
      d.inputs.push(...eventToCommands({ t: 'resize', ...geometry }, d.resolution));
      const lag = d.frameLagMs ?? 0;
      if (lag) setTimeout(() => { d.frameResolution = [...d.resolution]; }, lag);
      else d.frameResolution = [...d.resolution];
      return json(res, 200, deviceStatus(d));
    });
  } else {
    res.writeHead(404); res.end();
  }
}

http.createServer((req, res) => {
  const route = req.url.split('?')[0];
  const parts = route.split('/').filter(Boolean);

  if (route === '/status') {
    json(res, 200, { ...deviceStatus(devices.get(defaultId)), devices: [...devices.values()].map(deviceStatus), ...build });
    return;
  }
  if (route === '/devices') { json(res, 200, [...devices.values()].map(deviceStatus)); return; }

  if (parts[0] === 'devices' && parts[1]) {
    const d = devices.get(parts[1]);
    if (!d) { json(res, 404, { error: `unknown device "${parts[1]}"` }); return; }
    serveDeviceSub(d, '/' + parts.slice(2).join('/'), req, res);
    return;
  }

  // Legacy unprefixed routes alias the default device — same as real bridge.mjs.
  if (route === '/frame.jpg' || route === '/inspector'
    || ((route === '/input' || route === '/resize') && req.method === 'POST')) {
    serveDeviceSub(devices.get(defaultId), route, req, res);
    return;
  }

  if (route === '/debug/set' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const patch = JSON.parse(body);
      const { devices: _ignored, ...buildPatch } = patch;
      build = { ...build, build: buildPatch.build ?? build.build, buildError: 'buildError' in buildPatch ? buildPatch.buildError : build.buildError,
        buildAgeMs: buildPatch.buildAgeMs ?? build.buildAgeMs, buildStartedAgoMs: buildPatch.buildStartedAgoMs ?? build.buildStartedAgoMs,
        lastChangeAgeMs: 'lastChangeAgeMs' in buildPatch ? buildPatch.lastChangeAgeMs : build.lastChangeAgeMs };
      // Back-compat: the old single-device tests patch engineConnected/hasFrame/etc at the top level —
      // treat that as patching the default device, mirroring the old mock's flat `state` object.
      const d = devices.get(defaultId);
      for (const k of ['engineConnected', 'hasFrame', 'interactive', 'frameAgeMs', 'port', 'resolution', 'engineError']) {
        if (k in buildPatch) d[k] = buildPatch[k];
      }
      json(res, 200, { ...deviceStatus(d), devices: [...devices.values()].map(deviceStatus), ...build });
    });
  } else if (route === '/debug/setDevice' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const { id, ...patch } = JSON.parse(body);
      const d = devices.get(id);
      if (!d) { json(res, 404, { error: `unknown device "${id}"` }); return; }
      Object.assign(d, patch);
      json(res, 200, deviceStatus(d));
    });
  } else if (route === '/debug/inputs') {
    const id = new URL(req.url, 'http://x').searchParams.get('device') ?? defaultId;
    json(res, 200, devices.get(id)?.inputs ?? []);
  } else if (route === '/debug/clear') {
    for (const d of devices.values()) d.inputs.length = 0;
    json(res, 200, []);
  } else {
    res.writeHead(404); res.end();
  }
}).listen(port, '127.0.0.1', () => console.log(`mock bridge on :${port}`));
