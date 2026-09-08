// In-memory build-status channel shared between the orchestrator (writer) and the bridge
// (reader), so compile errors surface in the browser instead of only the terminal. Single
// process, so no temp file is needed.

export function createStatus() {
  let current = { state: 'idle', ts: Date.now() };
  // Timestamp of the newest watched-file change, independent of the build state machine. Together
  // with the build's startedAt this lets a client decide "has the latest edit been built yet?"
  // without guessing from wall-clock windows (see drive.mjs `wait --for-rebuild`).
  let lastChangeAt = null;
  return {
    get: () => current,
    set: (obj) => { current = { ...obj, ts: Date.now() }; },
    markChange: () => { lastChangeAt = Date.now(); },
    lastChangeAt: () => lastChangeAt,
  };
}

// Strip ANSI color codes and pull out the ArkTS error lines for display.
export function extractError(output = '') {
  const clean = output.replace(/\x1b\[[0-9;]*m/g, '');
  const lines = clean.split('\n').map((l) => l.trim()).filter(Boolean);
  const picked = lines.filter((l) => /ArkTS Compiler Error|Error Message:|At File:|ERROR:/.test(l));
  return (picked.length ? picked : lines.slice(-6)).join('\n').slice(0, 1200);
}
