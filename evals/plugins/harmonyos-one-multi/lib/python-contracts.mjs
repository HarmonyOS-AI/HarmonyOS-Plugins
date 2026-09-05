import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Reconstruct the source layout only in a temporary directory. The original
// contracts stay unchanged, while installed skills never depend on evals/.
export function runPythonContracts(moduleUrl) {
  const evaluationRoot = path.dirname(fileURLToPath(moduleUrl));
  const config = JSON.parse(readFileSync(path.join(evaluationRoot, 'eval.config.json'), 'utf8'));
  const skillRoot = path.resolve(evaluationRoot, config.target.path);
  const temporaryRoot = mkdtempSync(path.join(os.tmpdir(), 'one-multi-contracts-'));

  try {
    const isolatedSkill = path.join(temporaryRoot, config.target.skill);
    cpSync(skillRoot, isolatedSkill, { recursive: true });
    cpSync(evaluationRoot, path.join(isolatedSkill, 'evals'), { recursive: true });
    for (const suite of config.suites) {
      const result = spawnSync(process.env.PYTHON ?? 'python3', [
        path.join(isolatedSkill, 'evals', suite.entry),
      ], {
        cwd: isolatedSkill,
        env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
        stdio: 'inherit',
      });
      if (result.error) throw result.error;
      if (result.status !== 0) {
        process.exitCode = result.status ?? 1;
        return;
      }
    }
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
}
