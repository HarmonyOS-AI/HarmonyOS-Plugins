#!/usr/bin/env node
// Terminate preview orchestrators still running at the end of an agent session, so no Previewer
// engine or file-watch leaks past it. Driven by the on-disk registry (registry.mjs) rather than a
// broad `pkill -f`, so only this skill's own processes are touched.
//
// Each live preview.mjs records its PID + port; here we SIGTERM it (its own handler stops the engine
// and unlinks sockets), wait briefly, then SIGKILL any holdout. A `ps` command-line check guards
// against PID reuse — we only signal a PID that still looks like our orchestrator.
//
// Usage — host-agnostic, no arguments needed in the common case:
//   node cleanup.mjs                  sweep previews owned by this session (see registry.ownerId);
//                                     with no owner resolvable, sweeps everything
//   node cleanup.mjs --session <id>   sweep a specific owner's previews
//   node cleanup.mjs --all            sweep every registered preview, ignoring ownership
//
// Claude Code wires this to its SessionEnd hook (hooks/hooks.json) and pipes `{session_id, …}` in on
// stdin, which is read as the owner automatically. Hosts without a session-end hook (Codex,
// OpenCode, plain shells) can call it directly — previews also release themselves when the browser
// tab closes or on Ctrl-C, so this is a backstop, not a requirement.
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { listSessions, removeSession, deviceConfigDir, ownerId } from './lib/registry.mjs';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Drop the registry entry plus the generated `-f` device config files that orchestrator owned —
// a SIGKILLed preview never gets to run its own cleanup, so this is the backstop.
function forget(session) {
  removeSession(session.file);
  if (session.port == null) return;
  try { fs.rmSync(deviceConfigDir(session.port), { recursive: true, force: true }); } catch { /* best effort */ }
}

function isAlive(pid) {
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}

// Confirm the PID is really our orchestrator before signalling it (PID reuse safety). Returns true
// if we can't run ps at all, so cleanup still works where ps is unavailable.
function looksLikeOurs(pid) {
  try {
    const cmd = execFileSync('ps', ['-p', String(pid), '-o', 'command='], { encoding: 'utf8' });
    return cmd.includes('preview.mjs');
  } catch { return false; }
}

function parseArgv(argv) {
  const opts = { all: false, session: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--all') opts.all = true;
    else if (argv[i] === '--session') opts.session = argv[++i] ?? null;
  }
  return opts;
}

// Whose previews to sweep. Explicit --session wins; then a hook payload on stdin (Claude Code's
// SessionEnd pipes `{session_id, …}` in); then the ambient owner env (registry.ownerId). null means
// "no owner resolvable" — every entry is then treated as ours, preserving the original backstop
// behaviour on hosts that identify sessions in none of these ways.
async function resolveOwner(opts) {
  if (opts.session) return opts.session;
  const ambient = ownerId();
  if (process.stdin.isTTY) return ambient;
  const raw = await new Promise((resolve) => {
    let buf = '';
    // Never block shutdown on a stdin nobody writes to (a host that runs this without a payload).
    const done = setTimeout(() => resolve(buf), 300);
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (c) => { buf += c; });
    process.stdin.on('end', () => { clearTimeout(done); resolve(buf); });
    process.stdin.on('error', () => { clearTimeout(done); resolve(''); });
  });
  try { return JSON.parse(raw).session_id || ambient; } catch { return ambient; }
}

async function main() {
  const opts = parseArgv(process.argv.slice(2));
  const sessions = listSessions();
  if (!sessions.length) return;

  // An entry with no recorded owner still gets swept: it predates this field or was launched by a
  // host that sets none of the owner variables, and dropping the backstop entirely would be worse
  // than the cross-session kill this guard exists to prevent.
  const mine = opts.all ? null : await resolveOwner(opts);
  const targets = [];
  for (const s of sessions) {
    if (s.corrupt || !s.pid || !isAlive(s.pid)) { forget(s); continue; }
    if (mine && s.owner && s.owner !== mine) continue; // another session's preview — leave it running
    if (!looksLikeOurs(s.pid)) { forget(s); continue; } // stale file, PID reused
    try { process.kill(s.pid, 'SIGTERM'); targets.push(s); } catch { forget(s); }
  }
  if (!targets.length) return;

  await sleep(1500); // let each orchestrator's SIGTERM handler stop its engine + unlink sockets
  for (const s of targets) {
    if (isAlive(s.pid)) { try { process.kill(s.pid, 'SIGKILL'); } catch {} }
    forget(s);
  }
  console.log(`[harmonyos-live-preview] released ${targets.length} preview session(s)`);
}

main().catch(() => process.exit(0));
