#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const target = path.resolve(process.argv[2] ?? '.');
const scannerPath = path.resolve(process.argv[1]);
const scannerTestPath = path.resolve(path.dirname(scannerPath), 'test-scan-rules.mjs');
const ignored = new Set([
  '.git', '.hg', '.idea', '.hvigor', 'node_modules', 'oh_modules',
  'dist', 'build', 'out', 'coverage', '.rnohmulti'
]);
const sourceExtensions = new Set([
  '.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.ets',
  '.h', '.hpp', '.c', '.cc', '.cpp', '.json', '.json5'
]);

const rnSignals = [
  /from\s+["']react-native["']/,
  /require\(\s*["']react-native["']\s*\)/,
  /from\s+["'][^"']*(?:react_native_(?:adaptive_layout|breakpoints|avoid_area)|react-native-orientation)[^"']*["']/i,
  /\b(?:useWindowDimensions|Dimensions|StyleSheet|NavigationContainer|FlatList)\b/
];
const hostSignals = [
  /\b(?:RNApp|RNInstance|RNSurface|RNInstancesCoordinator|RNOHCoreContext|RNOHContext)\b/,
  /\bonWindowSizeChange\b/,
  /from\s+["'][^"']*(?:rnoh|react-native-harmony)[^"']*["']/i
];
const nativeSignals = [
  /\b(?:TurboModule|TurboModulesFactory|RNOHPackage|BaseView|ComponentJSIBinder|Fabric)\b/,
  /\b(?:codegenNativeComponent|TurboModuleRegistry|NativeModules)\b/,
  /\b(?:Surface|XComponent|PointerEvent)\b/
];
const harmonyPath = /(^|[\\/])(?:entry|features?|har|harmony)[\\/].*?[\\/]src[\\/]main[\\/]/i;

const rules = [
  {
    id: 'physical-screen-layout',
    severity: 'high',
    layers: ['rn'],
    pattern: /Dimensions\.get\(\s*["']screen["']\s*\)/,
    message: '物理 screen 不能表达分屏/自由窗的应用窗口；普通布局应读取当前 window。'
  },
  {
    id: 'module-window-cache',
    severity: 'high',
    layers: ['rn'],
    pattern: /^(?:export\s+)?const\s+[A-Z][A-Z0-9_]*\s*=\s*Dimensions\.get\(\s*["']window["']\s*\)(?:\.(?:width|height))?/m,
    message: '发现模块级窗口常量；检查它是否在启动后永久缓存并驱动布局。'
  },
  {
    id: 'module-window-destructure',
    severity: 'high',
    layers: ['rn'],
    pattern: /^(?:export\s+)?(?:const|let|var)\s*\{[^}\n]*\b(?:width|height|fontScale|scale)\b[^}\n]*\}\s*=\s*Dimensions\.get\(\s*["']window["']\s*\)/m,
    message: '发现模块级解构 window metrics；折展后依赖值和静态 StyleSheet 不会自动重新求值。'
  },
  {
    id: 'module-derived-metrics',
    severity: 'high',
    layers: ['rn'],
    pattern: /^(?:export\s+)?(?:const|let|var)\s+(?:rem|rpx|layoutScale|screenScale|screenWidth|windowWidth|deviceWidth|[A-Za-z_$][\w$]*(?:Rem|REM|Rpx|Scale|Ratio|Unit))\s*=\s*[^;\n]{0,180}(?:Dimensions\.get|screenWidth|windowWidth|deviceWidth)[^;\n]*/m,
    message: '发现模块级 rem/scale/设计单位派生；应由最新 application window 响应式计算并触发消费者 render。'
  },
  {
    id: 'static-responsive-styles',
    severity: 'medium',
    layers: ['rn'],
    pattern: /StyleSheet\.create\(\s*\{[\s\S]{0,2600}\b(?:rem|rpx|normalize|wp|hp|moderateScale|responsive(?:Screen)?(?:Width|Height|FontSize))\s*\(/i,
    message: '静态 StyleSheet 中发现响应式尺寸函数；核对该函数是否会随折展重算，非 hook 求值通常会固化启动尺寸。'
  },
  {
    id: 'static-stylesheet-window',
    severity: 'high',
    layers: ['rn'],
    pattern: /StyleSheet\.create\(\s*\{[\s\S]{0,2600}Dimensions\.get\(\s*["'](?:window|screen)["']\s*\)/i,
    message: '静态 StyleSheet 直接读取 Dimensions；窗口变化不会重新执行模块初始化，应把动态几何移到响应式 render/memo。'
  },
  {
    id: 'image-percent-aspect-ratio',
    severity: 'medium',
    layers: ['rn'],
    pattern: /<Image\b[^>]{0,600}\bstyle\s*=\s*\{\s*\{(?=[^}]{0,500}\bwidth\s*:\s*["']100%["'])(?=[^}]{0,500}\baspectRatio\s*:)[^}]*\}\s*\}/i,
    message: 'Image 同时依赖百分比宽度与 aspectRatio；在目标 RNOH 版本验证 intrinsic size、父约束和裁剪，必要时由外层容器持有比例、Image 填满容器。'
  },
  {
    id: 'flatlist-dynamic-columns-without-key',
    severity: 'medium',
    layers: ['rn'],
    pattern: /<FlatList\b[\s\S]{0,1800}\bnumColumns\s*=\s*\{\s*(?!\d+\s*\})[^}]+\}/i,
    requiresMissing: /<FlatList\b[\s\S]{0,1800}\bkey\s*=\s*\{[^}]+\}/i,
    message: 'FlatList 的 numColumns 是动态值但未见列表层 key；在锁定 RNOH 版本验证是否需要仅重挂列表呈现层，并保持业务锚点/状态在外部。'
  },
  {
    id: 'list-window-geometry-audit',
    severity: 'medium',
    layers: ['rn'],
    pattern: /(?:getItemLayout|snapToInterval|initialScrollIndex)[\s\S]{0,700}Dimensions\.get\(\s*["'](?:window|screen)["']\s*\)|Dimensions\.get\(\s*["'](?:window|screen)["']\s*\)[\s\S]{0,700}(?:getItemLayout|snapToInterval|initialScrollIndex)/i,
    message: '列表测量/滚动几何与 Dimensions 读取耦合；确认它随当前 window/columns 重算而非缓存启动值，并同步更新可见锚点。'
  },
  {
    id: 'scrollview-fixed-viewport-height',
    severity: 'medium',
    layers: ['rn'],
    pattern: /<ScrollView\b[^>]{0,700}\b(?:style|contentContainerStyle)\s*=\s*\{\s*\{[^}]{0,500}(?:height\s*:\s*(?:[4-9]\d{2}|[1-9]\d{3,})\b|Dimensions\.get\(\s*["']screen["']\s*\)\.height)/i,
    message: 'ScrollView 附近发现固定大高度或物理屏高；应由有界父链提供 viewport，并区分 style 与 contentContainerStyle。'
  },
  {
    id: 'empty-memo-responsive-capture',
    severity: 'medium',
    layers: ['rn'],
    pattern: /use(?:Memo|Callback)\(\s*[\s\S]{0,800}(?:StyleSheet\.create|\brem\s*\(|\brpx\s*\(|\bnormalize\s*\(|\b(?:width|height|breakpoint|layoutScale)\b)[\s\S]{0,240},\s*\[\s*\]\s*\)/i,
    message: '空依赖 memo/callback 可能捕获启动时 width、breakpoint 或 rem；核对依赖与列表 renderItem/getItemLayout。'
  },
  {
    id: 'global-scale-mutation',
    severity: 'medium',
    layers: ['rn'],
    pattern: /Dimensions\.addEventListener\(\s*["']change["'][\s\S]{0,1000}\b(?:rem|rpx|layoutScale|screenScale)\s*=/i,
    message: 'Dimensions 回调只修改全局 scale/rem 不会自动触发 React render；需要 state、hook 或可订阅 Context。'
  },
  {
    id: 'fontscale-drives-layout',
    severity: 'high',
    layers: ['rn'],
    pattern: /(?:width|height|minWidth|maxWidth|minHeight|maxHeight|margin|padding|gap|flexBasis)\s*:\s*[^,}\n]{0,120}\bfontScale\b/i,
    message: 'fontScale 正在驱动非文字布局；它表示用户文字偏好，不是页面 rem 或窗口比例。'
  },
  {
    id: 'double-font-scaling',
    severity: 'medium',
    layers: ['rn'],
    pattern: /fontSize\s*:\s*[^,}\n]{0,120}\bfontScale\b/i,
    message: 'fontSize 显式乘 fontScale 可能与 Text 默认系统缩放叠加；检查是否发生双重缩放。'
  },
  {
    id: 'global-disable-font-scaling',
    severity: 'medium',
    layers: ['rn'],
    pattern: /(?:Text|TextInput)\.defaultProps[\s\S]{0,300}allowFontScaling\s*=\s*false/i,
    message: '发现全局关闭字体缩放；不要用它掩盖容器、派生单位或版本型文本测量问题。'
  },
  {
    id: 'module-animation-dimension',
    severity: 'high',
    layers: ['rn'],
    pattern: /^(?:export\s+)?(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*new\s+Animated\.Value\([^;\n]{0,240}Dimensions\.get\(\s*["'](?:window|screen)["']/m,
    message: '发现模块级 Animated.Value 使用启动窗口；折展或自由窗变化后动画端点可能陈旧。'
  },
  {
    id: 'native-driver-layout-property',
    severity: 'medium',
    layers: ['rn'],
    pattern: /(?:width|height|top|right|bottom|left|flexBasis)\s*:\s*[A-Za-z_$][\w$.]*[\s\S]{0,1200}useNativeDriver\s*:\s*true/i,
    message: '同一区域发现动画布局属性与 Native Driver；Native Driver 不支持宽高/Flexbox/position，需核对实际 animated style。'
  },
  {
    id: 'absolute-physical-horizontal-edge',
    severity: 'medium',
    layers: ['rn'],
    pattern: /(?:position\s*:\s*["']absolute["'][\s\S]{0,320}\b(?:left|right)\s*:|\b(?:left|right)\s*:[\s\S]{0,320}position\s*:\s*["']absolute["'])/i,
    message: '绝对定位使用物理 left/right；确认它是物理边语义，否则需审计 RTL、resize 和动画方向。'
  },
  {
    id: 'builtin-safe-area-view',
    severity: 'medium',
    layers: ['rn'],
    pattern: /import\s*\{[^}]*\bSafeAreaView\b[^}]*\}\s*from\s*["']react-native["']/,
    message: '使用 RN 内置 SafeAreaView；上游已废弃，RNOH 项目应按锁定版本核对 safe-area-context 或现有平台方案。'
  },
  {
    id: 'device-type-layout',
    severity: 'medium',
    layers: ['rn'],
    pattern: /\bPlatform\.(?:isPad|isTV)\b/,
    message: '设备类型不能替代当前应用窗口；仅允许用于经验证的能力或资源默认值。'
  },
  {
    id: 'pixel-ratio-layout',
    severity: 'medium',
    layers: ['rn'],
    pattern: /(?:width|height|fontSize|margin|padding)\s*:\s*[^,}\n]{0,80}PixelRatio\.(?:get|getPixelSizeForLayoutSize)\s*\(/,
    message: 'PixelRatio 可能正在缩放布局盒或字体；确认它只用于资源像素或明确的单位转换。'
  },
  {
    id: 'root-remount-on-size',
    severity: 'high',
    layers: ['rn'],
    pattern: /<(?:NavigationContainer|Provider|[A-Za-z_$][\w$]*(?:Root|App))\b[^>]*\bkey\s*=\s*\{[^}]*(?:width|height|breakpoint|orientation|posture)[^}]*\}/i,
    message: '发现根/导航/Provider 随尺寸 key 重挂；这会丢失 route、表单和业务状态。'
  },
  {
    id: 'native-remount-on-size',
    severity: 'high',
    layers: ['rn'],
    pattern: /<[A-Za-z_$][\w$.]*(?:Video|Map|Surface|Native)[\w$.]*\b[^>]*\bkey\s*=\s*\{[^}]*(?:width|height|breakpoint|orientation|posture)[^}]*\}/i,
    message: '原生组件似乎随窗口 key 重建；优先消费布局提交并保持业务状态。'
  },
  {
    id: 'dimensions-listener-without-remove',
    severity: 'medium',
    layers: ['rn'],
    pattern: /Dimensions\.addEventListener\(\s*["']change["']/,
    requiresMissing: /(?:subscription|listener|dimensionsSubscription)[\s\S]{0,800}\.remove\s*\(|\.remove\s*\(\s*\)/i,
    message: '发现 Dimensions 订阅但同文件未见 remove；确认 subscription owner 与卸载清理。'
  },
  {
    id: 'rnoh-adaptive-deep-import',
    severity: 'medium',
    layers: ['rn'],
    pattern: /(?:from\s*|require\(\s*)["']@hadss\/react_native_(?:adaptive_layout|breakpoints|avoid_area)\/src(?:\/[^"']*)?["']/,
    message: '发现官方社区多设备包的 src 深路径 import；按 RN-13 核对实际 public exports、锁定版本和迁移风险，不从旧 README 固化内部路径。'
  },
  {
    id: 'avoid-area-page-listener',
    severity: 'medium',
    layers: ['rn'],
    pattern: /\bAvoid\.addAvoidAreaListener\s*\(/,
    message: '发现页面直接注册 avoid-area listener；审计版本为模块级单 subscription，应由应用级唯一 provider 持有、换算单位并向多消费者分发。'
  },
  {
    id: 'avoid-listener-without-remove',
    severity: 'high',
    layers: ['rn'],
    pattern: /\bAvoid\.addAvoidAreaListener\s*\(/,
    requiresMissing: /\bAvoid\.removeAvoidAreaListener\s*\(/,
    message: '发现 Avoid 订阅但同文件未见 remove；确认唯一 owner 在卸载时幂等清理，并保留注册时的回调/订阅引用。'
  },
  {
    id: 'avoid-area-without-unit-boundary',
    severity: 'medium',
    layers: ['rn'],
    pattern: /\bAvoid\.getWindowAvoidArea\s*\(/,
    requiresMissing: /\b(?:PixelRatio\.get|pxToVp|px2vp|convertPixelToVp|toLayoutUnit)\s*\(/i,
    message: '读取 Avoid 区域但未见单位转换边界；返回单位随包/版本核验，进入 RN style 前只转换一次并记录证据。'
  },
  {
    id: 'duplicate-keyboard-avoidance-owner',
    severity: 'high',
    layers: ['rn'],
    pattern: /(?:KeyboardAvoidingView[\s\S]{0,2400}(?:AvoidAreaType\.)?TYPE_KEYBOARD|(?:AvoidAreaType\.)?TYPE_KEYBOARD[\s\S]{0,2400}KeyboardAvoidingView)/i,
    message: '同文件同时出现 KeyboardAvoidingView 与 Avoid TYPE_KEYBOARD；核对 Host resize、Sheet 和输入页，仅保留一个键盘避让 owner。'
  },
  {
    id: 'fold-page-listener',
    severity: 'medium',
    layers: ['rn'],
    pattern: /\bFold\.(?:addFoldListener|removeFoldListener)\s*\(/,
    message: '发现页面直接管理 Fold listener；确认是否确需半折/折痕，并验证多消费者、同引用释放、方向副作用和 px→RN layout unit。'
  },
  {
    id: 'fold-listener-without-initial-snapshot',
    severity: 'high',
    layers: ['rn'],
    pattern: /\bFold\.addFoldListener\s*\(/,
    requiresMissing: /\bFold\.getFoldStatus\s*\(/,
    message: 'Fold 只订阅变化但未读取初始快照；冷启动可能停留在默认姿态，应按锁定 API 先订阅再取快照并处理时序。'
  },
  {
    id: 'fold-listener-without-remove',
    severity: 'high',
    layers: ['rn'],
    pattern: /\bFold\.addFoldListener\s*\(/,
    requiresMissing: /\bFold\.removeFoldListener\s*\(/,
    message: '发现 Fold 订阅但同文件未见 remove；确认唯一 provider 持有相同 callback/subscription，并在最后消费者释放时清理。'
  },
  {
    id: 'fold-status-numeric-comparison',
    severity: 'high',
    layers: ['rn'],
    pattern: /(?:foldStatus|foldState|posture)\s*={2,3}\s*\d+|\d+\s*={2,3}\s*(?:foldStatus|foldState|posture)/i,
    message: '折叠状态正在与裸数字比较；实际 enum 形态依赖锁定包版本，应使用导出 enum/适配器归一化，禁止字符串与数字跨类型直比。'
  },
  {
    id: 'orientation-listener-without-remove',
    severity: 'high',
    layers: ['rn'],
    pattern: /\bOrientation\.add(?:Orientation|DeviceOrientation)Listener\s*\(/,
    requiresMissing: /\bOrientation\.remove(?:Orientation|DeviceOrientation)Listener\s*\(/,
    message: '发现方向订阅但同文件未见成对 remove；保留同一 handler 引用并在 owner 卸载时清理。'
  },
  {
    id: 'orientation-lock-without-restore',
    severity: 'medium',
    layers: ['rn'],
    pattern: /\b(?:Orientation\.(?:lockToPortrait|lockToLandscape)|setPreferredOrientation)\s*\(/,
    requiresMissing: /\b(?:Orientation\.unlockAllOrientations|restorePreferredOrientation|setPreferredOrientation\s*\([^)]*(?:UNSPECIFIED|AUTO|FOLLOW|USER_ROTATION))/i,
    message: '发现运行时方向锁定但同文件未见恢复路径；页面退出/模式变化时恢复先前策略，不能把 lockToPortrait 当通用 cleanup。'
  },
  {
    id: 'fixed-large-dimension',
    severity: 'medium',
    layers: ['rn'],
    pattern: /\b(?:width|minWidth|height|minHeight)\s*:\s*(?:[4-9]\d{2}|[1-9]\d{3,})\b/,
    message: '发现较大固定尺寸；检查最窄窗口、大字体和滚动路径。'
  },
  {
    id: 'display-size-to-host',
    severity: 'high',
    layers: ['host', 'native'],
    pattern: /(?:getDefaultDisplaySync|getAllDisplays|getDefaultDisplay)\s*\([^)]*\)[\s\S]{0,500}(?:RNInstance|RNSurface|Coordinator|onWindowSizeChange)/i,
    message: '疑似把物理 display 尺寸传给 RNOH；应确认使用 owning application window。'
  },
  {
    id: 'manual-generated-edit-risk',
    severity: 'medium',
    layers: ['native'],
    pathPattern: /(?:^|[\\/])(?:generated|codegen|build[\\/]generated)(?:[\\/]|$)/i,
    pattern: /./,
    firstOnly: true,
    message: '扫描到生成目录源码；不要把适配修改落在 Codegen 生成物。'
  }
];

const warnings = [];

function collectFiles(entry, files = []) {
  if ([scannerPath, scannerTestPath].includes(path.resolve(entry))) return files;
  let stat;
  try {
    stat = fs.lstatSync(entry);
  } catch (error) {
    warnings.push(`无法读取 ${entry}: ${error.message}`);
    return files;
  }

  if (stat.isSymbolicLink()) return files;
  if (stat.isFile()) {
    if (sourceExtensions.has(path.extname(entry).toLowerCase())) files.push(entry);
    return files;
  }
  if (!stat.isDirectory()) return files;

  let names;
  try {
    names = fs.readdirSync(entry);
  } catch (error) {
    warnings.push(`无法遍历 ${entry}: ${error.message}`);
    return files;
  }
  for (const name of names) {
    if (!ignored.has(name)) collectFiles(path.join(entry, name), files);
  }
  return files;
}

function classify(file, source) {
  const extension = path.extname(file).toLowerCase();
  const layers = new Set();
  if (rnSignals.some((pattern) => pattern.test(source))) layers.add('rn');
  if ((extension === '.ets' || harmonyPath.test(file)) && hostSignals.some((pattern) => pattern.test(source))) {
    layers.add('host');
  }
  if (nativeSignals.some((pattern) => pattern.test(source))) layers.add('native');
  if (['.h', '.hpp', '.c', '.cc', '.cpp'].includes(extension)) layers.add('native');
  return layers;
}

function readRecord(file) {
  try {
    const source = fs.readFileSync(file, 'utf8');
    return { file, source, layers: classify(file, source) };
  } catch (error) {
    warnings.push(`无法读取 ${file}: ${error.message}`);
    return null;
  }
}

function lineAt(source, index) {
  return source.slice(0, index).split('\n').length;
}

function matches(source, pattern) {
  const flags = pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`;
  return [...source.matchAll(new RegExp(pattern.source, flags))];
}

if (!fs.existsSync(target)) {
  console.error(`Target does not exist: ${target}`);
  process.exit(2);
}

const records = collectFiles(target).map(readRecord).filter(Boolean);
const counts = { rn: 0, host: 0, native: 0 };
for (const record of records) {
  for (const layer of record.layers) counts[layer] += 1;
}
const activeLayers = Object.entries(counts).filter(([, count]) => count > 0).map(([layer]) => layer);
const inputMode = activeLayers.length > 1
  ? 'HYBRID'
  : activeLayers[0] === 'rn'
    ? 'RN_ONLY'
    : activeLayers[0] === 'host'
      ? 'HOST_ONLY'
      : activeLayers[0] === 'native'
        ? 'NATIVE_ONLY'
        : 'INSUFFICIENT';

console.log(`Input mode candidate: ${inputMode} (RN: ${counts.rn}, Host: ${counts.host}, Native: ${counts.native})`);
console.log('Confirm this candidate with lockfiles, project structure, imports, registration, and the actual call chain.');

const findings = [];
const findingKeys = new Set();
for (const record of records) {
  for (const rule of rules) {
    if (!rule.layers.some((layer) => record.layers.has(layer))) continue;
    if (rule.pathPattern && !rule.pathPattern.test(record.file)) continue;
    if (rule.requiresMissing?.test(record.source)) continue;
    const ruleMatches = matches(record.source, rule.pattern);
    for (const match of rule.firstOnly ? ruleMatches.slice(0, 1) : ruleMatches) {
      const line = lineAt(record.source, match.index);
      const key = `${rule.id}:${record.file}:${line}`;
      if (findingKeys.has(key)) continue;
      findingKeys.add(key);
      findings.push({
        id: rule.id,
        severity: rule.severity,
        message: rule.message,
        file: path.relative(process.cwd(), record.file),
        line
      });
    }
  }
}

for (const finding of findings) {
  console.log(`${finding.severity.toUpperCase()} ${finding.id} ${finding.file}:${finding.line}`);
  console.log(`  ${finding.message}`);
}
for (const warning of warnings) console.warn(`WARN ${warning}`);

console.log(`Scanned ${records.length} relevant file(s); found ${findings.length} RNOH adaptation risk(s).`);
process.exit(findings.some(({ severity }) => severity === 'high') ? 1 : 0);
