import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const evaluationRoot = path.dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(readFileSync(path.join(evaluationRoot, 'eval.config.json'), 'utf8'));
for (const suite of config.suites) {
  const result = spawnSync(process.execPath, ['--test', path.join(evaluationRoot, suite.entry)], {
    cwd: evaluationRoot,
    stdio: 'inherit',
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
