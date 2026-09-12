# Transform、布局动画与动态窗口

## 先区分布局几何与视觉几何

Yoga 先计算布局；`transform` 随后改变视觉位置或大小，但不会让相邻组件重新排布。出现重叠、留白或 `onLayout` 与画面位置不一致时，记录两套数据：

```text
window / breakpoint
  → Yoga style 与 onLayout
  → transform / animated value
  → 最终 native view / Surface bounds
```

如果目标是结构重排或真实宽高变化，更新 React 状态和布局 style；如果目标只是过渡效果，保留稳定布局并使用 transform。不要用 scale/translate 假装完成单双栏适配。

## 动态端点

- 模块级 `new Animated.Value(Dimensions.get(...))`、插值 outputRange、sheet/modal 高度和分页位移会固化启动窗口。
- 端点由当前 window、breakpoint、RTL 和 safe area 的纯函数产生；窗口变化时明确选择 `retarget`、停止后重新开始，或立即落到新布局。不要同时运行旧、新两套终点。
- effect/memo/callback 必须包含实际几何依赖；清理旧 animation listener 和 completion callback，防止快速折展后旧回调覆盖新状态。
- resize 中保持业务状态和组件 identity；不要用 `key={width}` 重挂动画树。

## Animated 与 LayoutAnimation

- Native Driver 适合 transform、opacity 等非布局属性，不能直接驱动宽高、Flexbox 和 position 等布局属性。
- 需要让 Flexbox 新布局产生过渡时，在更新布局状态前配置 `LayoutAnimation`，并核对目标 RNOH 版本支持行为。
- `onLayout` 在布局计算完成后触发，但动画进行时画面可能尚未到最终位置；验收不能只采一帧事件。
- 长循环动画可能影响 VirtualizedList 渲染；列表 resize 场景同时验证可见行和尾部加载。

## RNOH 分流

若 window、React state、Yoga style、onLayout 和动画端点均正确，但最终 RNOH view 未更新，再按 `RN-08` 检查锁定版本。历史 release 中出现过 animated event、transform 后视图行为等修复，只能作为最小复现的检索入口，不能直接套 workaround。

## 验证

覆盖静止时 resize、动画开始/中途/结束时 resize、快速窄→宽→窄、RTL/LTR、前后台，以及列表滚动中动画。记录 animation id/epoch、旧新端点、onLayout、最终 native bounds 和完成回调次数；旧 epoch 不得提交最终状态。

依据：

- React Native Transforms：transform 不改变周围布局，可能与相邻组件重叠。<https://reactnative.dev/docs/transforms>
- React Native Animations：Native Driver 只支持非布局属性；LayoutAnimation 用于下一次布局变化。<https://reactnative.dev/docs/animations>
- React Native View：`onLayout` 触发时，动画中的视觉位置可能还未更新。<https://reactnative.dev/docs/view>

