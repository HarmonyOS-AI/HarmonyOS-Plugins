#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const target = path.resolve(process.argv[2] ?? '.');
const scannerPath = path.resolve(process.argv[1]);
const webExtensions = new Set([
  '.html', '.htm', '.css', '.scss', '.less', '.js', '.mjs', '.cjs',
  '.ts', '.tsx', '.jsx', '.vue', '.svelte'
]);
const ignored = new Set([
  '.git', '.hg', '.idea', '.hvigor', 'node_modules', 'oh_modules',
  'dist', 'build', 'out', 'coverage'
]);

const rules = [
  { id: 'layout-by-ua', severity: 'high', pattern: /navigator\.userAgent|userAgent\b/i, message: 'UA 检测不应作为布局开关；优先使用 viewport、容器尺寸或能力检测。' },
  { id: 'physical-screen-size', severity: 'medium', pattern: /\bscreen\.(width|height|availWidth|availHeight)\b/, message: '物理屏幕尺寸通常不等于页面当前窗口；检查是否应使用 viewport 或组件容器尺寸。' },
  { id: 'fixed-viewport-height', severity: 'medium', pattern: /\bheight\s*:\s*100vh\b/i, message: '固定 height: 100vh 可能与动态视口、软键盘或内容增长冲突；检查滚动策略及 100dvh 渐进增强。' },
  { id: 'global-min-width', severity: 'high', pattern: /\b(body|html|#app|#root)\s*[^{}]*\{[^{}]*\bmin-width\s*:\s*\d{3,}px/is, message: '页面根节点固定最小宽度可能导致窄窗口横向滚动。' },
  { id: 'hide-horizontal-overflow', severity: 'medium', pattern: /overflow-x\s*:\s*hidden/i, message: '隐藏横向溢出可能掩盖真实越界元素；先定位首个溢出节点。' },
  { id: 'viewport-disables-zoom', severity: 'high', pattern: /<meta\b(?=[^>]*\bname\s*=\s*["']viewport["'])(?=[^>]*(?:user-scalable\s*=\s*no|maximum-scale\s*=\s*1))[^>]*>/i, message: '不要禁用用户缩放；这会损害可访问性。' },
  { id: 'resize-listener-invoked', severity: 'high', pattern: /addEventListener\(\s*["']resize["']\s*,\s*[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*\([^)]*\)\s*[,)]/, message: 'resize 监听器看起来传入了函数调用结果；确认该调用是否返回函数，否则应传函数引用。' },
  { id: 'initial-height-gates-resize', severity: 'medium', pattern: /(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*[^;\n]{0,100}\.clientHeight\s*;?[\s\S]{0,600}\b[A-Za-z_$][\w$]*\s*===\s*\1\s*&&/, message: '发现用启动时 clientHeight 相等条件守卫后续更新；折叠和旋转会改变高度，检查它是否错误阻止 REM 重算。' },
  { id: 'rem-without-resize-sync', severity: 'medium', pattern: /(?:documentElement|\bhtml\b|\broot\b)[\s\S]{0,1500}(?:style\.fontSize|style\.setProperty\(\s*["']font-size)/i, requiresMissing: /addEventListener\(\s*["']resize["']/i, message: '发现动态根字号写入但同文件没有 resize 同步；检查 REM 是否只在页面启动时计算。' },
  { id: 'viewport-scaled-root-font', severity: 'medium', pattern: /(?:clientWidth|innerWidth|getBoundingClientRect\(\)\.width)[\s\S]{0,1200}(?:style\.fontSize|style\.setProperty\(\s*["']font-size)/i, message: '发现 viewport 驱动的动态根字号；核对设计宽度、构建 rootValue、缩放上限和生成 CSS，并确认上限之后由响应式布局接管。' },
  { id: 'pxtorem-all-properties', severity: 'medium', pattern: /propList\s*:\s*\[\s*["']\*["']\s*\]/i, message: 'px→rem 配置会转换全部属性；检查字体、细边框、结构性 max-width 和稳定尺寸是否不应与动态根字号一起缩放。' },
  { id: 'pxtorem-media-query-conversion', severity: 'medium', pattern: /mediaQuery\s*:\s*true\b/i, message: 'px→rem 配置会转换媒体查询；必须核对生成 CSS 中断点是否仍表达预期的 viewport 阈值。' },
  { id: 'reload-on-resize', severity: 'high', pattern: /addEventListener\(\s*["']resize["'][\s\S]{0,240}(?:location\.)?reload\s*\(/i, message: '发现 resize 后整页 reload；这会丢失页面状态，应修复实际布局或根字号同步。' },
  { id: 'srcset-w-without-sizes', severity: 'medium', pattern: /<img\b(?=[^>]*\bsrcset\s*=\s*["'][^"']*\b\d+w\b)(?![^>]*\bsizes\s*=)[^>]*>/i, message: '发现使用 w 描述符的 srcset 但同一 img 没有 sizes；浏览器可能按 100vw 估算 slot 并选择过大资源。' },
  { id: 'picture-without-img-fallback', severity: 'high', pattern: /<picture\b(?:(?!<img\b|<\/picture>)[\s\S])*<\/picture>/i, message: 'picture 内缺少 img 回退；补齐默认 src、尺寸和可访问文本。' }
];

const arktsPathPattern = /(^|[\\/])src[\\/]main[\\/]ets([\\/]|$)/i;
const arktsSourcePatterns = [
  /from\s+["']@(?:kit|ohos)\.[^"']+["']/,
  /(?:^|\n)\s*@(?:Entry|Component|Observed|Reusable)\b/m,
  /(?:^|\n)\s*struct\s+[A-Za-z_$][\w$]*\s*\{/m,
  /\bUIAbility\b|\bWebviewController\b|\bwebview\.WebviewController\b/
];

const warnings = [];

function collectFiles(entry, files = []) {
  if (path.resolve(entry) === scannerPath) return files;
  let stat;
  try {
    stat = fs.lstatSync(entry);
  } catch (error) {
    warnings.push(`无法读取 ${entry}: ${error.message}`);
    return files;
  }

  if (stat.isSymbolicLink()) return files;
  if (stat.isFile()) {
    const extension = path.extname(entry).toLowerCase();
    if (extension === '.ets' || webExtensions.has(extension)) files.push(entry);
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

function readRecord(file) {
  let source;
  try {
    source = fs.readFileSync(file, 'utf8');
  } catch (error) {
    warnings.push(`无法读取 ${file}: ${error.message}`);
    return null;
  }

  const extension = path.extname(file).toLowerCase();
  const arkts = extension === '.ets'
    || (extension === '.ts' && (
      arktsPathPattern.test(file) || arktsSourcePatterns.some((pattern) => pattern.test(source))
    ));
  return { file, source, layer: arkts ? 'arkts' : 'web' };
}

function lineAt(source, index) {
  return source.slice(0, index).split('\n').length;
}

function findMatches(source, pattern) {
  const flags = pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`;
  return [...source.matchAll(new RegExp(pattern.source, flags))];
}

if (!fs.existsSync(target)) {
  console.error(`Target does not exist: ${target}`);
  process.exit(2);
}

const records = collectFiles(target).map(readRecord).filter(Boolean);
const webRecords = records.filter(({ layer }) => layer === 'web');
const arktsRecords = records.filter(({ layer }) => layer === 'arkts');
const inputMode = webRecords.length && arktsRecords.length
  ? 'HYBRID'
  : webRecords.length
    ? 'H5_ONLY'
    : arktsRecords.length
      ? 'ARKTS_ONLY'
      : 'INSUFFICIENT';

console.log(`Input mode candidate: ${inputMode} (H5: ${webRecords.length}, ArkTS: ${arktsRecords.length})`);
console.log('Confirm this candidate with project structure, imports, syntax, and the actual call chain.');

const findings = [];
const findingKeys = new Set();
for (const { file, source } of webRecords) {
  for (const rule of rules) {
    if (rule.requiresMissing?.test(source)) continue;
    for (const match of findMatches(source, rule.pattern)) {
      const line = lineAt(source, match.index);
      const key = `${rule.id}:${file}:${line}`;
      if (findingKeys.has(key)) continue;
      findingKeys.add(key);
      findings.push({
        file: path.relative(process.cwd(), file),
        line,
        ...rule
      });
    }
  }
}

for (const finding of findings) {
  console.log(`${finding.severity.toUpperCase()} ${finding.id} ${finding.file}:${finding.line}`);
  console.log(`  ${finding.message}`);
}
for (const warning of warnings) console.warn(`WARN ${warning}`);

console.log(`Scanned ${records.length} relevant file(s); found ${findings.length} H5 adaptation risk(s).`);
process.exit(findings.some(({ severity }) => severity === 'high') ? 1 : 0);
