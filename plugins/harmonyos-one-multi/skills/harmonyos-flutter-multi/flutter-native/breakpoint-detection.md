# 原生 Flutter 断点检测

局部组件用 `LayoutBuilder.constraints.maxWidth`，全页窗口分类用 `MediaQuery.sizeOf(context)`。将宽度映射成统一的 xs/sm/md/lg/xl 枚举，并让断点变化自然触发 rebuild。

```dart
enum WidthClass { xs, sm, md, lg, xl }

WidthClass widthClass(double width) => switch (width) {
  < 320 => WidthClass.xs,
  < 600 => WidthClass.sm,
  < 840 => WidthClass.md,
  < 1440 => WidthClass.lg,
  _ => WidthClass.xl,
};
```

不要额外监听尺寸再 `setState`，除非状态需在 Widget 树外共享；避免同一帧同时由 `MediaQuery` 和自定义监听触发两次切换。
