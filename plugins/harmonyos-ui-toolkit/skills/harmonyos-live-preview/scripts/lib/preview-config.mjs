// Writes the per-module `.preview/config/buildConfig.json` that DevEco's IDE side produces and
// hvigor's PreviewBuild only ever *reads* (PreviewUpdateAssets consumes its stageRouterConfig).
// Under a pure-CLI build nobody writes it, and the engine needs it in two situations:
//
//  1. HSP dependencies (`"type": "shared"` modules). The engine loads them as separate packages at
//     startup: modulePathMap in loader.json → <moduleDir>/.preview/config/buildConfig.json →
//     `aceModuleBuild` → modules.abc. Without the file the engine dies before any app code runs —
//     `load hsp failed, hsp name:<module>` at Fatal level, zero frames, engine never connects.
//     (hvigor already *compiles* those modules as a side effect of building the entry module; only
//     this pointer file is missing.)
//
//  2. Mocks (src/mock/mock-config.json5). PreviewArkTS rewrites every mock target into a normalized
//     OHM url that carries the module name — `@normalized:N&entry&&entry/src/mock/…&` — which the
//     engine resolves through the exact same lookup. Without the file every mocked module fails the
//     same way and the page comes up blank.
//
// Both are the same missing pointer, so one pass over loader.json's modulePathMap fixes both: any
// module that has preview artifacts of its own gets a buildConfig.json pointing at them.
import fs from 'node:fs';
import path from 'node:path';

// Where a module's compiled preview output lives. CLI-driven PreviewBuild (hvigor 6.26.x) names it
// `loader_out/`; other toolchain flows use `assets/`.
function artifactDir(moduleDir, product, target) {
  const intermediates = path.join(moduleDir, '.preview', product, 'intermediates');
  for (const dir of ['loader_out', 'assets']) {
    const ets = path.join(intermediates, dir, target, 'ets');
    if (fs.existsSync(ets)) return ets;
  }
  return null;
}

function modulePaths(config, loaderJsonPath) {
  const { moduleName, moduleDir } = config.project;
  const map = new Map([[moduleName, moduleDir]]);
  try {
    for (const [name, dir] of Object.entries(JSON.parse(fs.readFileSync(loaderJsonPath, 'utf8')).modulePathMap || {})) {
      if (!map.has(name)) map.set(name, dir);
    }
  } catch { /* no loader.json yet — the previewed module alone is still worth wiring up */ }
  return map;
}

// Returns the module names wired up. Never throws: a failure here costs mock support or HSP
// loading, but must not take the whole preview down.
export function syncPreviewBuildConfigs(config, paths, log = () => {}) {
  const { product, target } = config.project;
  const wired = [];
  for (const [name, dir] of modulePaths(config, paths.loaderJson)) {
    const ets = name === config.project.moduleName ? paths.jsApp : artifactDir(dir, product, target);
    if (!ets) continue; // module contributes no preview artifacts of its own (plain HAR) — nothing to point at
    const file = path.join(dir, '.preview', 'config', 'buildConfig.json');
    // Preserve whatever is already there — a DevEco-written file carries stageRouterConfig that
    // hvigor reads — and only ensure the fields the engine needs.
    let existing = {};
    try { existing = JSON.parse(fs.readFileSync(file, 'utf8')); } catch { /* absent or unreadable */ }
    try {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, JSON.stringify({ ...existing, aceModuleBuild: ets, moduleName: name, packageName: name }, null, 2));
      wired.push(name);
    } catch (e) {
      log(`preview-config: could not write ${file} (${e.message}) — mocks and HSP loading in "${name}" will fail`);
    }
  }
  if (wired.length) log(`preview-config: wired .preview/config for ${wired.join(', ')}`);
  return wired;
}
