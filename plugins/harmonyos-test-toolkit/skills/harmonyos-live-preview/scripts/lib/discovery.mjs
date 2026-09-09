// Auto-discovery for the zero-DevEco preview: resolve the HarmonyOS toolchain and read the
// previewable module's settings straight from the project's own config files. This is the only
// place that touches the filesystem layout of a HarmonyOS project, so the rest of the pipeline
// stays project-agnostic.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { parseJson5 } from './json5.mjs';

const readJson5 = (file) => parseJson5(fs.readFileSync(file, 'utf8'));

const WIN = process.platform === 'win32';

// The whole toolchain derives from a single root, so the only thing a caller (or the AI) must supply
// is that root. A "root" is either a standalone command-line-tools dir or a DevEco bundle: they lay
// hvigor out differently but share the same sdk/ subtree, so each tool lists its candidate relative
// paths and the first that exists wins. Binary file names differ on Windows.
const TOOL_CANDIDATES = {
  hvigorw: [
    ['bin', WIN ? 'hvigorw.bat' : 'hvigorw'],                    // standalone command-line-tools
    ['tools', 'hvigor', 'bin', WIN ? 'hvigorw.bat' : 'hvigorw'], // DevEco bundle
  ],
  previewerBin: [
    ['sdk', 'default', 'openharmony', 'previewer', 'common', 'bin', WIN ? 'Previewer.exe' : 'Previewer'],
  ],
  hsp: [
    ['sdk', 'default', 'hms', 'previewer'],
  ],
};

const TOOL_LABELS = { hvigorw: 'hvigorw', previewerBin: 'Previewer engine', hsp: 'HMS previewer' };

// A DevEco bundle keeps its tools one level below the app dir (Contents/ on macOS), so accept either
// the given dir or its Contents child — lets the caller pass the .app or the bundle root directly.
const rootVariants = (root) => [root, path.join(root, 'Contents')];

const firstExisting = (base, candidates) => {
  for (const rel of candidates) {
    const p = path.join(base, ...rel);
    if (fs.existsSync(p)) return p;
  }
  return null;
};

// Resolve all three tools under a single root (trying its Contents child too). Returns the resolved
// toolchain, or null if any tool is missing — a root counts only when the whole toolchain is present.
function resolveUnder(root) {
  for (const base of rootVariants(root)) {
    if (!fs.existsSync(base)) continue;
    const resolved = {};
    for (const key of Object.keys(TOOL_CANDIDATES)) resolved[key] = firstExisting(base, TOOL_CANDIDATES[key]);
    if (Object.values(resolved).every(Boolean)) return { clt: base, ...resolved };
  }
  return null;
}

// Conventional install locations probed only when no explicit root is given. Platform-aware: each OS
// has its own DevEco prefix, plus the standalone command-line-tools dirs that work everywhere.
function autoRoots() {
  const roots = [
    process.env.HARMONY_SDK,
    process.env.HARMONY_CLT,
    path.join(os.homedir(), 'command-line-tools'),
    path.join(os.homedir(), 'Library', 'command-line-tools'),
  ];
  if (process.platform === 'darwin') {
    roots.push('/Applications/DevEco-Studio.app');
  } else if (WIN) {
    roots.push(path.join(process.env.ProgramFiles || 'C:\\Program Files', 'Huawei', 'DevEco Studio'));
    if (process.env.LOCALAPPDATA) roots.push(path.join(process.env.LOCALAPPDATA, 'Huawei', 'DevEco Studio'));
  } else {
    roots.push('/opt/deveco-studio', path.join(os.homedir(), 'deveco-studio'));
  }
  return roots.filter(Boolean);
}

// Per-tool report of what is missing under an explicit root, so the error names the actual gap.
function missingTools(root) {
  const base = rootVariants(root).find((b) => fs.existsSync(b));
  if (!base) return [];
  return Object.keys(TOOL_CANDIDATES)
    .filter((key) => !firstExisting(base, TOOL_CANDIDATES[key]))
    .map((key) => `${TOOL_LABELS[key]} (looked for ${TOOL_CANDIDATES[key].map((r) => r.join('/')).join(' or ')})`);
}

// Locate the HarmonyOS toolchain from a single root, deriving hvigorw + the SDK Previewer relative
// to it. With an explicit root (--clt / --sdk / $HARMONY_SDK) the root must resolve or we fail with a
// precise error; without one, the conventional install locations above are probed.
export function discoverToolchain(rootOverride) {
  if (rootOverride) {
    const found = resolveUnder(rootOverride);
    if (found) return found;
    const missing = missingTools(rootOverride);
    throw new Error(
      `HarmonyOS toolchain incomplete under "${rootOverride}". ` +
      (missing.length ? `Missing: ${missing.join('; ')}. ` : 'Found no hvigorw or sdk/ there. ') +
      'Point --clt / --sdk at a command-line-tools dir or a DevEco bundle.',
    );
  }
  for (const root of autoRoots()) {
    const found = resolveUnder(root);
    if (found) return found;
  }
  throw new Error(
    'HarmonyOS toolchain not found. Pass the command-line-tools / DevEco root via --clt <dir> ' +
    '(or set HARMONY_SDK). Expected hvigorw (bin/hvigorw or tools/hvigor/bin/hvigorw) and ' +
    'sdk/default/openharmony/previewer/common/bin/Previewer under it.',
  );
}

function listBuildableModules(projectDir, modules) {
  const resolved = [];
  for (const m of modules) {
    const srcPath = (m.srcPath || '').replace(/^\.\//, '');
    const moduleDir = path.join(projectDir, srcPath);
    const moduleJson = path.join(moduleDir, 'src/main/module.json5');
    if (!fs.existsSync(moduleJson)) continue;
    resolved.push({
      name: m.name,
      srcPath,
      moduleDir,
      module: readJson5(moduleJson).module || {},
      target: m.targets?.[0]?.name || 'default',
    });
  }
  return resolved;
}

// Read the previewable module's settings from build-profile.json5 + module.json5 + oh-package.json5.
// Without --module, the entry-type module is chosen automatically.
export function discoverProject(projectDir, { module: moduleOverride, page } = {}) {
  const buildProfile = path.join(projectDir, 'build-profile.json5');
  if (!fs.existsSync(buildProfile)) {
    throw new Error(`Not a HarmonyOS project root: ${projectDir} (missing build-profile.json5).`);
  }
  const bp = readJson5(buildProfile);
  const product = bp.app?.products?.[0]?.name || 'default';
  const modules = listBuildableModules(projectDir, bp.modules || []);
  if (modules.length === 0) throw new Error(`No buildable modules with a module.json5 found under ${projectDir}.`);

  let chosen;
  if (moduleOverride) {
    chosen = modules.find((m) => m.name === moduleOverride);
    if (!chosen) throw new Error(`Module "${moduleOverride}" not found. Available: ${modules.map((m) => m.name).join(', ')}.`);
  } else {
    chosen = modules.find((m) => m.module.type === 'entry');
    if (!chosen) throw new Error(`No entry-type module to preview. Pass --module <name>. Available: ${modules.map((m) => m.name).join(', ')}.`);
  }

  const ability = (chosen.module.abilities || [])[0];
  if (!ability?.srcEntry) throw new Error(`Module "${chosen.name}" declares no UIAbility to preview.`);
  const abilitySrc = 'src/main/' + ability.srcEntry.replace(/^\.\//, '');
  const pagesProfile = (chosen.module.pages || '').replace(/^\$profile:/, '') || 'main_pages';

  const ohPkg = path.join(chosen.moduleDir, 'oh-package.json5');
  const pkgName = fs.existsSync(ohPkg) ? (readJson5(ohPkg).name || chosen.name) : chosen.name;

  let entryPage = page;
  if (!entryPage) {
    const pagesJson = path.join(chosen.moduleDir, 'src/main/resources/base/profile', `${pagesProfile}.json`);
    entryPage = fs.existsSync(pagesJson) ? (readJson5(pagesJson).src?.[0] || 'pages/Index') : 'pages/Index';
  }

  return {
    dir: projectDir,
    product,
    moduleName: chosen.name,
    moduleRel: chosen.srcPath,
    moduleDir: chosen.moduleDir,
    target: chosen.target,
    pkgName,
    abilityName: ability.name,
    abilitySrc,
    pagesProfile,
    entryPage,
    watchDirs: [path.join(chosen.moduleDir, 'src/main/ets')],
  };
}
