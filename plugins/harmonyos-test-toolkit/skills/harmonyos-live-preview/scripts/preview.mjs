#!/usr/bin/env node
// Zero-DevEco HarmonyOS ArkUI live preview — single-process orchestrator.
//
//   edit .ets  ──▶  hvigorw PreviewBuild (CLI builds the project model itself)
//              ──▶  relaunch the standalone Previewer engine on the fresh artifacts
//              ──▶  hand the new engine target to the in-process browser bridge
//              ──▶  browser updates within ~300ms
//
// No DevEco IDE, no hvigor preview-service, no projectConfig reconstruction. Point it at any
// HarmonyOS project root; the previewable module and its settings are auto-discovered.
import fs from 'node:fs';
import { resolveConfig } from './lib/config.mjs';
import { build } from './lib/builder.mjs';
import { launchEngine, stopEngine } from './lib/engine.mjs';
import { createBridge } from './lib/bridge.mjs';
import { createStatus, extractError } from './lib/status.mjs';
import { register, deviceConfigDir } from './lib/registry.mjs';
import { ensureDisplay } from './lib/display.mjs';
import { materializeDeviceConfigs } from './lib/device-profile.mjs';

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), '[preview]', ...a);

const HELP = `HarmonyOS ArkUI live preview (zero DevEco)

Usage: node preview.mjs --project <harmonyos-project-root> [options]

Options:
  --project <dir>    HarmonyOS project root (has build-profile.json5). Default: cwd
  --module <name>    Module to preview. Default: the entry-type module
  --page <route>     @Entry route to preview, e.g. pages/Index. Default: first page in the profile.
                     Any @Entry in the pages profile works (DevEco-style per-page preview).
  --device <spec>    Device size: a preset — phone (1080x2340@480dpi portrait) / tablet
                     (2048x1280@320dpi landscape) — or a custom size WxH[@dpi], optionally prefixed
                     with a device type: 1440x3200@560, tablet:1200x800, 2in1:2560x1600@240.
                     Sizes are 50-3840 px, dpi 120-640. Default: phone
  --devices <list>   Comma-separated device specs to preview *simultaneously*, side by side —
                     e.g. --devices phone,tablet,1440x3200@560. One Previewer engine process per
                     entry (each engine reads its resolution once at launch, so simultaneous sizes
                     need one process per size — see references/how-it-works.md). Overrides --device.
                     Sizes are also adjustable at runtime without a restart: drag a panel's corner in
                     the viewer, or \`drive.mjs resize <WxH[@dpi]>\`.
  --clt, --sdk <dir> HarmonyOS command-line-tools or DevEco bundle root (hvigorw + sdk/ derived from it).
                     Default: $HARMONY_SDK / $HARMONY_CLT, else common install locations are probed.
  --port <n>         Browser viewer HTTP port. Default: 8088
  --lws <n>          Base engine image-websocket port. Default: 41200. Each additional --devices entry
                     takes the next port up (phone=41200, tablet=41201, …).
  --ability-mode     Launch the real UIAbility (its lifecycle + whatever it loadContents) instead of
                     rendering --page directly. The shown page is then fixed by the ability, not --page.
  --no-watch         Build once and serve a static current-UI view (no edit-and-refresh)
  --keep-alive       Do not auto-release when the browser tab closes (for headless / always-on use).
                     Default: release the engine ~10s after the last viewer closes.
  -h, --help         Show this help

Then open the printed http://127.0.0.1:<port> in a browser.`;

function parseArgv(argv) {
  const opts = {};
  const flags = new Set(['--no-watch', '--ability-mode', '--keep-alive', '-h', '--help']);
  const keys = {
    '--project': 'project', '--module': 'module', '--page': 'page', '--device': 'device',
    '--devices': 'devices', '--clt': 'clt', '--sdk': 'clt', '--port': 'httpPort', '--lws': 'lwsPort',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--no-watch') opts.watch = false;
    else if (a === '--ability-mode') opts.abilityMode = true;
    else if (a === '--keep-alive') opts.keepAlive = true;
    else if (a === '-h' || a === '--help') opts.help = true;
    else if (keys[a]) opts[keys[a]] = argv[++i];
    else if (!a.startsWith('-') && !opts.project) opts.project = a; // bare positional = project
    else if (!flags.has(a)) { console.error(`unknown option: ${a}`); process.exit(2); }
  }
  return opts;
}

async function main() {
  const opts = parseArgv(process.argv.slice(2));
  if (opts.help) { console.log(HELP); return; }

  let config;
  try {
    config = resolveConfig(opts);
  } catch (e) {
    console.error('✗', e.message);
    process.exit(1);
  }

  const p = config.project;
  log(`project=${p.dir}`);
  log(`module=${p.moduleName} page=${p.entryPage} pkg=${p.pkgName} ability=${p.abilityName} mode=${config.abilityMode ? 'ability' : 'page'}`);
  log(`devices=${config.devices.map((d) => `${d.id}(${d.resolution.join('x')}@${d.density}dpi,:${d.lwsPort})`).join(', ')}`);

  // Headless Linux has no display for the Previewer's GL context; start a virtual one (Xvfb) and
  // feed its $DISPLAY to every engine launch. No-op on macOS / desktop Linux.
  let display = { display: null, stop() {} };
  try {
    display = await ensureDisplay(log);
  } catch (e) {
    console.error('✗', e.message);
    process.exit(1);
  }

  // One -f settings file per configured size, generated from that size's own geometry (vp
  // resolution + dpi-scaled safe area), in this port's own temp dir — removed on shutdown, and
  // known to cleanup.mjs by port in case we're killed before that runs. A caller-supplied
  // --device-config passes straight through instead.
  const deviceConfigs = materializeDeviceConfigs(config.devices, { dir: deviceConfigDir(config.ports.http) });
  const deviceSessions = config.devices.map((d) => ({ ...d, deviceConfig: deviceConfigs.paths.get(d.id) }));

  const status = createStatus();

  // deviceId -> engine handle. One Previewer process per configured device (see config.mjs
  // devices[]) — every rebuild restarts all of them, since each engine only reads its compiled
  // artifacts at launch (see references/how-it-works.md § 权衡).
  let engines = new Map();
  let building = false;
  let pending = false;
  let releasing = false;

  const stopAllEngines = () => { for (const eng of engines.values()) stopEngine(eng); engines = new Map(); };

  // Single teardown path, reused by SIGINT/SIGTERM and the bridge's auto-release. Idempotent so the
  // browser-close release and a racing signal can't double-kill.
  let deregister = () => {};
  const shutdown = (reason) => {
    if (releasing) return;
    releasing = true;
    if (reason) log(reason);
    deregister();
    stopAllEngines();
    display.stop();
    deviceConfigs.cleanup();
    bridge.close();
    process.exit(0);
  };

  const bridge = createBridge(config, status, {
    onIdle: () => shutdown('viewer closed — releasing preview'),
  });

  async function compile() {
    log('building (hvigorw PreviewBuild)…');
    // startedAt rides along through every state so /status clients can order this build against
    // the last watched change (drive.mjs `wait --for-rebuild` relies on that ordering).
    const startedAt = Date.now();
    status.set({ state: 'building', startedAt });
    const { ok, output } = await build(config, log);
    if (ok) {
      stopAllEngines();
      for (const d of deviceSessions) {
        const engine = launchEngine(d, { lws: d.lwsPort, display: display.display }, log);
        engines.set(d.id, engine);
        bridge.setEngine(d.id, {
          port: engine.port, sid: engine.sid, device: engine.device,
          send: engine.send, getInspectorTree: engine.getInspectorTree,
          getLastEngineError: engine.getLastEngineError,
        });
      }
      status.set({ state: 'ok', startedAt });
    } else {
      status.set({ state: 'error', error: extractError(output), startedAt });
      log('build failed — preview kept at last good state');
    }
  }

  async function rebuild() {
    if (building) { pending = true; return; }
    building = true;
    await compile();
    building = false;
    if (pending) { pending = false; rebuild(); }
  }

  let debounce = null;
  function startWatch() {
    for (const dir of p.watchDirs) {
      if (!fs.existsSync(dir)) { log(`watch dir missing: ${dir}`); continue; }
      fs.watch(dir, { recursive: true }, (_evt, file) => {
        if (!file || !file.endsWith('.ets')) return;
        status.markChange();
        clearTimeout(debounce);
        debounce = setTimeout(() => { log(`changed: ${file}`); rebuild(); }, 200);
      });
      log(`watching ${dir}`);
    }
  }

  process.on('SIGINT', () => shutdown());
  process.on('SIGTERM', () => shutdown());

  bridge.listen(config.ports.http, async () => {
    // Record this orchestrator so the SessionEnd hook (cleanup.mjs) can terminate it precisely.
    deregister = register({ port: config.ports.http, project: p.dir, autoRelease: config.autoRelease });
    log(`viewer: http://127.0.0.1:${config.ports.http}`);
    if (config.autoRelease) log('auto-release on: preview frees itself when the browser tab closes (use --keep-alive to disable)');
    await rebuild();
    if (config.watch) startWatch();
    else log('one-shot mode (--no-watch): static current-UI view');
  });
}

main();
