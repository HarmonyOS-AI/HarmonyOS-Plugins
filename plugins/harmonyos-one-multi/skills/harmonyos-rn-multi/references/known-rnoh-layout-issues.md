# RNOH UI 已知行为的证据化分流

本文件不是永久缺陷清单。只在业务尺寸、父约束和呈现链已证明正确，但目标版本仍出现 Text、ScrollView/List、SafeArea、Modal/Transform/Animation 或 Yoga 异常时读取。先记录锁定 RN/RNOH/HAR/CLI 版本，再查该版本 tag、release、类型/实现和真机；不要因为历史 release 出现过相似修复就直接套 workaround。

## 分流原则

1. 用最小 RN 页面复现，移除业务状态库、响应式库和复杂导航。
2. 同轮次证明 window、派生 token、React props 和 `onLayout` 已正确。
3. 在当前锁定版本、相邻已修复版本和手机基线比较；不要把 Android/iOS 上游问题直接当 RNOH 结论。
4. 优先升级到兼容线内已包含修复的版本；必须规避时记录版本条件、删除条件和手机回归。
5. 无法在目标设备复现或缺版本证据时写 `not_verified`，不要报告框架缺陷已修复。

## 症状地图

| 症状 | 先排除业务问题 | 版本证据方向 | 不要做 |
| --- | --- | --- | --- |
| 折展后 `useWindowDimensions` 不变 | Host window→RNInstance/RNSurface 传播、listener owner | RNOH 对应版本 Host/Dimensions 实现与官方多屏指导 | 用 posture 或 reload 掩盖尺寸不更新 |
| window 已变但 rem/StyleSheet 不变 | 模块级缓存、memo deps、全局单例不触发 render | 响应式库是否有 hook/subscription | 直接归因 Yoga/RNOH |
| Text 宽度、换行、`onTextLayout` 或 content size 异常 | fontSize/lineHeight/固定高度、fontScale、字体注册、父约束 | RNOH release 曾包含 Text 测量、content size、`allowFontScaling` 修复 | 全局关字体缩放或反复 force remount |
| 折展后列表位置跳变/归零 | pixel offset、列数、`getItemLayout`、key、可见项锚点 | RNOH release 曾包含 fold/unfold `contentOffset` 修复 | 重建 NavigationContainer 或清空列表状态 |
| 横向/多列列表裁剪或加载异常 | `removeClippedSubviews`、item geometry、extraData、viewport | RNOH release 曾包含横向切换/裁剪与 VirtualizedList 修复 | 把关闭虚拟化当永久通用方案 |
| SafeArea 缺失或重复 | Host/RNSurface/provider/page 四层 owner | RNOH release 与 safe-area-context 锁定版本 | 所有层都加同一 inset |
| KeyboardAvoidingView 行为消失或双重上抬 | Host resize、KAV、TextInput、Sheet 唯一策略 | RNOH release/FAQ 与目标版本真机 | 固定 keyboard height 或按设备分支 |
| 仅 1px 缝隙、边框或累计偏差 | 浮点求和、父子混合舍入、PixelRatio 手工 round | RN 0.72/Yoga 兼容线与项目实际 patch | 在每层重复 round 造成累计误差 |
| 路由后 Modal 仍在窗口顶层 | RN Modal/Portal/ArkUI Dialog owner、关闭时机 | 目标版本 FAQ 与 Modal/Dialog 实现 | 重建 NavigationContainer 清理弹窗 |
| transform/animation 最终 view 与 onLayout 不一致 | Yoga 几何、视觉 transform、端点依赖、旧 callback | RNOH release/实现中的 transform 与 animated event 修复 | 用更多 translate 补偿错误 owner |

## 文本测量为什么单独分流

RNOH 的 UI 布局由 Yoga 计算，而 Text 会通过原生 `TextMeasurer::measure()` 返回测量结果再参与 Yoga。若 React props 与父约束正确、普通 View 几何也正确，但只有 Text 的换行/宽高/`onTextLayout` 陈旧，应建立最小文本复现并检查版本，而不是继续修改 breakpoint 或 rem。

验证至少覆盖：默认/大字体、无/有显式 lineHeight、短/长文本、嵌套 Text、固定/可增长父容器、折→展→折，以及冷启动到相同最终 window 的对照。

## ScrollView 与列表连续性

折展后不能只比较绝对 contentOffset。列数、item 宽高或 header 尺寸变化时，同一像素 offset 不代表同一业务内容。优先记录 visible item key/index、局部 offset、contentSize、viewport、列数和 `getItemLayout` 版本。

若业务锚点与 geometry 已正确而 RNOH 仍错误，再检查锁定版本是否包含对应 fold/unfold offset、horizontal clipping 或 VirtualizedList 修复。临时关闭 `removeClippedSubviews`、移除 `getItemLayout` 等只可作为反证或带版本条件的规避。

## SafeArea 与键盘

历史 release 中出现过 nested SafeArea、某些场景 safe distance、KeyboardAvoidingView 与 TextInput 行为修复，说明这类问题必须做版本分流。但首先仍要建立 inset owner 表和键盘策略；业务重复消费 inset 与框架缺陷可以同时存在。

验证初始值与变化值：冷启动、旋转、折展、分屏/自由窗、键盘显示/隐藏、Modal/Sheet 和前后台。只有锁定版本、最小复现和运行证据一致时才建议升级或版本规避。

## Modal、Transform 与动画

RNOH 历史 FAQ/Release 出现过 ArkUI Dialog 顶层行为、transform 后 view 行为和 animated event 更新修复。先证明 overlay owner、Yoga/onLayout、transform/animated endpoint 和清理均正确；再用最小页面比较同兼容线版本。历史标题不能证明当前版本仍有问题。

## 依据与验证日期

验证日期：2026-08-29。

- RNOH 官方多屏适配指导：Flexbox、Dimensions、useWindowDimensions 与折叠尺寸监听。<https://gitee.com/openharmony-sig/ohos_react_native/blob/master/docs/zh-cn/%E5%A4%9A%E5%B1%8F%E9%80%82%E9%85%8D%E6%8C%87%E5%AF%BC.md>
- RNOH 官方 release：包含 Text 测量/content size、SafeArea、`allowFontScaling`、KeyboardAvoidingView、横向裁剪和折展 `contentOffset` 等历史修复记录。<https://gitee.com/openharmony-sig/ohos_react_native/releases>
- RNOH 渲染三阶段：Yoga 负责 UI 布局，Text 由原生 TextMeasurer 测量后返回 Yoga。<https://gitee.com/openharmony-sig/ohos_react_native/blob/master/docs/zh-cn/%E6%B8%B2%E6%9F%93%E4%B8%89%E9%98%B6%E6%AE%B5.md>
- React Native Dimensions：foldable/rotation 下尺寸可能变化，依赖尺寸的渲染与 style 不应缓存。<https://reactnative.dev/docs/dimensions>
- OpenHarmony RN 社区公告入口：RN 0.72 Yoga 浮点舍入共性问题。<https://gitcode.com/OpenHarmony-RN>
- RNOH 使用类 FAQ：包含 Modal 映射 ArkUI Dialog 及路由顶层行为的历史说明。<https://gitee.com/openharmony-sig/ohos_react_native/blob/0.72.5-ohos-5.0-release/docs/zh-cn/faqs/%E4%BD%BF%E7%94%A8%E7%B1%BBFAQ.md>
