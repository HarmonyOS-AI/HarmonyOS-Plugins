#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const evaluationRoot = path.dirname(fileURLToPath(import.meta.url));
const configPath = path.join(evaluationRoot, 'eval.config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const targetPath = path.resolve(evaluationRoot, config.target.path);

if (!fs.existsSync(path.join(targetPath, 'SKILL.md'))) {
  console.error(`Evaluation target is missing or invalid: ${targetPath}`);
  process.exit(1);
}

for (const suite of config.suites) {
  console.log(`\n=== ${config.target.skill}: ${suite.id} ===`);
  const result = spawnSync(process.execPath, [path.join(evaluationRoot, suite.entry)], {
    cwd: evaluationRoot,
    stdio: 'inherit',
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

console.log(`\n${config.suites.length} evaluation suites passed.`);
