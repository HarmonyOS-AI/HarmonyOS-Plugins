// On-disk registry of running preview orchestrators. Each live `preview.mjs` writes one JSON file
// here on startup and removes it on clean shutdown; `cleanup.mjs` (the SessionEnd hook) reads them
// to terminate leftovers precisely — by recorded PID, not a fragile `pkill -f` pattern that could
// hit unrelated processes.
//
// The file is keyed by the HTTP port (one orchestrator per port), so a relaunch on the same port
// overwrites cleanly and stale files are self-identifying.
//
// A record is a *claim* on a port, not proof that anything is serving there — see probe() for the
// authoritative check. Callers that signal processes (cleanup.mjs) want the PID; callers that send
// requests (drive.mjs) want the probe.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const REGISTRY_DIR = path.join(os.tmpdir(), 'harmonyos-live-preview', 'sessions');

// Identifies our own HTTP server in a /status response, so probing a port can tell "our preview" from
// "some unrelated service that happens to hold 8088".
export const SERVICE_ID = 'harmonyos-live-preview';

// Where one orchestrator's generated `-f` device config files live (device-profile.mjs writes them).
// Keyed by port like the registry entry itself, so cleanup.mjs can remove a killed orchestrator's
// files without the record having to carry a path — and a relaunch on the same port reuses the dir.
export const deviceConfigDir = (port) =>
  path.join(os.tmpdir(), 'harmonyos-live-preview', 'device-configs', String(port));

function entryPath(port) {
  return path.join(REGISTRY_DIR, `${port}.json`);
}

// Who owns a preview — used by cleanup.mjs to sweep only its own, since REGISTRY_DIR is a single
// directory shared by every agent session on the machine. Without an owner, one session ending took
// down previews other sessions were still using.
//
// Host-agnostic by design: any host (or a plain shell script) can claim ownership by exporting
// HARMONY_PREVIEW_OWNER. CLAUDE_CODE_SESSION_ID is only a convenience fallback for the one host
// that's verified to export a session id into tool subprocesses — nothing here depends on it, and a
// host that sets neither simply gets the old "clean up everything" behaviour.
const OWNER_ENV_KEYS = ['HARMONY_PREVIEW_OWNER', 'CLAUDE_CODE_SESSION_ID'];

export function ownerId() {
  for (const key of OWNER_ENV_KEYS) {
    const value = process.env[key];
    if (value) return value;
  }
  return null;
}

// Record this orchestrator. Returns a deregister() that removes the file (idempotent).
export function register(info) {
  fs.mkdirSync(REGISTRY_DIR, { recursive: true });
  const file = entryPath(info.port);
  const record = { pid: process.pid, startedAt: Date.now(), owner: ownerId(), ...info };
  // Write to a sibling temp file, then rename: a same-directory rename is atomic, so a concurrent
  // reader sees either the old record or the new one, never a half-written file — and a crash
  // mid-write leaves the previous record intact instead of corrupting it. The temp name carries the
  // PID so two orchestrators racing on one port can't clobber each other's staging file, and it ends
  // in `.tmp` so listSessions() (which only reads `.json`) skips it.
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(record));
  fs.renameSync(tmp, file);
  return () => { try { fs.unlinkSync(file); } catch {} };
}

// Read every registered session. Skips unreadable/corrupt files instead of throwing so one bad
// entry can't block cleanup of the rest.
export function listSessions() {
  let names;
  try { names = fs.readdirSync(REGISTRY_DIR); } catch { return []; }
  const out = [];
  for (const name of names) {
    if (!name.endsWith('.json')) continue;
    const file = path.join(REGISTRY_DIR, name);
    try {
      out.push({ file, ...JSON.parse(fs.readFileSync(file, 'utf8')) });
    } catch {
      out.push({ file, corrupt: true });
    }
  }
  return out;
}

export function removeSession(file) {
  try { fs.unlinkSync(file); } catch {}
}

// Is a preview actually serving on this port right now? Asks the port itself rather than trusting a
// record or a PID: a stale file, a PID the OS has since recycled, and a wedged orchestrator all fail
// here, while an unrelated service holding the port is rejected by the service marker. A refused
// connection returns immediately, so probing dead ports costs nothing — the timeout only bounds a
// port that accepts but never answers.
export async function probe(port, timeoutMs = 1500) {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/status`, { signal: AbortSignal.timeout(timeoutMs) });
    if (!res.ok) return false;
    const body = await res.json();
    // `build` is a field only our /status emits; accepting it keeps previews that were started
    // before the marker existed drivable instead of stranding them until the next relaunch.
    return body?.service === SERVICE_ID || (body != null && 'build' in body);
  } catch { return false; }
}

// Every registered session paired with a live probe of its port, as `live: boolean`. Corrupt and
// port-less records are dropped — nothing can be driven or probed through them.
export async function probeSessions() {
  const sessions = listSessions().filter((s) => !s.corrupt && s.port != null);
  const results = await Promise.all(sessions.map((s) => probe(s.port)));
  return sessions.map((s, i) => ({ ...s, live: results[i] }));
}
