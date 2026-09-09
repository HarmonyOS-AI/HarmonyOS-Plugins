// Headless-Linux rendering support. The standalone Previewer renders through a bundled GLFW that,
// by default, needs an X11 (or Wayland) display to create its GL context — there is no offscreen
// path we can select from outside the binary. On a desktop Linux that display already exists; on a
// headless server / container / cloud VM (ECS) there is none, so we start a virtual X server (Xvfb)
// and point the engine at it via $DISPLAY. Pure software: Xvfb + Mesa llvmpipe, no GPU needed.
//
// No-op on macOS, and on any Linux that already exposes a display ($DISPLAY / $WAYLAND_DISPLAY) — so
// the macOS dev path and the desktop-Linux path are left completely untouched.
import fs from 'node:fs';
import { spawn } from 'node:child_process';

const NOOP = { display: null, stop() {} };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Lowest X display number with neither a lock file nor a listening socket, so two previews (or an
// unrelated X server) never collide on the same number.
function freeDisplayNum(start = 99, end = 1099) {
  for (let n = start; n <= end; n++) {
    if (!fs.existsSync(`/tmp/.X${n}-lock`) && !fs.existsSync(`/tmp/.X11-unix/X${n}`)) return n;
  }
  return null;
}

const XVFB_HINT =
  'Install the headless render stack once (Debian/Ubuntu: `apt-get install -y xvfb libgl1 ' +
  'libglu1-mesa libgl1-mesa-dri fonts-noto-cjk`; Fedora/CentOS: `dnf install -y ' +
  'xorg-x11-server-Xvfb mesa-libGL mesa-dri-drivers google-noto-sans-cjk-fonts`), or run the ' +
  'command inside `xvfb-run -a`.';

// Ensure a usable X display, starting Xvfb if we are headless. Returns { display, stop } — stop() is
// a no-op when we reused an existing display, so we never tear down a display we did not create.
export async function ensureDisplay(log = console.log) {
  if (process.platform !== 'linux') return NOOP;
  if (process.env.DISPLAY || process.env.WAYLAND_DISPLAY) {
    return { display: process.env.DISPLAY || null, stop() {} };
  }

  const n = freeDisplayNum();
  if (n == null) throw new Error('headless: no free X display number for Xvfb');
  const display = `:${n}`;
  // One generous screen covers both phone (1080x2340) and tablet (2048x1280) windows; 24-bit depth
  // gives GLX/llvmpipe a visual to match. -ac drops host access control (local-only anyway).
  const xvfb = spawn('Xvfb', [display, '-screen', '0', '2560x2560x24', '-nolisten', 'tcp', '-ac'], { stdio: 'ignore' });
  let spawnErr = null;
  xvfb.on('error', (e) => { spawnErr = e; });

  // Ready once the server's Unix socket appears; bail out early on a spawn failure or a timeout.
  const sock = `/tmp/.X11-unix/X${n}`;
  for (let waited = 0; waited < 8000 && !spawnErr && !fs.existsSync(sock); waited += 100) await sleep(100);

  if (spawnErr) {
    if (spawnErr.code === 'ENOENT') throw new Error(`headless: Xvfb not found. ${XVFB_HINT}`);
    throw new Error(`headless: failed to start Xvfb: ${spawnErr.message}`);
  }
  if (!fs.existsSync(sock)) {
    try { xvfb.kill('SIGKILL'); } catch {}
    throw new Error(`headless: Xvfb did not become ready on ${display} within 8s. ${XVFB_HINT}`);
  }

  log(`headless: started virtual display ${display} via Xvfb (pid=${xvfb.pid})`);
  let stopped = false;
  return {
    display,
    stop() {
      if (stopped) return;
      stopped = true;
      try { xvfb.kill('SIGTERM'); } catch {}
      try { fs.unlinkSync(`/tmp/.X${n}-lock`); } catch {}
    },
  };
}
