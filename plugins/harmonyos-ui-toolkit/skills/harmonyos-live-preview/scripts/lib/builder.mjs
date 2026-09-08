// Compiles the project with the HarmonyOS command-line hvigorw (which computes the full project
// model itself — no DevEco, no preview-service). Runs the `PreviewBuild` task graph — the same one
// DevEco's own preview daemon drives (PreviewUpdateAssets → ReplacePreviewerPage → PreviewArkTS →
// buildPreviewerResource) — instead of `assembleHap`. It's a regular, CLI-invocable hvigor task
// (registered unconditionally for every HAP module, not IDE-injected), and its ArkTS compile embeds
// the inspector/debug metadata `assembleHap` output lacks, so the engine's "inspector" command comes
// back with a real component tree instead of a bare root. `previewer.replace.page` targets the exact
// @Entry route being previewed, mirroring the --page override.
import { spawn } from 'node:child_process';
import { buildPaths } from './config.mjs';
import { syncPreviewBuildConfigs } from './preview-config.mjs';
import { withBuildLock } from './build-lock.mjs';

// Two previews of the same project share one hvigor build tree, so their builds have to take turns —
// see build-lock.mjs. Keyed by project+product because that's exactly the .preview/<product> subtree
// they contend over; previewing two different projects, or two products of one project, still runs
// fully in parallel.
export function build(config, log = console.log) {
  const { dir, product } = config.project;
  return withBuildLock(`${dir}::${product}`, () => runPreviewBuild(config, log), { log });
}

function runPreviewBuild(config, log) {
  return new Promise((resolve) => {
    const { dir, moduleName, target, product, entryPage } = config.project;
    const t0 = Date.now();
    // `detached: true` makes this child the leader of its own process group (pgid === pid) instead
    // of sharing the orchestrator's group. `hvigorw` is a bash wrapper that forks `node hvigorw.js`,
    // which forks `node hvigor.js` — three processes deep — and killing just the top one leaves the
    // deeper two running as orphans (reparented to pid 1) since SIGKILL doesn't propagate to
    // children. Killing the whole group via `-child.pid` (see finish()) takes all three at once.
    // `buildRoot=.preview` is the master switch for the whole preview pipeline: hvigor-ohos-plugin
    // computes `isPreview = extraConfig.buildRoot === '.preview'` in every task, and only then do
    // the resource/asset steps write the .preview/<product>/intermediates tree that PreviewArkTS
    // (addOhmurlToHarAbility) reads back. Without it those tasks target the normal build/ tree and
    // PreviewArkTS crashes with `00308018 … "data" argument must be of type string` — which is a
    // missing-config symptom, not a toolchain bug.
    const child = spawn(config.toolchain.hvigorw, [
      '--mode', 'module',
      '-p', `module=${moduleName}@${target}`,
      '-p', `product=${product}`,
      '-p', 'buildRoot=.preview',
      '-p', `previewer.replace.page=${entryPage}`,
      // Escape hatch for build-injection experiments (extra `-p key=value` pairs, space-separated)
      // — same spirit as drive.mjs `raw` for the engine pipe.
      ...(process.env.PREVIEW_HVIGOR_ARGS ? process.env.PREVIEW_HVIGOR_ARGS.split(/\s+/) : []),
      'PreviewBuild', '--no-daemon',
    ], { cwd: dir, stdio: ['ignore', 'pipe', 'pipe'], detached: true });

    let tail = '';
    let settled = false;
    // `PreviewBuild` reliably prints its terminal "BUILD SUCCESSFUL"/"BUILD FAILED" line within a
    // few seconds — all task output is flushed to disk by then — but unlike `assembleHap` the
    // process itself doesn't reliably exit afterward (some hvigor-ohos-plugin preview task leaves a
    // handle open; harmless for a persistent daemon, but this skill invokes it `--no-daemon`, one
    // process per rebuild). So resolve on the printed marker and kill the process group explicitly,
    // rather than waiting on an `exit` event that may never come. `child.on('exit', …)` below stays
    // as a fallback for the case where the process does exit on its own first.
    const finish = (ok) => {
      if (settled) return;
      settled = true;
      log(`build ${ok ? 'OK' : 'FAILED'} in ${((Date.now() - t0) / 1000).toFixed(1)}s${ok ? '' : '\n' + tail.slice(-1200)}`);
      // The engine reads these right after launch (HSP loading happens before any app code runs),
      // so they have to exist before the engine starts — and they point at paths this build just
      // produced.
      if (ok) syncPreviewBuildConfigs(config, buildPaths(config), log);
      resolve({ ok, output: tail });
      try { process.kill(-child.pid, 'SIGKILL'); } catch { try { child.kill('SIGKILL'); } catch {} }
    };
    const cap = (d) => {
      tail = (tail + d).slice(-4000);
      if (/BUILD SUCCESSFUL/.test(tail)) finish(true);
      else if (/BUILD FAILED/.test(tail)) finish(false);
    };
    child.stdout.on('data', cap);
    child.stderr.on('data', cap);
    child.on('error', (err) => { if (!settled) { settled = true; resolve({ ok: false, output: `failed to spawn hvigorw: ${err.message}` }); } });
    child.on('exit', (code) => {
      if (settled) return;
      const ok = code === 0 && /BUILD SUCCESSFUL/.test(tail);
      log(`build ${ok ? 'OK' : 'FAILED'} in ${((Date.now() - t0) / 1000).toFixed(1)}s${ok ? '' : '\n' + tail.slice(-1200)}`);
      resolve({ ok, output: tail });
    });
  });
}
