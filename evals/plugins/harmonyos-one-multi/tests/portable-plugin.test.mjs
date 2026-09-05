import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, symlinkSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = fileURLToPath(new URL('../../../../', import.meta.url));
const pluginRoot = path.join(repositoryRoot, 'plugins/harmonyos-one-multi');
const temporaryRoot = mkdtempSync(path.join(os.tmpdir(), 'one-multi-plugin-'));
const isolatedPlugin = path.join(temporaryRoot, 'plugin');
cpSync(pluginRoot, isolatedPlugin, { recursive: true });
after(() => rmSync(temporaryRoot, { recursive: true, force: true }));

function filesUnder(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? filesUnder(target) : [target];
  });
}

test('all 230 migrated source files remain byte-for-byte unchanged', () => {
  const inventory = JSON.parse(readFileSync(new URL('../migration-inventory.json', import.meta.url), 'utf8'));
  assert.equal(inventory.files.length, 230);
  assert.equal(new Set(inventory.files.map((file) => file.destination)).size, 230);
  for (const file of inventory.files) {
    const destination = path.join(repositoryRoot, file.destination);
    assert.ok(existsSync(destination), file.source);
    const checksum = createHash('sha256').update(readFileSync(destination)).digest('hex');
    assert.equal(checksum, file.sourceSha256, file.source);
  }
});

test('five isolated skills have matching identities and exclude evaluation files', () => {
  const skillsRoot = path.join(isolatedPlugin, 'skills');
  const skills = readdirSync(skillsRoot, { withFileTypes: true }).filter((entry) => entry.isDirectory());
  assert.equal(skills.length, 5);
  for (const skill of skills) {
    const root = path.join(skillsRoot, skill.name);
    const source = readFileSync(path.join(root, 'SKILL.md'), 'utf8');
    assert.equal(source.match(/^name: (.+)$/m)?.[1], skill.name);
    assert.ok(!existsSync(path.join(root, 'evals')));
  }
});

test('OpenCode loads every skill and supporting resource from the isolated plugin', async () => {
  // Only Node dependencies are shared; all plugin content lives in the temp copy.
  symlinkSync(path.join(repositoryRoot, 'node_modules'), path.join(temporaryRoot, 'node_modules'), 'dir');
  const { default: createPlugin } = await import(pathToFileURL(path.join(isolatedPlugin, 'opencode/plugin.js')));
  const plugin = await createPlugin();
  const output = { system: [] };
  await plugin['experimental.chat.system.transform']({}, output);
  const loader = plugin.tool.harmonyos_one_multi_skill;
  for (const skill of readdirSync(path.join(isolatedPlugin, 'skills'))) {
    assert.ok(output.system.join('\n').includes(skill));
    assert.match(await loader.execute({ skill }), /Resource: SKILL\.md/);
    const references = JSON.parse(await loader.execute({ skill, resource: 'references' }));
    assert.ok(references.entries.length > 0);
    assert.ok(realpathSync(references.baseDirectory).startsWith(realpathSync(isolatedPlugin)));
    const resource = references.entries.find((entry) => entry.endsWith('.md'));
    assert.match(await loader.execute({ skill, resource: `references/${resource}` }), /Resource: references\//);
  }
});

test('npm package contains every runtime resource without evaluation or session files', () => {
  const result = spawnSync('npm', ['pack', '--dry-run', '--json', '--ignore-scripts'], {
    cwd: isolatedPlugin,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  const [packed] = JSON.parse(result.stdout);
  const included = new Set(packed.files.map((file) => file.path));
  for (const file of filesUnder(isolatedPlugin)) {
    const relative = path.relative(isolatedPlugin, file);
    if (path.basename(file) !== '.gitignore') assert.ok(included.has(relative), relative);
  }
  assert.ok(![...included].some((file) => /(^|\/)(evals|__pycache__|\.harmonybot|\.onemulti)(\/|$)/.test(file)));
});
