#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const repositoryRoot = path.resolve(import.meta.dirname, '..');
const evaluationsRoot = path.join(repositoryRoot, 'evals');

function findEvaluationRoots(directory) {
  const roots = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      roots.push(...findEvaluationRoots(entryPath));
    } else if (entry.name === 'eval.config.json') {
      roots.push(directory);
    }
  }
  return roots;
}

const evaluationRoots = findEvaluationRoots(evaluationsRoot).sort();
if (evaluationRoots.length === 0) {
  console.error('No eval.config.json files found under evals/.');
  process.exit(1);
}

for (const evaluationRoot of evaluationRoots) {
  const runner = path.join(evaluationRoot, 'run.mjs');
  if (!fs.existsSync(runner)) {
    console.error(`Missing evaluation runner: ${path.relative(repositoryRoot, runner)}`);
    process.exit(1);
  }

  console.log(`\n>>> ${path.relative(repositoryRoot, evaluationRoot)}`);
  const result = spawnSync(process.execPath, [runner], {
    cwd: repositoryRoot,
    stdio: 'inherit',
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

console.log(`\n${evaluationRoots.length} evaluation target(s) passed.`);
