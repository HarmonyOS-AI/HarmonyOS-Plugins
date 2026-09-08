// Launches the HarmonyOS ArkUI Previewer engine standalone (no DevEco). It plays the role
// DevEco's node preview-server plays: create the Unix-domain command/image/trace sockets the
// engine connects to as a client, then spawn the SDK Previewer pointed at the regular build
// artifacts. The engine auto-renders the entry page and streams JPEG frames over its -lws
// WebSocket (consumed by the bridge).
import net from 'node:net';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { buildPaths, abilityOhmurl } from './config.mjs';

function freshIds() {
  const rnd = Number(process.hrtime.bigint() % 100000n).toString();
  return {
    base: `hpv_${rnd}_1`,
    trace: `hpvt_${rnd}`,
    sid: (rnd + 'a').padEnd(32, '0123456789abcdef'.repeat(2)).slice(0, 32),
  };
}

export function launchEngine(config, { lws, page, display } = {}, log = console.log) {
  const p = config.project;
  const targetPage = page || p.entryPage;
  const { base, trace, sid } = freshIds();
  const sockPaths = [`/tmp/${base}_commandPipe`, `/tmp/${base}_imagePipe`, `/tmp/${trace}`];
  // The engine connects to these as a client. The command pipe (index 0) is bidirectional: the
  // engine streams status back (inspector tree, avoid-area, command acks) which we parse below, and
  // we write input commands to it (tap/swipe/key) — exactly how DevEco's preview-server drives input.
  let cmdSocket = null;
  // Inbound framing mirrors outbound: JSON + a single NUL terminator, and the engine may coalesce
  // several messages into one write, so buffer until a trailing NUL and split on it. There's no
  // correlation ID on either side of this protocol, so only one "inspector" request is allowed in
  // flight at a time — good enough since callers (the /inspector bridge route) never overlap.
  //
  // The pipe isn't purely request/response: the engine also pushes unsolicited messages on its own
  // (route changes, ACE runtime errors) using a different envelope — {MessageType, args} instead of
  // {command, result} — confirmed from the previewer's own source (ide_previewer
  // mock/rich/VirtualScreenImpl.cpp's PageCallback/LoadContentCallback/FastPreviewCallback, each of
  // which calls CommandLineInterface::CreatCommandToSendData on its own, not in reply to a request).
  // The one worth surfacing here is FastPreviewCallback, wired to ACE's onError callback
  // (JsAppImpl::SetOnError) — it's the engine's own runtime-error channel, arriving as
  // {"MessageType":"MemoryRefresh","args":{"FastPreviewMsg":"<message>"}} (the MessageType name is the
  // previewer's own, not chosen by us). It complements PREVIEW_ENGINE_LOG=1 stdout scraping with a
  // structured signal for "build succeeded but the page errored/blanked at runtime".
  let recvBuf = '';
  let pendingInspector = null; // { resolve, timer } while a request is in flight
  let lastEngineError = null;

  function handleInboundMessage(msg) {
    if (!msg) return;
    if (msg.command === 'inspector' && pendingInspector) {
      const { resolve, timer } = pendingInspector;
      clearTimeout(timer);
      pendingInspector = null;
      try { resolve(JSON.parse(msg.result)); } catch { resolve(null); }
      return;
    }
    if (msg.MessageType === 'MemoryRefresh' && typeof msg.args?.FastPreviewMsg === 'string') {
      lastEngineError = msg.args.FastPreviewMsg || null;
    }
  }

  const servers = sockPaths.map((sp, idx) => {
    try { fs.unlinkSync(sp); } catch {}
    const s = net.createServer((c) => {
      if (idx === 0) {
        cmdSocket = c;
        c.on('data', (chunk) => {
          recvBuf += chunk.toString('utf8');
          if (recvBuf.charCodeAt(recvBuf.length - 1) !== 0) return; // message not complete yet
          const parts = recvBuf.split('\0').filter(Boolean);
          recvBuf = '';
          for (const part of parts) {
            try { handleInboundMessage(JSON.parse(part)); } catch { /* not JSON we care about */ }
          }
        });
        c.on('close', () => { if (cmdSocket === c) cmdSocket = null; });
      } else {
        c.on('data', () => {});
      }
      c.on('error', () => {});
    });
    s.listen(sp);
    return s;
  });

  const b = buildPaths(config);
  const [resW, resH] = config.resolution.map(String);
  // Page-preview mode (default) renders the @Entry route named by -url directly — exactly DevEco's
  // per-page preview. No UIAbility is launched, so any @Entry in the pages profile shows without
  // recompiling or touching the ability's loadContent. Ability mode instead adds -d/-abn/-abp so the
  // engine runs the real UIAbility (its onCreate/onWindowStageCreate lifecycle) and shows whatever it
  // loadContents; -d (debug) makes -abp mandatory, which is why the two travel together.
  // -cpm true is the engine half of DevEco's @Preview component preview (flips the compiled
  // getPreviewComponentFlag() gate). Callers opt in via config.componentMode; plain page/ability
  // preview keeps it false. Findings on the full component-preview flow: how-it-works.md
  // § 组件预览调查.
  const args = [
    '-refresh', 'region', '-projectID', '700700900', '-ts', trace,
    '-j', b.jsApp, '-s', base, '-cpm', config.componentMode ? 'true' : 'false',
    '-device', config.device, '-shape', 'rect', '-sd', String(config.density),
    '-ljPath', b.loaderJson, '-sid', sid,
    '-or', resW, resH, '-cr', resW, resH, '-f', config.deviceConfig,
    '-url', targetPage, '-av', 'ACE_2_0', '-n', p.pkgName, '-arp', b.appResource,
    '-pm', 'Stage', '-pages', p.pagesProfile,
    '-hsp', config.toolchain.hsp, '-l', 'zh_CN', '-cm', 'light', '-o', config.orientation, '-ilt', 'true',
    '-lws', String(lws),
  ];
  if (config.abilityMode) {
    args.push('-d', '-abn', p.abilityName, '-abp', abilityOhmurl(config));
  }
  // On headless Linux the orchestrator hands us a virtual $DISPLAY (Xvfb) the GLFW context binds to;
  // elsewhere display is null and the engine inherits the parent environment unchanged.
  const env = display ? { ...process.env, DISPLAY: display } : process.env;
  // The engine's stdout carries the ArkTS console + engine diagnostics — normally dropped, but
  // PREVIEW_ENGINE_LOG=1 surfaces it (interleaved with orchestrator logs) to diagnose blank frames.
  const child = spawn(config.toolchain.previewerBin, args, {
    cwd: path.dirname(config.toolchain.previewerBin),
    stdio: process.env.PREVIEW_ENGINE_LOG ? 'inherit' : 'ignore',
    env,
  });
  log(`engine up (pid=${child.pid}, lws=${lws}, sid=${sid.slice(0, 8)}…, page=${targetPage}, mode=${config.abilityMode ? 'ability' : 'page'})`);

  // Frame the command exactly as DevEco does: JSON + a single NUL terminator. Returns false when
  // the engine has not yet connected its command pipe (e.g. just after relaunch) so callers can
  // drop the event instead of throwing.
  const send = (cmd) => {
    if (!cmdSocket || cmdSocket.destroyed) return false;
    try { cmdSocket.write(JSON.stringify(cmd) + '\0'); return true; } catch { return false; }
  };

  // Requests the ArkUI inspector's JSON component tree — the same "inspector" command DevEco's
  // preview-server sends, over the same command pipe `send()` already writes to. The engine pushes
  // the response back asynchronously (no request id), so this just waits for the next "inspector"
  // message to land; getInspectorTree only returns a populated tree when the engine is running
  // against a PreviewBuild-produced bundle (see config.mjs) — against a plain assembleHap bundle it
  // resolves to a bare `{ $type: "root", ... }` with no children.
  const getInspectorTree = (timeoutMs = 4000) => new Promise((resolve) => {
    if (pendingInspector) { resolve(null); return; } // one in flight at a time
    if (!send({ version: '1.0.1', command: 'inspector', type: 'action' })) { resolve(null); return; }
    const timer = setTimeout(() => { pendingInspector = null; resolve(null); }, timeoutMs);
    pendingInspector = { resolve, timer };
  });

  return {
    child, servers, sockPaths, sid, port: lws, device: config.device, send, getInspectorTree,
    getLastEngineError: () => lastEngineError,
  };
}

export function stopEngine(engine) {
  if (!engine) return;
  try { engine.child.kill('SIGKILL'); } catch {}
  for (const s of engine.servers) { try { s.close(); } catch {} }
  for (const sp of engine.sockPaths) { try { fs.unlinkSync(sp); } catch {} }
}
