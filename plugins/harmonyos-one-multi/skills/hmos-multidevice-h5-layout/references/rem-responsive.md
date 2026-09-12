# 动态 REM：存量兼容、缩放边界与宽屏接管

## 能力定位

动态 REM 是把移动设计稿尺寸映射到 CSS viewport 的存量兼容层，不是平板或折叠屏的完整响应式方案。它可以在有限区间内连续缩放，但宽度继续增加时，应由 Grid、Flex、media/container query 完成重复、挪移、缩进、分栏或信息密度变化，而不是继续整体放大字号、图片、间距和圆角。

页面没有 JavaScript 动态根字号生成器时，不新增一套 REM 脚本。新建多设备页面也默认保持浏览器根字号语义，按 `responsive-layout.md` 实现布局；只有现有构建产物已经依赖动态根字号时，才进入本文件的兼容、修复或渐进迁移流程。

## 先做策略门禁

先记录当前 viewport 宽度、computed root `font-size`、公式期望值和异常元素，再选择处理方向：

| 证据                                                           | 判断与动作                                           |
| -------------------------------------------------------------- | ---------------------------------------------------- |
| viewport 宽度变化，根字号未变化或刷新后才恢复                  | `H5-07` 为主场景，修复调度、守卫或多写入者           |
| 根字号变化且符合既定公式，但宽屏页面靠左、留白、单列或导航错位 | 根因是页面结构，改选 `H5-01/02`；不要提高 REM 上限   |
| 根字号变化，但持续放大造成文字过大、图片模糊或间距失衡         | 审计公式与缩放上限；上限之后让响应式布局接管         |
| 源码尺寸与运行时尺寸不一致                                     | 联查 px→rem 构建配置和生成 CSS，再决定公式或结构修改 |
| 只有固定 `rem`，没有动态写根字号                               | 使用浏览器根字号、断点和组件约束，不引入动态 REM     |

动态 REM 的上限是产品布局决策，不是设备参数。不得因为某台平板或折叠屏宽度更大，就把 `maxWidth` 调到接近该设备宽度。应连续改变容器尺寸，找出字号、触控目标、图片清晰度、行长、卡片密度或空间利用开始失衡的位置，再确定缩放停止点和宽屏布局开始点。

## 还原尺寸模型

先从源码和构建配置提取四个量：

- `D`：设计稿基准宽度，例如 `750` 设计像素。
- `R`：px→rem 的 `rootValue` 或 `remUnit`，例如 `75`。
- `V`：当前 layout viewport 的 CSS 像素宽度。
- `C`：经内容验证后的最大缩放宽度；没有证据时保持现状并报告待确认项。

常见有界公式是：

```text
rootFontSize(V) = min(V, C) × R / D
```

源码中的 `Npx` 经构建转换为 `N/R rem` 后，预期运行时尺寸为：

```text
runtimeSize(N, V) = N × min(V, C) / D CSS px
```

至少验证三个不变量：

1. 设计稿整宽 `Dpx` 在缩放区间应映射为当前 viewport 宽度。
2. 到达 `C` 后根字号和移动设计坐标停止增长。
3. 页面内容壳、fixed/sticky 导航和弹层在封顶后使用同一宽屏策略；不能只封顶 REM 而让容器继续通栏或靠左。

不要把源码 `px` 直接解释成运行时 CSS px。必须读取 PostCSS 插件、`rootValue/remUnit`、`propList`、`mediaQuery`、排除规则和实际生成 CSS。区分两类值：

- 设计稿尺寸可以按既有规则转换。
- 断点、真实内容上限、细边框和需要稳定语义的字体/触控尺寸，应确认构建后仍表达预期值；必要时使用项目插件的排除机制或放入不参与转换的样式层。

同时区分浏览器 `window.devicePixelRatio`、viewport `initial-scale` 和 flexible 库内部的 `dpr/scale` 变量。`initial-scale=1` 不能单独证明设备像素比为 `1`；REM 最终仍以 layout viewport 的 CSS 像素宽度计算。

还要验证用户缩放：某些环境放大页面后 layout viewport 会变窄，按 viewport 反向减小根字号可能抵消一部分放大效果。如果文字无法达到预期放大比例，应把字体从动态设计 REM 中拆出，或推进“渐进退出动态根字号”，不能把测试通过归因于页面没有溢出。

## 三种实施策略

### 1. 修复现有动态 REM

只在根字号没有按原公式更新时使用。保留已确认的 `D`、`R` 和 `C`，统一根字号写入者，并让更新只依赖最新 layout viewport。

下面的数字只是展示变量关系，落地时必须替换为项目已有且经验证的值：

```typescript
const root = document.documentElement;
const DESIGN_WIDTH = 750;
const BUILD_ROOT_VALUE = 75;
const SCALE_CAP = 540;

let appliedWidth = -1;
let frameId = 0;

function calculateRootFontSize(width: number): number {
	const effectiveWidth = Math.min(width, SCALE_CAP);
	return (effectiveWidth * BUILD_ROOT_VALUE) / DESIGN_WIDTH;
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
window.addEventListener("resize", scheduleRemRefresh, { passive: true });

function handlePageShow(event: PageTransitionEvent): void {
	if (!event.persisted) return;
	appliedWidth = -1;
	scheduleRemRefresh();
}
window.addEventListener("pageshow", handlePageShow);

// 基础设施真正卸载时移除 resize/pageshow，并取消 frameId。
```

如果实测 layout viewport 已变化但 `window.resize` 漏发，可在能力检测后观察 `document.documentElement`；所有信号仍进入同一个幂等调度函数：

```typescript
const viewportObserver =
	"ResizeObserver" in window
		? new ResizeObserver(scheduleRemRefresh)
		: undefined;

viewportObserver?.observe(document.documentElement);
// 卸载时：viewportObserver?.disconnect();
```

`VisualViewport.resize` 主要反映视觉视口、缩放和键盘变化，不替代 layout viewport 作为 REM 输入。已有 ArkTS 通知时，它也只触发 `scheduleRemRefresh`；不要把原生 dp 宽度直接写成根字号。

### 2. 用 CSS 保留旧公式

如果公式只依赖 viewport，且目标 Web 内核与构建链验证通过，可把 JS 调度替换成等价 CSS。以 `D=750`、`R=75`、`C=540` 为例：

```css
html {
	font-size: 10vw;
}

@media (min-width: 540px) {
	html {
		font-size: 54px;
	}
}
```

这段基础样式必须避免再次被 px→rem 插件意外转换。CSS 化只减少运行时监听，不会自动获得平板布局；到达上限后的页面仍需按 `responsive-layout.md` 重排。

CSS `vw` 根字号与 JavaScript 动态 REM 具有相同的整体缩放和用户缩放风险；它是旧公式的低运行时成本实现，不是推荐给新页面的现代化方案。

### 3. 渐进退出动态根字号

当需求是原生式多设备体验，而不是放大的移动画布时，逐步把职责拆开：

- 根字号恢复用户可预期的基线，`rem/em` 用于文字和设计 token。
- 页面几何使用 `%`、`fr`、`minmax()`、Grid/Flex 和内容驱动断点。
- 组件使用 container query；宽屏使用重复、挪移、缩进或分栏布局。
- 流式字号和间距只在小范围内使用有上下界的 `clamp()`。
- 图片使用容器尺寸、`aspect-ratio`、`object-fit` 与 `srcset/sizes`，不依赖根字号放大资源。

不能只把 `html` 改为 `font-size: 100%`：如果现有 CSS 已大量构建成设计稿 REM，必须同步调整构建配置或分批迁移样式，否则尺寸会整体失真。

## 高频错误模式

### 把调用结果注册成监听器

```javascript
// 错误：普通 refreshRem 返回 undefined。
window.addEventListener("resize", refreshRem());

// 正确：初始化与监听分开。
refreshRem();
window.addEventListener("resize", refreshRem);
```

只有 `refreshRem()` 明确返回另一个函数时，第一种写法才成立。

### 用初始高度阻止重算

按宽度计算 REM 时，用启动时 `clientHeight` 相等作为守卫会误伤折叠、旋转和多窗口切换。比较当前宽度与上次已应用宽度；键盘造成的纯高度变化不应改根字号。

### 多个写入者或缓存启动尺寸

检查入口脚本、UI 库、页面组件和 flexible 脚本。保留一个权威写入者，每次重新读取 `documentElement.clientWidth`，不要永久缓存启动宽度，也不要切换到 `screen.width`。

### 用提高上限代替布局

根字号符合公式但页面仍单列、靠左或留白时，先检查内容壳、导航、Grid/Flex 和断点。提高 `maxWidth` 只会延迟问题，并可能放大文字与图片。

### 依赖方向、折叠状态或 reload

`orientationchange` 和折叠状态不能覆盖分屏、自由窗口或 Web 组件实际 slot；`reload()` 会丢失滚动、表单、弹层和请求状态。统一响应 viewport/container 变化并保持业务状态。

## 验证矩阵

记录每个状态的 `clientWidth`、公式期望根字号、computed root `font-size`、内容壳宽度、关键文字尺寸、图片 rect/currentSrc 和页面状态：

- 最小支持宽度、手机基准宽度、`C-1/C/C+1` 和至少一个明显宽于 `C` 的窗口。
- 外屏启动→展开、内屏启动→折叠、内屏横竖屏切换。
- 分屏进入、连续调整和退出；相同最终 viewport 必须得到相同根字号和布局。
- 快速连续 resize、BFCache 返回和 SPA 重挂；监听不重复、无需 reload。
- 输入框聚焦与键盘开合；纯高度变化不改变按宽度计算的根字号。
- 200% 文字缩放和可用时的页面放大；核心内容不截断、不重叠、不丢失。
- 宽屏新增空间用于增列、挪移、缩进或分栏；文字、图片、间距和圆角不继续无界放大。
- 图片保持比例与清晰度，内容图候选与实际 slot 匹配。

通过条件：直板机原有视觉无退化；公式、构建产物和 computed style 一致；缩放上限有内容证据；上限之后由响应式布局接管；状态切换不丢失业务状态。
