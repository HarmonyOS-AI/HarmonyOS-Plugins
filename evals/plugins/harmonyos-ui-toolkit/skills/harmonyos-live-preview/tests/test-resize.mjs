#!/usr/bin/env node
// 自定义尺寸能力的两层测试：
//   1) device-profile.mjs 的纯函数（规格解析 / 几何校验 / 设备配置文件生成）——不需要任何服务
//   2) drive.mjs 的 resize 命令 —— 对着 mock-bridge.mjs 跑，覆盖等待帧几何、越界拒绝、--device 定向
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import {
  parseDeviceSpecs, buildDeviceConfigJson, checkGeometry, toVp, materializeDeviceConfigs, SIZE_LIMITS,
} from '../../../../../../plugins/harmonyos-ui-toolkit/skills/harmonyos-live-preview/scripts/lib/device-profile.mjs';
import { createEvalTempDir, DRIVE, MOCK } from './paths.mjs';

const execFileP = promisify(execFile);
const PORT = 18901;
const base = `http://127.0.0.1:${PORT}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const temporary = createEvalTempDir('resize');

let passed = 0, failed = 0;
const check = (name, cond, detail = '') => {
  if (cond) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.log(`  ✗ ${name}  ${detail}`); }
};
const spec1 = (s) => parseDeviceSpecs(s)[0];
const rejects = (s) => { try { parseDeviceSpecs(s); return false; } catch { return true; } };

console.log('规格解析:');
check('预设 phone', JSON.stringify(spec1('phone')) === JSON.stringify({
  id: 'phone', device: 'phone', resolution: [1080, 2340], density: 480, orientation: 'portrait',
  safeArea: { top: 39, bottom: 28 },
}), JSON.stringify(spec1('phone')));
check('裸尺寸默认 phone 类型', spec1('720x1280').device === 'phone' && spec1('720x1280').id === 'phone-720x1280');
check('@dpi 生效并进 id', spec1('1440x3200@560').density === 560 && spec1('1440x3200@560').id === 'phone-1440x3200-560dpi');
check('类型前缀生效', spec1('tablet:1200x800').device === 'tablet' && spec1('tablet:1200x800').density === 320);
check('引擎支持的其他类型可用', spec1('2in1:2560x1600').device === '2in1' && spec1('2in1:2560x1600').density === 240);
check('宽>高 → landscape', spec1('1200x800').orientation === 'landscape' && spec1('800x1200').orientation === 'portrait');
check('与预设等价的自定义尺寸回落成预设 id', spec1('1080x2340@480').id === 'phone');
check('同一面板不重复', parseDeviceSpecs('phone,1080x2340@480,tablet').map((d) => d.id).join(',') === 'phone,tablet');
check('多规格保持顺序', parseDeviceSpecs('tablet,720x1280').map((d) => d.id).join(',') === 'tablet,phone-720x1280');

console.log('几何校验:');
check('未知档位被拒', rejects('watch'));
check('太小被拒', rejects('40x100'));
check('超过启动上限被拒', rejects('3900x1000'));
check('dpi 越界被拒', rejects('1080x2340@99') && rejects('1080x2340@700'));
check('启动上限 3840 > resize 上限 3000', checkGeometry({ width: 3200, height: 1000, density: 480 }) === null
  && checkGeometry({ width: 3200, height: 1000, density: 480 }, { maxSize: SIZE_LIMITS.maxResizeSize }) !== null);
check('vp 换算', toVp(1080, 480) === 360 && toVp(1440, 560) === 411);

console.log('设备配置文件生成:');
const phoneCfg = buildDeviceConfigJson(spec1('phone'));
check('phone 与仓库里原有的档位资产一致（安全区 + vp 分辨率）',
  phoneCfg.setting['1.0.1'].AvoidArea.args.topRect.height === 117
  && phoneCfg.setting['1.0.1'].AvoidArea.args.bottomRect.posY === 2256
  && phoneCfg.frontend['1.0.0'].Resolution.args.Resolution === '360*780',
  JSON.stringify(phoneCfg.setting['1.0.1'].AvoidArea.args));
const bigCfg = buildDeviceConfigJson(spec1('1440x3200@560'));
check('安全区按 dpi 换算而不是按屏幕比例', bigCfg.setting['1.0.1'].AvoidArea.args.topRect.height === Math.round(39 * 560 / 160),
  JSON.stringify(bigCfg.setting['1.0.1'].AvoidArea.args.topRect));
check('安全区贴边（底部矩形贴到屏幕底）',
  bigCfg.setting['1.0.1'].AvoidArea.args.bottomRect.posY === 3200 - Math.round(28 * 560 / 160));
check('无安全区的档位四个矩形全零',
  Object.values(buildDeviceConfigJson(spec1('tablet')).setting['1.0.1'].AvoidArea.args)
    .every((r) => r.width === 0 && r.height === 0));
check('DeviceType 跟着类型前缀走', buildDeviceConfigJson(spec1('2in1:2560x1600')).frontend['1.0.0'].DeviceType.args.DeviceType === '2in1');

const written = materializeDeviceConfigs(parseDeviceSpecs('phone,1440x3200@560'));
check('每个档位落一个文件', written.paths.size === 2 && [...written.paths.values()].every((p) => fs.existsSync(p)));
check('落盘内容可被解析回同样的 JSON',
  JSON.stringify(JSON.parse(fs.readFileSync(written.paths.get('phone'), 'utf8'))) === JSON.stringify(phoneCfg));
const customConfigPath = path.join(temporary.path, 'custom.json');
const overridden = materializeDeviceConfigs([{ ...spec1('phone'), deviceConfig: customConfigPath }]);
check('调用方给了 -f 覆盖就原样透传', overridden.paths.get('phone') === customConfigPath);
const dir = written.dir;
written.cleanup(); overridden.cleanup();
check('cleanup 删干净临时目录', !fs.existsSync(dir));

console.log('\ndrive.mjs resize（对 mock-bridge）:');
const mock = spawn('node', [MOCK, String(PORT)], { stdio: 'inherit' });
for (let i = 0; i < 40; i++) {
  try { await fetch(`${base}/status`); break; } catch { await sleep(100); }
}

async function drive(...args) {
  try {
    const { stdout, stderr } = await execFileP('node', [DRIVE, ...args, '--port', String(PORT)], { timeout: 30000 });
    return { code: 0, stdout, stderr };
  } catch (e) { return { code: e.code ?? 1, stdout: e.stdout ?? '', stderr: e.stderr ?? '' }; }
}
const getStatus = async () => (await fetch(`${base}/status`)).json();
const getInputs = async (id) => (await fetch(`${base}/debug/inputs?device=${id}`)).json();
const setDevice = (id, patch) => fetch(`${base}/debug/setDevice`, { method: 'POST', body: JSON.stringify({ id, ...patch }) });

try {
  let r = await drive('resize', '900x1600@320');
  check('exits 0', r.code === 0, r.stderr);
  check('打印新几何与 vp', r.stdout.includes('900x1600@320dpi') && r.stdout.includes('450x800vp'), r.stdout);
  let st = await getStatus();
  check('默认设备被改', JSON.stringify(st.devices[0].resolution) === '[900,1600]' && st.devices[0].density === 320);
  check('启动几何仍被记着', JSON.stringify(st.devices[0].launchResolution) === '[1080,2340]');
  check('另一台没被碰', JSON.stringify(st.devices[1].resolution) === '[2048,1280]');

  const cmds = await getInputs('phone');
  const rs = cmds.find((c) => c.command === 'ResolutionSwitch');
  check('发出的是 ResolutionSwitch', !!rs, JSON.stringify(cmds.slice(-1)));
  check('用 set 信封（action 会被引擎丢掉）', rs?.type === 'set', JSON.stringify(rs));
  check('args 完整', rs?.args.originWidth === 900 && rs?.args.width === 900 && rs?.args.height === 1600
    && rs?.args.screenDensity === 320 && rs?.args.reason === 'resize', JSON.stringify(rs?.args));

  console.log('省略 dpi 时沿用当前密度:');
  r = await drive('resize', '600x900');
  st = await getStatus();
  check('密度保持 320', st.devices[0].density === 320 && JSON.stringify(st.devices[0].resolution) === '[600,900]', JSON.stringify(st.devices[0]));

  console.log('--device 定向:');
  r = await drive('resize', '1000x700', '--device', 'tablet');
  check('exits 0', r.code === 0, r.stderr);
  st = await getStatus();
  check('只改了 tablet', JSON.stringify(st.devices[1].resolution) === '[1000,700]' && JSON.stringify(st.devices[0].resolution) === '[600,900]');

  console.log('越界与坏输入:');
  r = await drive('resize', '3200x1000');
  check('超过 resize 上限 → exit 1，且本地就拦下了', r.code === 1 && r.stderr.includes('50-3000'), r.stderr);
  r = await drive('resize', 'abc');
  check('格式不对 → usage', r.code === 1 && r.stderr.includes('usage: resize'), r.stderr);
  r = await drive('resize', '900x1600', '--device', 'nope');
  check('未知 --device 快速失败', r.code === 1 && r.stderr.includes('unknown --device'), r.stderr);

  console.log('等待帧几何跟上:');
  await setDevice('phone', { frameLagMs: 1200 });
  const t0 = Date.now();
  r = await drive('resize', '800x1400');
  const elapsed = Date.now() - t0;
  check('阻塞到新尺寸的帧真的出现', r.code === 0 && elapsed >= 1200, `${elapsed}ms ${r.stdout}`);
  check('没有多余的告警', !r.stdout.includes('catching up'), r.stdout);
  st = await getStatus();
  check('frameResolution 已收敛', JSON.stringify(st.devices[0].frameResolution) === '[800,1400]', JSON.stringify(st.devices[0]));

  console.log('devices 输出:');
  r = await drive('devices');
  check('带 dpi 与 vp', r.stdout.includes('800x1400@320dpi') && r.stdout.includes('vp)'), r.stdout);

  console.log('raw --type:');
  await fetch(`${base}/debug/clear`);
  r = await drive('raw', 'FoldStatus', '{"FoldStatus":"fold"}', '--type', 'set');
  const raw = (await getInputs('phone')).at(-1);
  check('type 透传到引擎命令', raw?.type === 'set' && raw?.command === 'FoldStatus', JSON.stringify(raw));
  r = await drive('raw', 'Something', '{}', '--type', 'bogus');
  check('非法 type 被拒', r.code === 1 && r.stderr.includes('--type must be'), r.stderr);
} finally {
  mock.kill('SIGKILL');
  temporary.cleanup();
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
