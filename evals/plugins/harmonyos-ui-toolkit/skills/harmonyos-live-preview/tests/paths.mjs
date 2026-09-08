import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const testsDirectory = path.dirname(fileURLToPath(import.meta.url));

export const repositoryRoot = path.resolve(testsDirectory, '../../../../../..');
export const skillRoot = path.join(
  repositoryRoot,
  'plugins',
  'harmonyos-ui-toolkit',
  'skills',
  'harmonyos-live-preview',
);
export const DRIVE = path.join(skillRoot, 'scripts', 'drive.mjs');
export const MOCK = path.join(testsDirectory, 'mock-bridge.mjs');

export function createEvalTempDir(suite) {
  const temporaryPath = fs.mkdtempSync(path.join(os.tmpdir(), `harmonyos-live-preview-${suite}-`));
  return {
    path: temporaryPath,
    cleanup: () => fs.rmSync(temporaryPath, { recursive: true, force: true }),
  };
}
