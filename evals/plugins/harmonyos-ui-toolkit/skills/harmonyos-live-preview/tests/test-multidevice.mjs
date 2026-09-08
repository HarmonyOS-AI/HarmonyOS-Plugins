#!/usr/bin/env node
// Multi-device smoke test for drive.mjs's --device/--all support against mock-bridge.mjs
// (registers "phone" 1080x2340 + "tablet" 2048x1280 by default).
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import { createEvalTempDir, DRIVE, MOCK } from './paths.mjs';

const execFileP = promisify(execFile);
const PORT = 18900;
const base = `http://127.0.0.1:${PORT}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const temporary = createEvalTempDir('multidevice');
const framePath = path.join(temporary.path, 'frame.jpg');
const frameBase = framePath.replace(/\.jpe?g$/i, '');

let passed = 0, failed = 0;
const check = (name, cond, detail = '') => {
  if (cond) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.log(`  ✗ ${name}  ${detail}`); }
};

async function drive(...args) {
  try {
    const { stdout, stderr } = await execFileP('node', [DRIVE, ...args, '--port', String(PORT)], { timeout: 30000 });
    return { code: 0, stdout, stderr };
  } catch (e) {
    return { code: e.code ?? 1, stdout: e.stdout ?? '', stderr: e.stderr ?? '' };
  }
}
const getInputs = async (id) => (await fetch(`${base}/debug/inputs?device=${id}`)).json();
const clearInputs = () => fetch(`${base}/debug/clear`);
const setDevice = (id, patch) => fetch(`${base}/debug/setDevice`, { method: 'POST', body: JSON.stringify({ id, ...patch }) });

const mock = spawn('node', [MOCK, String(PORT)], { stdio: 'inherit' });
await sleep(400);

try {
  console.log('devices:');
  let r = await drive('devices');
  check('lists both devices', r.stdout.includes('phone') && r.stdout.includes('tablet'), r.stdout);
  check('shows resolutions', r.stdout.includes('1080x2340') && r.stdout.includes('2048x1280'), r.stdout);
  check('shows online state', r.stdout.includes('online'), r.stdout);

  console.log('unknown --device fails fast:');
  r = await drive('tap', '0.5,0.5', '--device', 'watch');
  check('exits 1 naming known devices', r.code === 1 && r.stderr.includes('unknown --device') && r.stderr.includes('phone') && r.stderr.includes('tablet'), r.stderr);

  console.log('--device targets only that device:');
  await clearInputs();
  r = await drive('tap', '0.5,0.5', '--device', 'tablet');
  check('exits 0', r.code === 0, r.stderr);
  const tabletInputs = await getInputs('tablet');
  const phoneInputs = await getInputs('phone');
  check('tablet got the tap', tabletInputs.length === 2, JSON.stringify(tabletInputs));
  check('phone got nothing', phoneInputs.length === 0, JSON.stringify(phoneInputs));
  // tablet is 2048x1280 — center should be 1024,640, not phone's 540,1170
  check('coords scaled to tablet resolution', tabletInputs[0]?.args.x === 1024 && tabletInputs[0]?.args.y === 640, JSON.stringify(tabletInputs[0]?.args));

  console.log('default device unaffected (no --device):');
  await clearInputs();
  r = await drive('tap', '0.5,0.5');
  check('exits 0', r.code === 0, r.stderr);
  check('goes to phone (default)', (await getInputs('phone')).length === 2 && (await getInputs('tablet')).length === 0);

  console.log('shot --all:');
  r = await drive('shot', framePath, '--all');
  check('exits 0', r.code === 0, r.stderr);
  check('wrote phone file', fs.existsSync(`${frameBase}-phone.jpg`) && fs.readFileSync(`${frameBase}-phone.jpg`)[0] === 0xff);
  check('wrote tablet file', fs.existsSync(`${frameBase}-tablet.jpg`) && fs.readFileSync(`${frameBase}-tablet.jpg`)[0] === 0xff);

  console.log('wait --device targets that device\'s engine state:');
  await setDevice('tablet', { engineConnected: false, hasFrame: false });
  r = await drive('wait', '--timeout', '2', '--device', 'tablet');
  check('times out on tablet specifically', r.code === 2 && r.stderr.includes('engineConnected=false'), r.stderr);
  r = await drive('wait', '--timeout', '2'); // default device (phone) still healthy
  check('default device unaffected', r.code === 0, r.stderr);
  await setDevice('tablet', { engineConnected: true, hasFrame: true });

  console.log('engineError surfaces in status:');
  await setDevice('tablet', { engineError: 'ReferenceError: foo is not defined' });
  r = await drive('devices');
  check('shows engine error on the right device line', /tablet.*ReferenceError/.test(r.stdout), r.stdout);
  await setDevice('tablet', { engineError: null });
} finally {
  mock.kill();
  temporary.cleanup();
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
