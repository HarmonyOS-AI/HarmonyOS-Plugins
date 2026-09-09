import { copyFile, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPluginConfigs } from './lib/plugin-config.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = path.join(root, 'dist', 'release');
const plugins = await loadPluginConfigs(root);
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
const checksums = [];
const names = new Set();
const notes = [
  '# 插件下载', '',
  'Qoder CN 导入插件 ZIP；TraeWork 逐个导入 Skill ZIP；OpenCode 使用对应版本的 .tgz 包。',
  '插件 ZIP 也包含其他客户端的清单和本地安装脚本，使用方法见仓库 README。',
  '不要使用 GitHub 自动生成的 Source code ZIP 作为插件导入包。', '',
  '| 插件 | 版本 | 用途 | 文件 |', '| --- | --- | --- | --- |'
];

for (const { config } of plugins) {
  const directory = path.join(root, 'dist', `${config.name}-${config.version}`);
  const manifest = JSON.parse(await readFile(path.join(directory, 'artifacts.json'), 'utf8'));
  if (manifest.plugin !== config.name || manifest.version !== config.version) {
    throw new Error(`Distribution metadata mismatch: ${config.name}`);
  }
  const entries = [
    ['Qoder CN / 完整插件', manifest.archives['qoder-cn']],
    ['OpenCode V1', manifest.archives['opencode-v1']],
    ['OpenCode V2', manifest.archives['opencode-v2']],
    ...(manifest.archives['trae-work'] ?? []).map(file => ['TraeWork Skill', file])
  ];
  for (const [host, relative] of entries) {
    const source = path.resolve(directory, relative);
    if (!source.startsWith(`${directory}${path.sep}`)) throw new Error(`Invalid artifact: ${relative}`);
    const name = relative.startsWith('trae-work/')
      ? `${config.name}-trae-work-${path.basename(relative)}`
      : path.basename(relative);
    if (names.has(name)) throw new Error(`Duplicate release asset: ${name}`);
    names.add(name);
    await copyFile(source, path.join(output, name));
    const hash = createHash('sha256').update(await readFile(source)).digest('hex');
    checksums.push(`${hash}  ${name}`);
    notes.push(`| ${config.name} | ${config.version} | ${host} | ${name} |`);
  }
}
await writeFile(path.join(output, 'SHA256SUMS.txt'), `${checksums.sort().join('\n')}\n`);
await writeFile(path.join(output, 'DOWNLOADS.md'), `${notes.join('\n')}\n`);
console.log(`Prepared ${names.size} release archives in ${output}`);
