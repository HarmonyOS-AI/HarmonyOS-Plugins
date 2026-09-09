// Assembles the immutable runtime config for one preview session from caller inputs +
// auto-discovery. Pure assembly: no spawning, no servers — just the resolved object the
// builder/engine/bridge read. Build-artifact paths and the ability ohmurl are derived here so
// the layout knowledge lives in one place.
import fs from 'node:fs';
import path from 'node:path';
import { discoverToolchain, discoverProject } from './discovery.mjs';
import { parseDeviceSpecs } from './device-profile.mjs';

// Per-device render geometry comes from device-profile.mjs, which turns each --device/--devices
// entry (a preset name like `phone`, or a custom size like `1440x3200@560` / `tablet:1200x800`)
// into the three pieces the Previewer engine needs, and which must agree:
//   resolution   — physical framebuffer px, passed as -or/-cr (this IS the frame size)
//   density      — screen dpi, passed as -sd; logical vp = px / (density / 160)
//   deviceConfig — the -f settings file, whose "Resolution" is that same logical vp and
//                  whose DeviceType drives which ArkUI deviceType/breakpoints the app sees.
// The config file is generated from the same profile (see materializeDeviceConfigs), so the three
// can't drift apart the way a hand-maintained per-device JSON asset could.

export function resolveConfig(opts = {}) {
  const projectDir = path.resolve(opts.project || process.cwd());
  const toolchain = discoverToolchain(opts.clt);
  const project = discoverProject(projectDir, { module: opts.module, page: opts.page });

  // false (default) = page-preview mode: render the page via -url, like DevEco's per-@Entry preview.
  // true = ability mode: launch the real UIAbility and show whatever its loadContent loads.
  const abilityMode = opts.abilityMode === true;
  // Engine half of DevEco's @Preview component preview (flips the compiled getPreviewComponentFlag()
  // gate) — plain page/ability preview keeps it off. See how-it-works.md § 组件预览调查.
  const componentMode = opts.componentMode === true;
  // Each device gets its own Previewer engine process (one process = one resolution — the engine
  // reads its geometry once at launch, see engine.mjs), so a second/third simultaneous size means a
  // second/third -lws port. Base port + index keeps them predictable and collision-free from a single
  // --lws override.
  const lwsBase = Number(opts.lwsPort ?? process.env.LWS ?? 41200);

  // An explicit -f override applies to every device (it's a single file); otherwise deviceConfig is
  // left null here and preview.mjs materializes one file per profile before launching the engines.
  const deviceConfigOverride = opts.deviceConfig || process.env.HARMONY_DEVICE_CONFIG || null;

  // Every device entry is a complete, self-contained "engine session config" (project/toolchain/
  // abilityMode/componentMode + its own geometry) — engine.mjs's launchEngine() takes exactly this
  // shape already, so passing devices[i] straight through needs no changes there.
  const devices = parseDeviceSpecs(opts.devices ?? opts.device ?? 'phone').map((profile, i) => Object.freeze({
    ...profile,
    project,
    toolchain,
    abilityMode,
    componentMode,
    deviceConfig: deviceConfigOverride,
    lwsPort: lwsBase + i,
  }));

  return Object.freeze({
    toolchain,
    project,
    devices,
    ports: {
      http: Number(opts.httpPort ?? process.env.PORT ?? 8088),
    },
    watch: opts.watch !== false,
    abilityMode,
    componentMode,
    // Auto-release the preview once the last browser viewer closes (default on). --keep-alive turns
    // it off for headless / always-on use. Grace tolerates a reload before tearing down.
    autoRelease: opts.keepAlive !== true,
    releaseGraceMs: Number(opts.releaseGraceMs ?? process.env.PREVIEW_RELEASE_GRACE_MS ?? 10000),
  });
}

// Build artifacts produced by `hvigorw PreviewBuild`, laid out as
// .preview/<product>/intermediates/{loader,assets,res}/<target>/… — the same task graph DevEco's
// own preview daemon drives. Its ArkTS compile step (PreviewArkTS) embeds inspector/debug metadata
// (component tree, per-node rects, source line mapping) that a plain `assembleHap` build strips, so
// this is what makes the engine's "inspector" command return a populated tree instead of a bare root.
export function buildPaths(config) {
  const { moduleDir, product, target } = config.project;
  const intermediates = path.join(moduleDir, '.preview', product, 'intermediates');
  // The compiled-app dir is named `loader_out/` by CLI-driven PreviewBuild (hvigor 6.26.x) and
  // `assets/` by other toolchain flows — probe for whichever this build produced.
  const jsDir = ['loader_out', 'assets'].find(
    (d) => fs.existsSync(path.join(intermediates, d, target, 'ets')),
  ) || 'loader_out';
  return {
    intermediates,
    loaderJson: `${intermediates}/loader/${target}/loader.json`,
    jsApp: `${intermediates}/${jsDir}/${target}/ets`,
    appResource: `${intermediates}/res/${target}`,
  };
}

// e.g. @normalized:N&&&default/src/main/ets/defaultability/DefaultAbility&
export function abilityOhmurl(config) {
  const { pkgName, abilitySrc } = config.project;
  return `@normalized:N&&&${pkgName}/${abilitySrc.replace(/\.ets$/, '')}&`;
}
