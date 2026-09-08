// Serializes `hvigorw PreviewBuild` runs against the same project+product.
//
// hvigor's preview build tree (.preview/<product>/intermediates/…) is shared by every process
// building that project — it is not per-invocation. Two orchestrators previewing the same project
// on different ports will happily run two hvigorw processes over the same intermediates, and one
// reads a file the other is halfway through writing: measured 3 failures in 4 concurrent launches,
// all `JSON5: invalid end of input` on
// `components/*/.preview/default/intermediates/merge_profile/default/module.json`. Different --port
// / --lws values do not help; the collision is in the build tree, not the runtime.
//
// A cross-process lock is enough because a preview build takes seconds: the second orchestrator
// waits, then builds against a settled tree. `mkdir` is the lock primitive — atomic on every
// platform, and its leftovers are self-diagnosing (the holder file inside says which pid claimed it).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';

const LOCK_ROOT = path.join(os.tmpdir(), 'harmonyos-live-preview', 'build-locks');
const POLL_MS = 150;
// A cold build of a large multi-module project runs ~30s; 3 minutes is "the holder is wedged",
// not "the holder is slow". Past it we take the lock anyway — a stuck peer must not block previews
// forever, and a corrupted build is still better than a dead skill.
const WAIT_TIMEOUT_MS = 180_000;
// Independent of the wait: a holder file older than this is treated as abandoned even if some
// unrelated process now owns that pid.
const STALE_HOLDER_MS = 10 * 60_000;
// mkdir and the holder-file write cannot be one atomic step, so a just-acquired lock is briefly
// holderless. Waiters must not mistake that window for an abandoned lock and delete it — that is
// exactly how several builders end up "holding" the lock at once. Writing a small JSON takes
// microseconds; anything holderless for longer than this really is debris.
const HOLDERLESS_GRACE_MS = 2_000;

const isAlive = (pid) => {
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
};

function lockDir(key) {
  const hash = crypto.createHash('sha1').update(key).digest('hex').slice(0, 16);
  return path.join(LOCK_ROOT, hash);
}

function readHolder(dir) {
  try { return JSON.parse(fs.readFileSync(path.join(dir, 'holder.json'), 'utf8')); } catch { return null; }
}

function release(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* best effort */ }
}

// mkdir is the atomic test-and-set: it either creates the directory (we hold the lock) or throws
// EEXIST (someone else does).
function tryAcquire(dir) {
  fs.mkdirSync(LOCK_ROOT, { recursive: true });
  try {
    fs.mkdirSync(dir);
  } catch (e) {
    if (e.code === 'EEXIST') return false;
    throw e;
  }
  fs.writeFileSync(path.join(dir, 'holder.json'), JSON.stringify({ pid: process.pid, at: Date.now() }));
  return true;
}

// A lock whose holder died (SIGKILLed orchestrator) or went stale is reclaimed rather than waited on.
function reclaimIfAbandoned(dir, log) {
  const holder = readHolder(dir);
  if (!holder) {
    // Either the holder is mid-acquire (see HOLDERLESS_GRACE_MS) or it died between mkdir and the
    // holder write. Only the latter is ours to clean up.
    let age = 0;
    try { age = Date.now() - fs.statSync(dir).mtimeMs; } catch { return; } // already gone
    if (age > HOLDERLESS_GRACE_MS) {
      log('build lock: clearing lock with no holder record');
      release(dir);
    }
    return;
  }
  const dead = !holder.pid || !isAlive(holder.pid);
  const stale = Date.now() - (holder.at ?? 0) > STALE_HOLDER_MS;
  if (dead || stale) {
    log(`build lock: reclaiming ${dead ? 'dead' : 'stale'} lock from pid ${holder.pid}`);
    release(dir);
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Run `fn` while holding the build lock for `key`. Always releases, including when `fn` throws.
export async function withBuildLock(key, fn, { log = () => {} } = {}) {
  const dir = lockDir(key);
  const startedAt = Date.now();
  let waited = false;

  while (!tryAcquire(dir)) {
    reclaimIfAbandoned(dir, log);
    if (Date.now() - startedAt > WAIT_TIMEOUT_MS) {
      log('build lock: waited too long, taking it anyway (concurrent builds may corrupt artifacts)');
      release(dir);
      tryAcquire(dir);
      break;
    }
    if (!waited) {
      waited = true;
      const holder = readHolder(dir);
      log(`build lock: another preview is building this project${holder?.pid ? ` (pid ${holder.pid})` : ''} — waiting`);
    }
    await sleep(POLL_MS);
  }

  try {
    return await fn();
  } finally {
    release(dir);
  }
}
