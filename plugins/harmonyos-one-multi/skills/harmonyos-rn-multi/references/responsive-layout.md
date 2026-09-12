# RN 自适应与响应式布局

## 先判组件约束还是页面结构

命中 `RN-01` 时先修首个不可收缩、不可增长、固定或比例错误的组件约束。只有信息结构、导航位置、列数或同时可见区域确实变化时才进入 `RN-02`。

| 现象 | 优先机制 | 何时使用断点 |
| --- | --- | --- |
| Row 文本/操作溢出 | `flexGrow/flexShrink`、可增长高度、必要换行 | 操作区需要迁移到另一行/区域 |
| 内容过宽 | 外层占满、内层 `maxWidth` 居中 | 宽屏需要新增侧栏/详情 |
| 图片/视频变形 | 受约束宽度、`aspectRatio`、语义化 `resizeMode` | 不同窗口需要不同构图/结构 |
| 卡片稀疏 | 连续伸缩或列表增列 | 列数变化能显著改善信息密度 |
| 导航拥挤 | 同一 route registry 下重排 | 底部 Tab 迁移侧栏 |

## 窗口与断点

函数组件直接消费当前应用窗口：

```tsx
type Breakpoint = 'compact' | 'medium' | 'expanded';

function resolveBreakpoint(width: number): Breakpoint {
  if (width >= 840) return 'expanded';
  if (width >= 600) return 'medium';
  return 'compact';
}

function useBreakpoint(): Breakpoint {
  const { width } = useWindowDimensions();
  return useMemo(() => resolveBreakpoint(width), [width]);
}
```

示例阈值不是平台标准。优先复用工程 design tokens；没有规范时连续改变目标窗口，根据内容首次拥挤、浪费或信息结构失效的位置选择阈值。不要复制 ArkUI 断点枚举，也不要按设备类型映射断点。宽而短的横屏/自由窗口还要检查高度、宽高比和核心操作是否可达，不能只套 `minWidth` 大屏规则。

`Dimensions.get('window')` 可用于命令式即时读取；hook 不适用时才订阅 `Dimensions.addEventListener('change', ...)`，保存 subscription 并在 owner 卸载时 `remove()`。不要把启动值放进模块常量或静态 StyleSheet 后永久使用。项目使用 rem/rpx/normalize 或响应式样式库时继续读取 `dynamic-scaling-and-styles.md`，不能只确认原始 width 更新。

## Flexbox 约束

RN 默认 `flexDirection: 'column'`。候选 style 属性必须经过当前 RN/RNOH 类型和运行行为确认，不能照搬 Web CSS。

```tsx
const styles = StyleSheet.create({
  viewport: { flex: 1, alignItems: 'center' },
  content: { width: '100%', maxWidth: 960 },
  row: { flexDirection: 'row', alignItems: 'center' },
  body: { flexGrow: 1, flexShrink: 1, minWidth: 0 },
  action: { flexShrink: 0 },
});
```

`minWidth: 0`、`gap` 等行为按锁定版本和最小复现确认，不机械添加。启用 `flexWrap` 后移除只容纳一行的固定高度。大字体下关键文本、表单错误和操作说明不能靠默认 `numberOfLines` 隐藏。

若子项变成 0、百分比高度失效、ScrollView 空白/不能滚动或宽短窗口操作不可达，转 `RN-09` 读取 `layout-constraints-and-scroll.md`，逐层证明父约束和 viewport；不要继续在叶子叠 `flex: 1`。

## 列表、主从栏与导航

- FlatList 列数变化前检查当前版本行为；若必须重挂，只给列表呈现层使用由列数派生的 key，并把数据、筛选、选中、路由和业务锚点放在列表外。
- 列数或派生 item 尺寸变化时同步检查 item 宽高、间距、`renderItem/useCallback` 闭包、`extraData`、`getItemLayout`、`removeClippedSubviews`、骨架、空态和尾部加载；不要只改 `numColumns`。
- 记录 visible item key/index 与局部 offset。布局变化后绝对 pixel offset 不一定对应同一内容；如果业务链正确但折展后 offset 仍跳变，按 `RN-08` 检查锁定 RNOH 版本。
- 主从详情共享一个 `selectedId`/route state；紧凑模式显示其一，展开模式同时显示，不创建两份选中状态。
- Tab 与侧栏可以切换视觉容器，但共享 route registry 与 active route；NavigationContainer 不进入断点互斥分支。
- Modal/Sheet 受当前窗口和安全区约束，内容可滚动，actions 参与正常布局；含输入框时只选一个键盘避让 owner。
- 路由后弹窗残留、Portal/Dialog 层级冲突或弹窗打开期间不随窗口更新时，转 `RN-12`；需要评估官方分栏、栅格、Fold 容器或避让组件时才增加 `RN-13`。

## 文本、图标与媒体

- 从 `useWindowDimensions()` 读取 `fontScale`；若 `width/height/fontScale` 本身陈旧，先路由 `RN-04` 检查 Host 传播；原始值正确而派生 fontSize/样式陈旧则路由 `RN-03`。
- 固定高度 + 固定 lineHeight + 多行文本是高风险组合；优先让容器增长/换行。
- `fontScale` 是用户文字偏好，不是页面 rem；不要把它乘到非文字布局，也不要与 Text 默认缩放重复相乘。
- 图标视觉尺寸和点击热区分开验证；不要用 PixelRatio 放大布局盒。
- Image/Video 先判断完整展示还是允许裁切，再选 `contain`/`cover`；用 `aspectRatio` 保持比例，验证加载前占位和失败态。
- PixelRatio 只用于资源像素、发丝线和明确的布局单位↔物理像素边界；布局宽高和断点保持 RN layout units。
- RN wrapper 已收到新 bounds、内部 Surface/触控仍旧时，转 `RN-07`，不要继续改外层 style。
- React props、父约束和 onLayout 都正确但 Text 测量/换行仍异常时，读取 `known-rnoh-layout-issues.md` 做版本分流，不用更多 rem 补偿。
- 出现 RTL 绝对定位/方向性图标/动画错向时转 `RN-10`；transform 造成重叠或 resize 动画终点陈旧时转 `RN-11`。

## 状态连续性

NavigationContainer、Provider、Store、数据缓存和业务 controller 位于不随 breakpoint 变化的稳定层。断点只改变 presentation；逐个审计依赖 width/height/breakpoint 的 effect，允许重算布局，不允许无条件清空数据、导航或长生命周期资源。

## 验证矩阵

- 手机窄屏基线；断点前/中/后；目标大屏；同宽短高度窗口。
- 冷启动折态→展态→折态、冷启动展态→折态→展态，以及旋转、分屏和自由窗口拖拽。
- 默认/大字体、长文本、空态/加载/错误态、键盘与安全区组合。
- 列表位置、选中项、表单、route、焦点、媒体进度和原生组件状态保持连续。

完成条件：没有由固定约束造成的溢出/截断；页面结构只在内容需要处切换；相同最终窗口得到相同呈现；手机基线和业务状态无退化。
