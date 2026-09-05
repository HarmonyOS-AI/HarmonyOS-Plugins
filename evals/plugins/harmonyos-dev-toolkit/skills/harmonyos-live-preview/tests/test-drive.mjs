#!/usr/bin/env node
// End-to-end tests for drive.mjs against the mock bridge.
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import { createEvalTempDir, DRIVE, MOCK } from './paths.mjs';

const execFileP = promisify(execFile);
const PORT = 18899;
const base = `http://127.0.0.1:${PORT}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const temporary = createEvalTempDir('drive');
const framePath = path.join(temporary.path, 'frame.jpg');

let passed = 0, failed = 0;
const check = (name, cond, detail = '') => {
  if (cond) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.log(`  ✗ ${name}  ${detail}`); }
};

// run drive; never throws — returns {code, stdout, stderr}
async function drive(...args) {
  try {
    const { stdout, stderr } = await execFileP('node', [DRIVE, ...args, '--port', String(PORT)], { timeout: 30000 });
    return { code: 0, stdout, stderr };
  } catch (e) {
    return { code: e.code ?? 1, stdout: e.stdout ?? '', stderr: e.stderr ?? '' };
  }
}
const setState = (obj) => fetch(`${base}/debug/set`, { method: 'POST', body: JSON.stringify(obj) });
const getInputs = async () => (await fetch(`${base}/debug/inputs`)).json();
const clearInputs = () => fetch(`${base}/debug/clear`);

const mock = spawn('node', [MOCK, String(PORT)], { stdio: 'inherit' });
await sleep(400);

try {
  console.log('status:');
  let r = await drive('status');
  check('exits 0', r.code === 0);
  check('prints resolution', r.stdout.includes('"resolution"'));

  console.log('wait (healthy):');
  r = await drive('wait', '--timeout', '5');
  check('exits 0 when ok+frame', r.code === 0, r.stderr);

  console.log('wait (build error):');
  await setState({ build: 'error', buildError: 'ArkTS Compiler Error\nAt File: Index.ets:12' });
  r = await drive('wait', '--timeout', '5');
  check('exits 1', r.code === 1);
  check('prints ArkTS error lines', r.stderr.includes('At File: Index.ets:12'));
  await setState({ build: 'ok', buildError: null });

  console.log('wait --for-rebuild (no watched change ever):');
  r = await drive('wait', '--for-rebuild', '--timeout', '15');
  check('exits 3', r.code === 3, `code=${r.code}`);
  check('explains watcher', r.stderr.includes('no rebuild detected'));

  console.log('wait --for-rebuild (edit already built — delayed wait):');
  await setState({ lastChangeAgeMs: 12000, buildStartedAgoMs: 8000, build: 'ok' });
  r = await drive('wait', '--for-rebuild', '--timeout', '10');
  check('accepts settled build newer than change', r.code === 0, r.stderr);

  console.log('wait --for-rebuild (stale build predates change → must wait for cycle):');
  await setState({ lastChangeAgeMs: 500, buildStartedAgoMs: 60000, build: 'ok' });
  const waiting = drive('wait', '--for-rebuild', '--timeout', '20');
  await sleep(700); await setState({ build: 'building', hasFrame: false, engineConnected: false });
  await sleep(1500); await setState({ build: 'ok', buildStartedAgoMs: 100, lastChangeAgeMs: 2700 });
  await sleep(700); await setState({ engineConnected: true, hasFrame: true });
  r = await waiting;
  check('exits 0 after full cycle', r.code === 0, r.stderr);
  await setState({ lastChangeAgeMs: null, buildStartedAgoMs: 6000 });

  console.log('shot:');
  r = await drive('shot', framePath);
  check('exits 0', r.code === 0, r.stderr);
  check('writes jpeg bytes', fs.readFileSync(framePath)[0] === 0xff);

  console.log('tree:');
  r = await drive('tree');
  check('outline has Text node', r.stdout.includes('Text "Hello World"'), r.stdout);
  check('outline has source line', r.stdout.includes('pages/Index.ets(12:9)'));
  check('corner-pair rect parsed as 300x80', r.stdout.includes('300x80'), r.stdout);
  check('indented by depth', /^ {4}Text/m.test(r.stdout));
  r = await drive('tree', '--json');
  check('--json emits raw tree', r.stdout.trim().startsWith('{') && r.stdout.includes('$children'));

  console.log('find:');
  r = await drive('find', 'Hello');
  check('finds by substring', r.code === 0 && r.stdout.includes('#0'));
  r = await drive('find', '--type', 'TextInput');
  check('finds by type', r.stdout.includes('请输入内容'));
  r = await drive('find', '不存在的文案');
  check('no match exits 1', r.code === 1);

  console.log('tap by text:');
  await clearInputs();
  r = await drive('tap', '登录', '--index', '0');
  let inputs = await getInputs();
  check('exits 0', r.code === 0, r.stderr);
  check('press+release', inputs.length === 2 && inputs[0].command === 'MousePress' && inputs[1].command === 'MouseRelease', JSON.stringify(inputs));
  check('at element center px', inputs[0].args.x === 540 && inputs[0].args.y === 1260, JSON.stringify(inputs[0]?.args));

  console.log('tap ambiguity:');
  r = await drive('tap', '登录');
  check('multiple matches exit 1 and list', r.code === 1 && r.stderr.includes('#1'), r.stderr);

  console.log('tap by normalized coords:');
  await clearInputs();
  r = await drive('tap', '0.5,0.5');
  inputs = await getInputs();
  check('center of screen', inputs[0]?.args.x === 540 && inputs[0]?.args.y === 1170, JSON.stringify(inputs[0]?.args));

  console.log('tap by device px coords:');
  await clearInputs();
  r = await drive('tap', '540,1170');
  inputs = await getInputs();
  check('px accepted', inputs[0]?.args.x === 540 && inputs[0]?.args.y === 1170, JSON.stringify(inputs[0]?.args));

  console.log('swipe:');
  await clearInputs();
  r = await drive('swipe', '0.5,0.75', '0.5,0.25', '--steps', '4');
  inputs = await getInputs();
  check('down + 4 moves + up', inputs.length === 6, `${inputs.length}`);
  check('sequence', inputs[0]?.command === 'MousePress' && inputs[2]?.command === 'MouseMove' && inputs[5]?.command === 'MouseRelease');
  check('endpoint', inputs[5]?.args.y === 585, JSON.stringify(inputs[5]?.args));

  console.log('type:');
  await clearInputs();
  r = await drive('type', 'ab 1');
  inputs = await getInputs();
  check('4 chars → 12 KeyPress', inputs.length === 12 && inputs.every((c) => c.command === 'KeyPress'), `${inputs.length}`);
  check('keyString carried', inputs[0]?.args.keyString === 'a' && inputs[9]?.args.keyString === '1', JSON.stringify(inputs.map((c) => c.args.keyString)));
  check('space keycode 2050', inputs[6]?.args.keyCode === 2050);

  console.log('type CJK rejected:');
  r = await drive('type', '中文');
  check('exits 1 mentioning IME', r.code === 1 && r.stderr.includes('IME'), r.stderr);

  console.log('raw command escape hatch:');
  await clearInputs();
  r = await drive('raw', 'FoldStatus', '{"FoldStatus":"fold"}');
  inputs = await getInputs();
  check('raw command forwarded verbatim', r.code === 0 && inputs[0]?.command === 'FoldStatus' && inputs[0]?.args.FoldStatus === 'fold', JSON.stringify(inputs));
  r = await drive('raw', 'X', 'not-json');
  check('raw rejects bad json', r.code === 1 && r.stderr.includes('JSON'));

  console.log('key / back:');
  await clearInputs();
  await drive('key', 'Enter');
  await drive('back');
  inputs = await getInputs();
  check('Enter → 3 KeyPress keyCode 2054', inputs.slice(0, 3).every((c) => c.command === 'KeyPress' && c.args.keyCode === 2054), JSON.stringify(inputs[0]));
  check('BackClicked sent', inputs[3]?.command === 'BackClicked');

  console.log('unknown command:');
  r = await drive('bogus');
  check('exits 2 with command list', r.code === 2 && r.stderr.includes('commands:'));
} finally {
  mock.kill();
  temporary.cleanup();
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
