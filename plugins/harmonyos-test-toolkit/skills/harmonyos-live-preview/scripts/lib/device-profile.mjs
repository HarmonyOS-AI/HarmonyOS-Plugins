// 设备档位领域模型：把 `--devices` 上的每一条规格字符串解析成引擎需要的几何信息（设备类型 /
// 分辨率 / 密度 / 方向 / 安全区），并生成与之匹配的 `-f` 设备配置文件。
//
// 引擎侧的事实依据（ide_previewer 源码）：
//   - `-device` 只接受 util/CommandParser.h `supportedDevices` 里的字符串；不在表里直接启动失败。
//   - 启动参数 `-or/-cr` 的合法区间是 1–3840（CommandParser.h `MIN/MAX_RESOLUTION`），运行时改尺寸
//     的 `ResolutionSwitch` 命令则是 50–3000 / dpi 120–640（cli/CommandLine.h 的
//     `minWidth/maxWidth/minDpi/maxDpi`）——两条路径的上限本就不同，所以这里也分开记：启动尺寸按
//     3840 收（1440x3200 这种真实手机分辨率必须能启动），运行时 resize 按 3000 收。下限统一取 50，
//     再小的"设备"没有意义，而且低于 50 的尺寸连 resize 都调不回来。
//   - 逻辑尺寸（vp）= px / (dpi / 160)，BASE_SCREEN_DENSITY=160（jsapp/rich/JsAppImpl.h）。
//     ArkUI 的断点/响应式判断走的是 vp，所以自定义尺寸真正要对的是这个换算，而不是 px 本身。
//   - `-f` 文件里只有 `setting` 段会被引擎当成 SET 命令执行（cli/CommandLineInterface.cpp 的
//     `ApplyConfig`），也就是 Language + AvoidArea；`frontend` 段（Resolution/DeviceType）是给 IDE
//     读的元数据。生成时两段都写全，保持与 DevEco 产出的档位文件同构。
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const BASE_DENSITY = 160;

export const SIZE_LIMITS = Object.freeze({
  minSize: 50, maxLaunchSize: 3840, maxResizeSize: 3000, minDensity: 120, maxDensity: 640,
});

// 引擎默认的每类设备屏幕密度（jsapp/rich/JsAppImpl.h 的 *ScreenDensity 字段）——只在规格里没写
// `@dpi` 时兜底。tablet 是唯一的例外：这里沿用 320 而不是引擎默认的 400，因为 2048x1280@320 才是
// DevEco tablet 档位的 1024x640vp，本 skill 一直用的也是它。
const DEVICE_DENSITY = Object.freeze({
  phone: 480, tablet: 320, wearable: 320, tv: 320, car: 320, '2in1': 240, default: 480,
});

// 有完整默认几何的档位：直接写 `phone`/`tablet` 就能用。其余设备类型只作为 `<type>:WxH` 的类型
// 前缀存在——引擎虽然接受它们，但本 skill 没有实测过的默认分辨率，与其编一个不如要求显式写尺寸。
//
// safeArea 用 **vp** 记（不是 px）：状态栏 39vp / 导航条 28vp 是与屏幕大小无关的物理常量，换算成
// px 才依赖 dpi。phone 档位的 117px/84px @480dpi 正是 39vp/28vp。
const PRESETS = Object.freeze({
  phone: { deviceType: 'phone', resolution: [1080, 2340], safeArea: { top: 39, bottom: 28 } },
  tablet: { deviceType: 'tablet', resolution: [2048, 1280], safeArea: {} },
});

const DEVICE_TYPES = Object.keys(DEVICE_DENSITY);
const SPEC_RE = /^(?:([A-Za-z0-9]+):)?(\d+)x(\d+)(?:@(\d+))?$/i;

const isInt = (v) => Number.isInteger(v);

// 几何合法性检查，解析（启动）和运行时 resize 共用一份，两条路径的报错因此完全一致——只有尺寸上限
// 不同（引擎两侧的校验本就不同，见文件头），由 maxSize 传入。
// 返回 null 表示合法，否则返回可直接展示给用户的错误文案。
export function checkGeometry({ width, height, density }, { maxSize = SIZE_LIMITS.maxLaunchSize } = {}) {
  const { minSize, minDensity, maxDensity } = SIZE_LIMITS;
  for (const [name, v] of [['width', width], ['height', height]]) {
    if (!isInt(v) || v < minSize || v > maxSize) {
      return `${name} must be an integer within ${minSize}-${maxSize} (got ${v})`;
    }
  }
  if (!isInt(density) || density < minDensity || density > maxDensity) {
    return `density must be an integer within ${minDensity}-${maxDensity} (got ${density})`;
  }
  return null;
}

// px → vp。引擎按 vp 决定 ArkUI 断点，所以这是自定义尺寸里唯一"有语义"的数字。
export const toVp = (px, density) => Math.round(px / (density / BASE_DENSITY));

// 面板 id：既是 URL 路径段（/devices/:id）也是 `drive.mjs --device` 的取值，所以只用 [a-z0-9-]。
// 与档位默认几何完全一致时回落成档位名本身，这样 `--devices phone` 和 `--devices 1080x2340@480`
// 指的是同一块面板，不会因为写法不同多开一个引擎。
function deviceId(deviceType, [width, height], density) {
  const preset = PRESETS[deviceType];
  if (preset && preset.resolution[0] === width && preset.resolution[1] === height
    && DEVICE_DENSITY[deviceType] === density) return deviceType;
  const dpiPart = density === DEVICE_DENSITY[deviceType] ? '' : `-${density}dpi`;
  return `${deviceType}-${width}x${height}${dpiPart}`;
}

// 一条规格 → 一个设备档位。接受两种写法：
//   `phone` / `tablet`            —— 内置档位
//   `[<deviceType>:]<W>x<H>[@dpi]` —— 任意自定义尺寸，deviceType 默认 phone，dpi 默认按类型取
function parseDeviceSpec(raw) {
  const spec = String(raw).trim();
  const m = SPEC_RE.exec(spec);

  if (!m) {
    const preset = PRESETS[spec];
    if (!preset) {
      throw new Error(
        `unsupported device "${spec}"; use a preset (${Object.keys(PRESETS).join(', ')}) `
        + `or a custom size like 1440x3200@560 or tablet:1200x800 `
        + `(device types: ${DEVICE_TYPES.join(', ')})`,
      );
    }
    return makeProfile(preset.deviceType, preset.resolution, DEVICE_DENSITY[preset.deviceType]);
  }

  const deviceType = (m[1] ?? 'phone').toLowerCase();
  if (!DEVICE_DENSITY[deviceType]) {
    throw new Error(`unsupported device type "${deviceType}" in "${spec}"; supported: ${DEVICE_TYPES.join(', ')}`);
  }
  const resolution = [Number(m[2]), Number(m[3])];
  const density = m[4] ? Number(m[4]) : DEVICE_DENSITY[deviceType];
  const problem = checkGeometry({ width: resolution[0], height: resolution[1], density });
  if (problem) throw new Error(`invalid device "${spec}": ${problem}`);
  return makeProfile(deviceType, resolution, density);
}

function makeProfile(deviceType, [width, height], density) {
  return Object.freeze({
    id: deviceId(deviceType, [width, height], density),
    device: deviceType,
    resolution: Object.freeze([width, height]),
    density,
    // 引擎自己也会在 ResolutionSwitch 里按宽高关系重设方向（JsAppImpl::SetResolutionParams），
    // 启动参数 `-o` 用同一条规则推导，两条路径才不会打架。
    orientation: width > height ? 'landscape' : 'portrait',
    // vp 尺寸只用于展示与生成配置文件里的 frontend.Resolution，引擎不读它。
    safeArea: PRESETS[deviceType]?.safeArea ?? {},
  });
}

// `--devices a,b,c` / `--device a` → 档位数组。同一个 id 只保留一份（`phone` 与 `1080x2340@480`
// 是同一块面板），顺序按首次出现。
export function parseDeviceSpecs(raw) {
  const specs = (Array.isArray(raw) ? raw : String(raw).split(',')).map((s) => s.trim()).filter(Boolean);
  if (!specs.length) throw new Error('at least one --device/--devices value is required');
  const byId = new Map();
  for (const spec of specs) {
    const profile = parseDeviceSpec(spec);
    if (!byId.has(profile.id)) byId.set(profile.id, profile);
  }
  return [...byId.values()];
}

// 安全区（vp）→ 这个分辨率下的 px 矩形。安全区永远贴边：top/bottom 通宽、left/right 通高，
// 厚度按 dpi 换算，所以同一个档位放大分辨率时状态栏不会跟着变粗。没声明的边给零矩形——引擎要求
// 四个矩形都在（cli/CommandLine.cpp `AvoidAreaCommand::IsSetArgValid`）。
function avoidAreaRects(safeArea, [width, height], density) {
  const px = (vp) => Math.round((vp ?? 0) * (density / BASE_DENSITY));
  const zero = () => ({ posX: 0, posY: 0, width: 0, height: 0 });
  const topH = px(safeArea.top);
  const bottomH = px(safeArea.bottom);
  const leftW = px(safeArea.left);
  const rightW = px(safeArea.right);
  const sideH = Math.max(0, height - topH - bottomH); // 侧边安全区夹在上下安全区之间
  return {
    topRect: topH ? { posX: 0, posY: 0, width, height: topH } : zero(),
    leftRect: leftW ? { posX: 0, posY: topH, width: leftW, height: sideH } : zero(),
    rightRect: rightW ? { posX: width - rightW, posY: topH, width: rightW, height: sideH } : zero(),
    bottomRect: bottomH ? { posX: 0, posY: height - bottomH, width, height: bottomH } : zero(),
  };
}

// 生成 `-f` 设备配置文件的内容。`setting` 段是引擎真正会执行的（Language + AvoidArea），
// `frontend` 段是 vp 尺寸 + 设备类型的元数据，保持与 DevEco 产出的档位文件同构。
export function buildDeviceConfigJson(profile, { language = 'zh_CN' } = {}) {
  const [width, height] = profile.resolution;
  return {
    setting: {
      '1.0.1': {
        Language: { args: { Language: language } },
        AvoidArea: { args: avoidAreaRects(profile.safeArea ?? {}, profile.resolution, profile.density) },
      },
    },
    frontend: {
      '1.0.0': {
        Resolution: { args: { Resolution: `${toVp(width, profile.density)}*${toVp(height, profile.density)}` } },
        DeviceType: { args: { DeviceType: profile.device } },
      },
    },
  };
}

// 把每个档位的配置文件落到一个本次会话专属的临时目录里，返回 id → 路径，外加一个幂等的 cleanup()。
// 唯一有副作用的导出；解析与生成都是纯函数，可以单独测。
// 已经带了 deviceConfig 路径的档位（`--device-config` / $HARMONY_DEVICE_CONFIG 覆盖）原样透传。
//
// 这个目录归本函数所有：给定 dir 时会先清空再写，所以同一个端口重启预览不会留下上一次配置里的
// 设备文件。调用方（preview.mjs）传的是 registry.mjs 的 deviceConfigDir(port)，这样即使编排器被
// SIGKILL、cleanup() 没来得及跑，SessionEnd 钩子也知道该删哪儿。
export function materializeDeviceConfigs(profiles, { dir } = {}) {
  const root = dir ?? fs.mkdtempSync(path.join(os.tmpdir(), 'harmony-preview-devices-'));
  if (dir) { try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ } }
  fs.mkdirSync(root, { recursive: true });
  const paths = new Map();
  for (const profile of profiles) {
    if (profile.deviceConfig) { paths.set(profile.id, profile.deviceConfig); continue; }
    const file = path.join(root, `${profile.id}.json`);
    fs.writeFileSync(file, `${JSON.stringify(buildDeviceConfigJson(profile), null, 1)}\n`);
    paths.set(profile.id, file);
  }
  let cleaned = false;
  return {
    dir: root,
    paths,
    cleanup() {
      if (cleaned) return;
      cleaned = true;
      try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ }
    },
  };
}
