# 动态 REM 与 viewport 变化

## 何时使用

页面通过 JavaScript 写入 `html` 根字号，且折叠、展开、旋转、分屏或窗口缩放后出现以下任一现象时使用本文件：

- 外屏启动字体较小，展开后仍沿用小字号。
- 内屏启动字体较大，折叠后仍沿用大字号并造成截断。
- 刷新或重新加载后恢复正常。
- `document.documentElement.clientWidth` 已变化，但 computed root `font-size` 未变化。

如果项目只是在 CSS 中使用固定 `rem`，没有任何动态根字号生成器，不要新增一套 REM 脚本；改查 CSS 断点、组件约束和浏览器默认根字号。

## 决策原则

`1rem` 始终等于当前根节点的 computed `font-size`。根字号被正确修改后，浏览器会自动重新计算所有 REM 长度；问题通常不在 REM 生效机制，而在根字号生成器没有再次运行或使用了旧 viewport。

修复时遵守以下约束：

1. 先找出原公式、设计稿基准、最小/最大缩放策略和所有根字号写入者；不得凭目标设备型号重新设计比例。
2. 使用 layout viewport 宽度，即 `document.documentElement.clientWidth`，必要时回退到 `window.innerWidth`；不得用 `screen.width` 或设备折叠状态计算 REM。
3. 折叠和旋转首先是尺寸变化。`H5_ONLY` 优先监听 Web 标准尺寸信号；已有原生通知或实测标准事件漏发时，按 `references/arkts-h5-coordination.md` 汇聚信号，但 H5 仍读取自身 viewport 计算 REM。
4. 根字号同步必须幂等，只在有效宽度变化后写入；高频事件合并到动画帧。
5. 修改源文件而不是构建生成的压缩 bundle；若只能看到 bundle，先通过 sourcemap、入口引用或搜索特征定位源实现。

## 审计顺序

1. 确认 viewport 声明包含 `width=device-width, initial-scale=1`。`viewport-fit=cover` 只影响安全区，不负责重算 REM。
2. 搜索 `documentElement.style.fontSize`、`setProperty('font-size')`、`flexible`、`remUnit`、`clientWidth /`、`/ 10` 和 PostCSS REM 配置。
3. 在窄屏首次加载时记录 `clientWidth`、`clientHeight`、computed root `font-size` 和公式输出。
4. 完成外屏→内屏、内屏→外屏、竖屏→横屏后再次记录。如果宽度变而根字号不变，继续检查事件与守卫；如果根字号已变而布局仍错，转查固定尺寸、断点或多个写入者。
5. 临时给根字号写入点加调用计数和输入输出日志，确认是未调用、使用旧尺寸，还是写入后又被覆盖。

```javascript
console.table({
  innerWidth: window.innerWidth,
  innerHeight: window.innerHeight,
  clientWidth: document.documentElement.clientWidth,
  clientHeight: document.documentElement.clientHeight,
  rootFontSize: getComputedStyle(document.documentElement).fontSize
});
```

## 高频错误模式

### 把调用结果注册成监听器

```javascript
// ❌ 初始化时立即执行；普通 refreshRem 返回 undefined，resize 时不会调用。
window.addEventListener('resize', refreshRem());

// ✅ 初始化与监听分开。
refreshRem();
window.addEventListener('resize', refreshRem);
```

只有当 `refreshRem()` 明确返回另一个函数时，第一种写法才成立。审计压缩代码时不要仅凭括号断言，检查返回值。

### 用初始高度阻止重算

```javascript
const initialHeight = document.documentElement.clientHeight;

function refreshRem() {
  const height = document.documentElement.clientHeight;
  // ❌ 折叠和旋转通常改变高度，整个更新被短路。
  initialHeight === height && updateRootFontSize();
}
```

这类守卫通常用于规避软键盘导致的纯高度变化，但同时误伤折叠和旋转。根字号按宽度计算时，直接比较当前宽度与上次已应用宽度。

### 缓存启动尺寸或使用物理屏幕

不要在模块加载时永久缓存 `clientWidth`，也不要切换到 `screen.width`。每次同步都重新读取 layout viewport；是否写入由上次已应用宽度决定。

### 多个写入者互相覆盖

检查入口脚本、UI 库、页面组件和第三方 flexible 脚本是否都在写根字号。保留一个权威写入者；否则事件顺序不同会让最终字号依赖启动路径。

### 依赖 `orientationchange`、折叠状态或 reload

- `orientationchange` 不能覆盖分屏、自由窗口和所有折叠尺寸变化。
- 折叠状态不能表达 H5 实际可用宽度，同一状态下窗口仍可能变化。
- `reload()` 只是重新执行首次初始化，会丢失滚动、表单、弹层和请求状态，不能作为正式适配。

## 修复模板

先把示例中的 `calculateRootFontSize` 替换为项目原公式。示例只负责正确调度，不规定设计比例。

```typescript
const root = document.documentElement;
let appliedWidth = -1;
let frameId = 0;

function calculateRootFontSize(width: number): number {
  // 示例：若原项目为 width / 10 且宽屏上限为 375px，则保持该语义。
  const effectiveWidth = Math.min(width, 375);
  return effectiveWidth / 10;
}

function refreshRem(): void {
  frameId = 0;
  const width = root.clientWidth || window.innerWidth;
  if (!Number.isFinite(width) || width <= 0 || width === appliedWidth) return;

  appliedWidth = width;
  root.style.fontSize = `${calculateRootFontSize(width)}px`;
}

function scheduleRemRefresh(): void {
  if (frameId) cancelAnimationFrame(frameId);
  frameId = requestAnimationFrame(refreshRem);
}

refreshRem();
window.addEventListener('resize', scheduleRemRefresh, { passive: true });

function handlePageShow(event: PageTransitionEvent): void {
  if (!event.persisted) return;
  appliedWidth = -1;
  scheduleRemRefresh();
}
window.addEventListener('pageshow', handlePageShow);

// SPA 页面真正卸载该基础设施时执行：
// window.removeEventListener('resize', scheduleRemRefresh);
// window.removeEventListener('pageshow', handlePageShow);
// if (frameId) cancelAnimationFrame(frameId);
```

如果目标 Web 内核实测存在 layout viewport 改变但 `window.resize` 漏发，可在 H5 内增加 `ResizeObserver` 作为能力回退；两个信号调用同一个幂等调度函数，不创建两套公式：

```typescript
const viewportObserver = new ResizeObserver(scheduleRemRefresh);
viewportObserver.observe(document.documentElement);
// 卸载时：viewportObserver.disconnect();
```

仅在能力检测确认 `ResizeObserver` 可用时启用。`VisualViewport.resize` 主要服务缩放、键盘和视觉视口，不应替代 layout viewport 作为 REM 计算输入。

如果项目已由 ArkTS 发送 `onScreenChange` 等事件，H5 消费回调调用同一个 `scheduleRemRefresh`。不要直接把原生 dp 宽度写成根字号；事件可能早于 Web viewport 稳定，调度到动画帧后重新读取 `root.clientWidth`。两端源码都提供时命中 `H5-08`，同步验证事件契约和首次状态。

## 原公式如何保留

| 原有策略 | 修复时保持的语义 | 风险检查 |
| --- | --- | --- |
| `width / 10` | 每次使用最新 layout viewport 宽度 | 展开宽屏是否导致字体和间距过度放大 |
| `min(width, designWidth) / 10` | 宽屏保持设计上限，窄屏连续缩放 | 上限是否确为项目既有设计决策 |
| `width / designWidth * baseSize` | 保留 `designWidth` 与 `baseSize` | 两个常量是否被其他构建配置共享 |
| 分段/断点公式 | 保留断点语义并统一所有调用入口 | 临界值前后是否跳变或被 CSS 覆盖 |

如果无法从源码、历史样式或构建配置确认公式，不要猜测。先报告已有计算和视觉基线，再请求开发者确认设计基准。

## 验证矩阵

每条路径都记录最终 `clientWidth`、computed root `font-size`、调用次数和页面状态：

- 外屏启动 → 展开内屏。
- 内屏启动 → 折叠外屏。
- 内屏竖屏 ↔ 内屏横屏。
- 快速连续折叠、展开和旋转。
- 分屏进入、调整和退出。
- 输入框聚焦与软键盘开合：纯高度变化不得无故改变按宽度计算的根字号。
- 返回缓存页面（`pageshow.persisted`）与 SPA 重挂：监听不重复，最终尺寸正确。

通过条件：相同最终 viewport 得到相同根字号，与启动形态和操作顺序无关；无需 reload，滚动、表单和业务状态不丢失；直板机原始宽度的 computed root `font-size` 与修改前一致。
