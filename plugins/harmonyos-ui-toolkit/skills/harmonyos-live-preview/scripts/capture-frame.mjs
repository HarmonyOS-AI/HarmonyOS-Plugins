#!/usr/bin/env node
// Debug helper: grab one JPEG frame straight from a running Previewer engine, no browser needed.
// Useful for headless verification that a frame is rendering. Auto-discovers the engine's -lws
// port and -sid from `ps` (override with argv).
//   node capture-frame.mjs [out.jpg] [port] [sid]
//
// Positional args only — there is no --out/--help. For everyday screenshots use
// `drive.mjs shot <out.jpg>` instead: it goes through the orchestrator, so it targets the preview
// you actually mean. This script's `ps` sniffing picks the *first* engine it finds, which is the
// wrong one as soon as more than one preview is running.
import { writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

let [out = '/tmp/harmony-frame.jpg', port, sid] = process.argv.slice(2);
if (!port || !sid) {
  const line = execSync('ps -A -ww -o args=').toString().split('\n')
    .find((l) => l.includes('common/bin/Previewer') && l.includes('-lws'));
  if (!line) { console.error('no running Previewer engine found'); process.exit(1); }
  port ||= line.match(/-lws\s+(\d+)/)?.[1];
  sid ||= line.match(/-sid\s+([a-f0-9]+)/)?.[1];
}

const ws = new WebSocket(`ws://127.0.0.1:${port}/${sid}`);
ws.binaryType = 'arraybuffer';
const timer = setTimeout(() => { console.error('timeout (no frame — trigger a redraw)'); process.exit(1); }, 8000);
ws.onerror = (e) => { console.error('ws error:', e.message || 'error'); process.exit(1); };
ws.onmessage = (ev) => {
  const b = Buffer.from(ev.data);
  const s = b.indexOf(Buffer.from([0xff, 0xd8, 0xff]));
  const e = b.indexOf(Buffer.from([0xff, 0xd9]), s + 3);
  if (s >= 0 && e > s) {
    writeFileSync(out, b.subarray(s, e + 2));
    clearTimeout(timer);
    console.log(`saved ${out} (${e - s + 2} bytes) from :${port}`);
    process.exit(0);
  }
};
