# 多设备资源差异化与动态样式

## 结论与适用边界

这个场景在 RN/RNOH 中成立，但不是因为 RN 支持 CSS `rem`。React Native 的布局尺寸是无单位、与密度无关的 layout units；`rem/rpx/wp/hp/scale/normalize` 只是工程自定义函数或三方库约定。不要为一个原本没有设计单位系统的项目新造 `rem`，也不要用整页等比缩放替代 Flexbox、断点、分栏和内容最大宽度。

本场景处理两类问题：

1. 字号、间距、图标、圆角、列数或布局方向需要按窗口断点取不同值。
2. 项目已有连续设计单位或动态样式，但窗口变化后派生值、React render、StyleSheet、列表缓存或动画端点没有同步。

如果只是父容器无界、Flexbox 收缩失败或文本不能自然换行，转 `RN-01`/`RN-09`；如果 `useWindowDimensions()` 本身陈旧，转 `RN-04`。

## 先明确术语

React Native style 接收数值布局单位，没有浏览器 CSS 的原生 `rem` 单位。工程中的 `rem/rpx/wp/hp/scale/normalize/responsiveFontSize` 通常是自定义函数或三方库，把设计稿尺寸转换为 RN layout units。

因此“折叠展开后 fontSize/rem 没变化”至少有三种不同根因：

1. `useWindowDimensions`/`Dimensions` 本身仍是旧 window：转 `RN-04` 检查 Host。
2. window 已更新，但派生函数、token 或 StyleSheet 仍持有启动值：留在 `RN-03`。
3. JS props/onLayout 已正确，但文本测量或原生 UI 仍旧：形成最小复现后转 `RN-08` 或 `RN-07`。

系统 `fontScale` 是用户文字偏好，`scale/PixelRatio` 是像素密度，自定义 `layoutScale/rem` 是项目设计单位。三者不能互相代替。

## 先选择正确的值来源

| 需求 | 首选方式 | 关键约束 |
| --- | --- | --- |
| 永远不随窗口变化的颜色、基础圆角或固定触控下限 | 模块级 `StyleSheet.create` / 静态 token | 不要为了“响应式”把所有值动态化 |
| 字体、间距、图标、列数、布局方向等离散变化 | 项目唯一的 breakpoint provider/hook | 必须有最小断点兜底；当前档缺值时只按项目既定规则回退 |
| 随窗口小范围连续变化的已有设计单位 | `useWindowDimensions()` + 纯函数 + clamp | 仅保留确有设计规范的连续缩放，不无限放大整页 |
| 一次命令式读取且不参与后续 render | `Dimensions.get('window')` | 不能缓存后供动态样式长期使用 |
| Hook 不适用、确需订阅窗口事件 | `Dimensions.addEventListener('change')` | 单一 owner、更新 React state/store、卸载时 `remove()` |
| 原生物理 px ↔ RN layout unit 边界或资源清晰度 | `PixelRatio` | 只在明确边界转换一次，不缩放字体、断点或整套间距 |
| 用户系统文字大小 | `fontScale` / Text 字体缩放属性 | 只表达文字可访问性，不驱动非文字布局 |

优先复用工程现有断点源。只有锁文件、import 和运行实现证明项目使用某个断点包时，才调用该包的 `useBreakpointValue` 一类 Hook；不要仅因示例中出现某个包名就新增依赖。

### 离散断点值：字体、间距和组件尺寸

下面的 `useBreakpointValue` 代表“工程现有的响应式断点 Hook”，签名和断点名以锁定实现为准。示例中的值全部来自项目设计 token，不代表 RN/HarmonyOS 推荐值：

```tsx
const fontSize = useBreakpointValue<number>({
  base: designTokens.typography.bodyCompact,
  md: designTokens.typography.bodyRegular,
  lg: designTokens.typography.bodyLarge,
});

const paddingHorizontal = useBreakpointValue<number>({
  base: designTokens.spacing.pageCompact,
  md: designTokens.spacing.pageRegular,
  lg: designTokens.spacing.pageExpanded,
});

const iconSize = useBreakpointValue<number>({
  base: designTokens.iconSize.regular,
  md: designTokens.iconSize.large,
});

const cardStyle = useBreakpointValue<ViewStyle>({
  base: designTokens.card.compact,
  md: designTokens.card.regular,
});

return (
  <View style={[styles.container, { paddingHorizontal }]}>
    <Text style={[styles.title, { fontSize }]}>标题</Text>
  </View>
);
```

断点适合离散设计决策，不要用设备类型推断，也不要让多个 Provider/Manager 同时维护 active breakpoint。列数变化时还要审计 `FlatList key`、`extraData`、`getItemLayout` 和滚动锚点，避免用重建整个 React 根来刷新。

### 无第三方断点 Hook 时

直接由当前应用窗口计算语义断点和 token；集中在唯一 Hook/Provider 中，避免每个页面复制阈值：

```tsx
function useResponsiveTokens() {
  const { width } = useWindowDimensions();
  return useMemo(() => {
    if (width >= projectBreakpoints.expandedMin) {
      return projectResponsiveTokens.expanded;
    }
    if (width >= projectBreakpoints.mediumMin) {
      return projectResponsiveTokens.medium;
    }
    return projectResponsiveTokens.compact;
  }, [width]);
}
```

`projectBreakpoints` 和 `projectResponsiveTokens` 必须来自项目已有配置。若项目没有这些配置，应先根据内容断裂点、目标窗口和设计验收建立并记录依据；不要从示例、设备型号或其他项目复制阈值。

## 派生链审计

从最终异常属性反向搜索所有生产者：

```text
application window width/height
  → useWindowDimensions 或 Dimensions change
  → resolveBreakpoint / resolveLayoutScale / rem / token factory
  → hook state / Context value / memo dependencies
  → StyleSheet 或组件 props
  → Text/View/Image/List onLayout
```

每一段在折态、展态、再次折态记录值。找到“上一段已变化、下一段未变化”的第一处：

- window 变、`layoutScale` 不变：派生函数使用启动缓存、错误输入或缺订阅。
- `layoutScale` 变、组件不 render：只修改全局变量/单例，没有 React state、hook 或 Context 通知。
- 组件 render、style 值不变：`useMemo/useCallback/React.memo` 依赖不完整，或模块级 `StyleSheet.create` 固化值。
- style 值变、`onLayout` 不变：检查父约束、Yoga/原生测量和锁定版本，不继续叠 scale。

## 高风险实现

```tsx
import { designTokens } from './design-tokens';

const { width } = Dimensions.get('window');
const rem = width / designTokens.layoutScale.baseWidth;

const styles = StyleSheet.create({
  title: { fontSize: designTokens.typography.title * rem },
  card: { width: designTokens.card.width * rem },
});
```

这里的风险不是某个基准宽度值，而是模块只执行一次；后续 `Dimensions` 对象更新不会重新执行 `rem` 和 `StyleSheet.create`。即使所有参数都来自正确的项目 token，这种消费方式仍会持有启动值。

以下写法也不闭环：

- 在 `Dimensions.addEventListener` 中只写 `globalRem = nextWidth / baseWidth`。
- `useMemo(() => createStyles(rem), [])` 或 `useCallback(renderItem, [])` 捕获旧 rem。
- Context Provider 的 value 引用始终不变，仅修改内部字段。
- 响应式库的非 hook 静态函数在模块级 StyleSheet 中求值；库 runtime 更新但消费者不订阅。
- `Animated.Value`、插值 input/output、Modal/Sheet 高度只在 mount 时按旧 window 创建。

## 连续派生值：仅用于已有设计单位体系

只有项目已经定义连续缩放策略时，才保留现有公式，并把它改为当前 window 的纯派生值，让消费者响应。策略必须作为具名配置传入，不在适配代码里填写来源不明的数字：

```tsx
type DesignScalePolicy = Readonly<{
  baseWidth: number;
  minScale: number;
  maxScale: number;
}>;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function useDesignUnits(policy: DesignScalePolicy) {
  const { width, height, fontScale } = useWindowDimensions();
  const { baseWidth, minScale, maxScale } = policy;
  const layoutScale = useMemo(
    () => clamp(width / baseWidth, minScale, maxScale),
    [width, baseWidth, minScale, maxScale],
  );
  return { width, height, fontScale, layoutScale };
}

function Page() {
  const { layoutScale } = useDesignUnits(designTokens.layoutScale);
  const styles = useMemo(() => createStyles(layoutScale), [layoutScale]);
  return <View style={styles.card} />;
}

const createStyles = (layoutScale: number) => StyleSheet.create({
  card: { padding: designTokens.spacing.card * layoutScale },
});
```

### 连续缩放参数从哪里来

| 参数 | 合法来源 | 不合法来源 |
| --- | --- | --- |
| `baseWidth` | 项目设计稿基准、现有 design token、既有适配库配置 | 因为某个数字在手机设计中常见就直接使用 |
| `minScale` / `maxScale` | 产品与设计允许的缩放范围，并经最窄/最宽目标窗口验收 | 从示例复制经验值，或仅凭视觉感觉设置 |
| breakpoint 阈值 | 项目统一断点规范，或内容开始拥挤/需要改变信息结构的实测临界点 | 设备型号、物理屏幕宽度、其他项目阈值 |
| 字号、间距、图标、圆角 token | 项目设计系统和可访问性要求 | 用同一个比例机械缩放所有属性 |

在代码审查或交付记录中说明参数所在文件、设计依据和验证窗口。找不到可追溯来源时，不要猜测 `baseWidth`、最小/最大 scale，也不要新建连续缩放；回到 Flexbox、内容最大宽度和离散 breakpoint token。宽屏通常通过增列、分栏或留白组织空间，而不是把整页等比放大。

静态不变量继续放模块级 `StyleSheet.create`；动态值可以通过 style 数组覆盖，避免每次 render 重建全部样式：

```tsx
const baseStyles = StyleSheet.create({
  card: { width: '100%' },
});

function Card() {
  const { layoutScale } = useDesignUnits(designTokens.layoutScale);
  const dynamicStyle = useMemo(
    () => ({ padding: designTokens.spacing.card * layoutScale }),
    [layoutScale],
  );
  return <View style={[baseStyles.card, dynamicStyle]} />;
}
```

## 字体与双重缩放

- `fontScale` 代表用户辅助功能设置，不代表展开屏要把整页放大。
- RN Text 默认可能继续应用系统字体缩放；若 `fontSize` 已乘自定义 layoutScale，再显式乘 `fontScale`，可能发生双重缩放。
- 不为消除溢出而全局设置 `allowFontScaling={false}`。先允许 Text/父容器增长、换行，再按产品和可访问性要求决定 `maxFontSizeMultiplier` 等策略，并验证目标 RNOH 版本。
- 如果项目把“根 fontSize”同时当 spacing、width、height 和文字基准，先拆成 `layoutScale` 与文字 token；避免系统字体调整把非文字布局一起放大。
- 固定 `height/lineHeight` 与动态文字组合容易截断；优先使用最小高度和自然测量。

## PixelRatio 与单位边界

- RN 布局数值是无单位、与密度无关的 layout units。不要把 CSS `px`、HarmonyOS 原生物理 px 和 RN layout units 混成一种单位。
- `PixelRatio.get()` 表示设备像素密度；`getPixelSizeForLayoutSize()` 可在请求位图或调用明确要求物理 px 的原生接口时，将 layout size 转成 pixel size。
- 原生 API 返回物理 px 时，先依据该 API 的锁定版本和文档确认坐标空间，再在唯一 adapter/provider 中转换成 RN layout units。页面不得重复转换。
- 不要把 `PixelRatio.get()` 乘到 `width`、`height`、`fontSize`、breakpoint 或整套 spacing；RN 会在提交原生视图时处理像素栅格对齐。

```tsx
// 资源请求：layout size 与资源 pixel size 分工明确
const imageLayoutSize = 48;
const imagePixelSize = PixelRatio.getPixelSizeForLayoutSize(imageLayoutSize);

// 布局仍使用 layout size
<Image source={loadAvatar(imagePixelSize)} style={{ width: 48, height: 48 }} />;
```

若跨 RNOH 原生边界，转换方向不能仅凭变量名猜测。先确认 API 返回的是物理 px、vp 还是已映射的 RN layout unit，再决定是否转换。

## 条件样式与 StyleSheet 组织

- 静态不变量保留在模块级 `StyleSheet.create`。
- 动态值通过 style 数组末项覆盖，或用依赖完整的 `useMemo` 创建；style 数组后项优先。
- 一次性 `Dimensions.get('window')` 只适合命令式快照，不适合需要随折展、旋转、分屏或自由窗口更新的 render。
- 连续拖拽窗口时，如果计算昂贵，可对派生计算或下游副作用做节流；不要让显示状态长期落后于最终 window。

## 列表、缓存与动画

- `renderItem`、`getItemLayout`、item memo comparator 和 `extraData` 都要审计派生尺寸依赖。item 是 PureComponent/React.memo 且 props 未变化时，仅外部全局 rem 变化不会刷新。
- 列数或 item geometry 变化后，旧 `getItemLayout`、像素 offset 和测量缓存可能失效；保存可见 item key/index 与局部 offset，必要时只重挂列表呈现层。
- 动画端点由 width/rem 派生时，在变化前取消或结算旧动画，再用最新值更新；不要让旧回调覆盖新 epoch。
- 第三方响应式样式库必须核对锁定版本是否提供 hook/subscription，以及 breakpoint/token 是否和 runtime window 同步；不要只读一次 runtime 单例。

## 验证矩阵

每个状态记录 `{window.width, window.height, scale, fontScale, layoutScale, breakpoint}` 和关键 style/onLayout：

- 冷启动折态 → 展态 → 折态。
- 冷启动展态 → 折态 → 展态。
- 断点前/中/后、同宽短高度、分屏/自由窗连续拖拽。
- 系统默认字体 → 大字体；确认只影响应受影响的文字和容器。
- FlatList 可见项、动画中途 resize、Modal/Sheet 打开时 resize。

同一最终 window 必须得到相同 token 和布局，不能依赖启动形态；整个过程不 reload、不重建 React 根、不丢 route/表单/列表业务状态。

## 依据

- React Native Height and Width：布局尺寸无单位，并表示与密度无关的 pixels。<https://reactnative.dev/docs/height-and-width>
- React Native Dimensions：依赖可变尺寸的渲染和 style 不应缓存，React 组件优先使用 `useWindowDimensions`。<https://reactnative.dev/docs/dimensions>
- React Native useWindowDimensions：window、scale 和 fontScale 变化会触发 hook 更新。<https://reactnative.dev/docs/usewindowdimensions>
- React Native PixelRatio：用于像素密度、资源 pixel size 和明确的 layout size↔pixel size 边界。<https://reactnative.dev/docs/pixelratio>
- React Native Style：style 可使用对象或数组，数组后项优先。<https://reactnative.dev/docs/style>
- React Native Text：`allowFontScaling`、`maxFontSizeMultiplier` 等属性属于文字可访问性策略。<https://reactnative.dev/docs/text>
- `react-native-responsive-dimensions` 项目说明：静态方法求值后不会自动更新，折叠/旋转需要响应式 hooks。<https://github.com/react-native-toolkit/react-native-responsive-dimensions#responsive-hooks>
