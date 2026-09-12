<!--
Merged from ohos-multi-device-adaptation/references/dpi-guide.md.
Role: full DPI/breakpoint adaptation guide (ten strategies, AdaptiveDpiColumn).
Summary entry: ohos-platform/dpi-and-framework-extensions.md.
-->
# 多设备自适应 DPI 指南

整合自 `flutter_samples/ohos/docs/Scenario_based_cases/multi-device-responsive-dpi-guide.md`。

## 概述

系统总结 Flutter 多设备自适应 DPI 的核心策略、断点体系、布局适配方案及最佳实践，
帮助快速掌握从手机到折叠屏、平板、大屏设备的全场景适配方法。

## 断点体系

### 标准宽度断点（5 级，ArkUI 规范）

| 断点 | 范围 (vp)  | 典型设备              |
| ---- | ---------- | --------------------- |
| xs   | < 320      | 超小屏 / 分屏小窗     |
| sm   | 320 - 599  | 手机竖屏              |
| md   | 600 - 839  | 手机横屏 / 小折叠展开 |
| lg   | 840 - 1439 | 平板 / 大折叠展开     |
| xl   | ≥ 1440     | PC / 超大屏           |

### 标准高度断点

| 断点 | 范围 (vp) |
| ---- | --------- |
| sm   | < 600     |
| md   | 600 - 839 |
| lg   | ≥ 840     |

### 宽高比断点（弹幕等场景，基于 h/w 比值）

| 断点 | 宽高比 (h/w)        |
| ---- | ------------------- |
| sm   | < 0.8（横屏/扁宽）  |
| md   | 0.8 - 1.2（近方形） |
| lg   | ≥ 1.2（竖屏/窄长）  |

### 设备类型分类（宽度 + 宽高比）

| 设备类型     | 宽度阈值    | 宽高比条件   |
| ------------ | ----------- | ------------ |
| mobile       | < 600       | 任意         |
| tablet       | 600 - 1199  | 任意         |
| wide         | 1200 - 1599 | 任意         |
| ultraWide    | ≥ 1600      | 宽高比 > 2.0 |
| wide（回退） | ≥ 1600      | 宽高比 ≤ 2.0 |

常见简化分类：

| 设备枚举 | 名称    | 典型尺寸 | 默认列数 |
| -------- | ------- | -------- | -------- |
| phone    | 直板机  | 360×800  | 1        |
| foldable | 折叠屏  | 720×840  | 2        |
| tablet   | 平板    | 1024×768 | 3        |
| pc       | PC/2in1 | 1366×900 | 4        |

### 初始化与监听

```dart
await BreakpointManager().init();
final widthBp = BreakpointManager().getWindowWidthBreakpoint();
final heightBp = BreakpointManager().getWindowHeightBreakpoint();
BreakpointManager().addBreakpointCallback((widthBp, heightBp) {
  setState(() { /* 更新布局 */ });
});
BreakpointManager().destroy();
```

### 通用断点-值映射模式（3 值映射 5 断点）

```dart
static T getValue<T>(WidthBreakpoint bp, T smValue, T mdValue, T lgValue) {
  switch (bp) {
    case WidthBreakpoint.xs: return smValue;  // xs 与 sm 共享值
    case WidthBreakpoint.sm: return smValue;
    case WidthBreakpoint.md: return mdValue;
    case WidthBreakpoint.lg: return lgValue;
    case WidthBreakpoint.xl: return lgValue;  // lg 与 xl 共享值
  }
}
```

典型示例：

| 参数         | xs/sm | md   | lg/xl   |
| ------------ | ----- | ---- | ------- |
| 网格列数     | 2     | 3    | 4       |
| 卡片间距     | 6.0   | 12.0 | 16.0    |
| 内边距       | 8     | 16   | 24/32   |
| 字体缩放系数 | 1.0   | 1.0  | 1.1/1.2 |

### WindowInfo 混合断点模式

```dart
WindowInfo.fromSize(size: Size(1024, 768));  // 纯像素
WindowInfo.fromSizeWithBreakpoint(            // 结合平台断点（推荐）
  size: Size(1024, 768), widthBreakpoint: hadssWidthBp, heightBreakpoint: hadssHeightBp,
);
```

## 十大适配策略

### 策略 1：自适应导航模式

| 断点     | 导航形式            | 说明                           |
| -------- | ------------------- | ------------------------------ |
| xs/sm/md | BottomNavigationBar | 底部导航栏，60px 高度          |
| lg       | NavigationRail      | 侧边导航轨，带文字标签         |
| xl       | 完整侧边栏          | 可展开二级菜单，宽度按断点区分 |

侧边栏宽度：ultraWide 320px, wide 280px, tablet 240px, mobile 200px。
xl 断点下侧边栏支持两级导航，并为每个一级 Tab 记忆上次选择的二级索引。

### 策略 2：LayoutBuilder 条件布局

```dart
LayoutBuilder(builder: (context, constraints) {
  final width = constraints.maxWidth;
  final crossAxisCount = width > 600 ? 4 : 2;
  final shouldScroll = width < 500;
  final showSideAd = width > 600;
  return ...;
});
```

典型阈值：600vp（网格/侧边内容分界）、500vp（是否滚动）、760vp（横向分栏↔堆叠）、
900vp（内边距 16↔24）。

```dart
int _columns(double width) {
  if (width < 560) return 1;
  if (width < 920) return deviceColumns.clamp(1, 2);
  return deviceColumns.clamp(2, 4);
}
```

### 策略 3：GridRow 响应式栅格

```dart
GridRow(
  columns: 8, gutter: Gutter(x: 5, y: 5),
  breakpoints: Breakpoints(value: [320, 480, 640, 960],
    reference: BreakpointsReference.componentSize),
  gridCols: [
    GridCol(span: SpanOption(xs: 2, sm: 2, md: 2, lg: 1, xl: 1, xxl: 1),
      offset: OffsetOption(xs: 0, sm: 0, md: 1, lg: 0),
      order: OrderOption(xs: 1, sm: 1, md: 2, lg: 1),
      child: ItemWidget()),
  ],
)
```

- `SpanOption`：每断点占列数
- `OffsetOption`：每断点偏移
- `OrderOption`：每断点排列顺序
- `BreakpointsReference.componentSize`：断点基于组件尺寸而非全局屏幕

### 策略 4：宽高比设备分类 + 布局方向切换

| 断点     | 布局方向    | 图文比例                   |
| -------- | ----------- | -------------------------- |
| xs/sm    | 纵向 Column | 图占 100%，文独立下方      |
| md/lg/xl | 横向 Row    | 图占 50%-60%，文占 40%-50% |

```dart
final isHorizontal = ScreenUtils.isHorizontalLayout(breakpoint);
if (isHorizontal) {
  final imageFlex = (imageWidthRatio * 10).toInt();
  return Row(children: [Expanded(flex: imageFlex), Expanded(flex: 10 - imageFlex)]);
} else {
  return Column(children: [image, textSection]);
}
```

视频 + 评论区联动：

| 状态            | 视频区域  | 评论区                  |
| --------------- | --------- | ----------------------- |
| 宽屏 + 评论开启 | 66% 宽度  | 34% 右侧面板            |
| 宽屏 + 评论关闭 | 100% 宽度 | 无                      |
| 窄屏 + 评论开启 | 100% 宽度 | 底部浮层（58-82% 高度） |
| 窄屏 + 评论关闭 | 100% 宽度 | 无                      |

### 策略 5：内容最大宽度约束

```dart
static double getContentMaxWidth(BuildContext context) {
  if (windowInfo.isUltraWide) return 1200;
  else if (windowInfo.isWide) return 1000;
  else return double.infinity;
}
BoxConstraints(maxWidth: getContentMaxWidth(context))
```

### 策略 6：内容优先级 / 渐进展示

```dart
final showPriority2 = displayWidthPercent >= 50;
final showPriority3 = displayWidthPercent >= 80;
Visibility(visible: constraints.maxWidth > 600, child: SideAdWidget())
```

### 策略 7：折叠屏 / 悬停态 / 三折设备适配

折叠状态检测：

| 折叠状态       | 代码  | 含义             |
| -------------- | ----- | ---------------- |
| expanded       | 1     | 完全展开         |
| folded         | 2     | 完全折叠         |
| halfFolded     | 3     | 悬停态（半折叠） |
| tripleFoldFull | 11/21 | 三折完全展开     |

三折屏幕模式：dualFoldExpanded / dualFoldClosed / tripleFoldFull / tripleFoldDual / tripleFoldSingle。

```dart
final foldStatus = await MethodChannel('fold_status_detector').invokeMethod('getFoldStatus');
EventChannel('fold_status_detector/events').receiveBroadcastStream().listen((status) {
  setState(() { /* 重新布局 */ });
});
final creaseRegion = await MethodChannel('fold_status_detector').invokeMethod('getCreaseRegion');
final canLandscape = FoldStatusDetector.canRotateLandscape(foldStatus);
```

悬停态三区域布局：

| 区域       | 位置               | 用途                   |
| ---------- | ------------------ | ---------------------- |
| 主显示区   | 上半屏（折痕以上） | 视频/图片/核心内容     |
| 动态填充区 | 折痕区域           | 避让折痕或填充过渡内容 |
| 操作区     | 下半屏底部 56px    | 触控交互（按钮/输入）  |

```dart
final mainDisplayHeight = _creaseTop - _creaseHeight;
WidgetsBinding.instance.addPostFrameCallback((_) => _initFoldStatus());
```

### 策略 8：弹窗与安全区域避让

```dart
final dialogHeight = MediaQuery.of(context).size.height * 0.3;
final actualStatusBarHeight = windowPadding.top / devicePixelRatio;
if (dialogHeight > availableHeight) {
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersive);
}
SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);  // 关闭时恢复
SafeArea(top: !_isFullScreen, bottom: !_isFullScreen, child: ...)
Listener(behavior: HitTestBehavior.opaque, onPointerDown: (_) => _toggle(), child: ExitButton())
```

### 策略 9：自适应参数映射（超越布局）

| 参数         | xs   | sm   | md   | lg   | xl   |
| ------------ | ---- | ---- | ---- | ---- | ---- |
| 字体大小     | 12   | 14   | 16   | 18   | 20   |
| 输入框高度   | 36   | 40   | 44   | 48   | 52   |
| 容器高度比   | 0.3  | 0.3  | 0.4  | 0.4  | 0.5  |
| 弹幕速度     | 1.5  | 2.0  | 2.5  | 3.0  | 3.5  |
| 最大弹幕数   | 10   | 15   | 20   | 25   | 30   |
| 生成间隔(ms) | 2000 | 1500 | 1000 | 800  | 600  |

### 策略 10：ThemeExtension 语义化主题

```dart
class AppColors extends ThemeExtension<AppColors> {
  final Color danmakuAreaBg; final Color pageBg; final Color inputFill; final Color bulletBubbleBg;
  const AppColors({...});
  @override AppColors copyWith({...}) => ...;
  @override AppColors lerp(AppColors? other, double t) => ...;
}
ThemeData(extensions: [AppColors.light(), AppColors.dark()]);
final colors = Theme.of(context).extension<AppColors>()!;
```

## DPI 参数速查表

### 字体与输入框

| 断点 | 字体大小 | 输入框高度 | 字体缩放系数 |
| ---- | -------- | ---------- | ------------ |
| xs   | 12       | 36         | 1.0          |
| sm   | 14       | 40         | 1.0          |
| md   | 16       | 44         | 1.0          |
| lg   | 18       | 48         | 1.1          |
| xl   | 20       | 52         | 1.2          |

### 间距与内边距

| 断点  | 卡片间距 | 页面内边距 | 内容最大宽度 |
| ----- | -------- | ---------- | ------------ |
| xs/sm | 6.0      | 8          | ∞            |
| md    | 12.0     | 16         | ∞            |
| lg/xl | 16.0     | 24/32      | 1000/1200    |

### 网格与布局

| 断点  | 网格列数 | 侧边栏宽度 | 导航形态   |
| ----- | -------- | ---------- | ---------- |
| xs/sm | 2        | 200px      | 底部导航栏 |
| md    | 3        | 240px      | 底部导航栏 |
| lg    | 4        | 280px      | 侧边导航轨 |
| xl    | 4        | 320px      | 完整侧边栏 |

### 布局方向切换阈值

| 宽度阈值          | 布局切换                    |
| ----------------- | --------------------------- |
| 500vp             | Row ↔ SingleChildScrollView |
| 600vp             | 2列 ↔ 4列网格               |
| 600vp             | 是否显示侧边内容            |
| 660vp             | 是否显示浮动内容            |
| 760vp             | 横向分栏 ↔ 纵向堆叠         |
| 900vp             | 页面内边距 16 ↔ 24          |
| aspectRatio ≥ 1.2 | 视频侧面板 ↔ 底部浮层       |

## DPI 缩放计算

```dart
final scaleFactor = MediaQuery.of(context).size.width / 352.0;  // 352vp 基线
final scaledHeight = 540 * scaleFactor;
final childAspectRatio = availableWidth / (availableWidth * 0.6 + 40 * fontScale);
final imageHeight = (screenHeight * 0.6).clamp(150.0, 400.0);
```

## Column 溢出自适应 DPI 方案（AdaptiveDpiColumn）

### 快速上手

将可能溢出的顶层 `Column` 替换为 `AdaptiveDpiColumn`，零配置生效。

| 场景                        | 替换前                    | 替换后                               |
| --------------------------- | ------------------------- | ------------------------------------ |
| 页面顶层 Column（可能溢出） | `Column(children: [...])` | `AdaptiveDpiColumn(children: [...])` |
| 页面顶层 Column（不会溢出） | `Column(children: [...])` | 无需替换                             |
| Row 溢出                    | `Row(children: [...])`    | 不适用                               |

### 原理

DPI 计算公式：

```
overflowRatio = actualSize / allocatedSize
  actualSize    = Column 可用高度
  allocatedSize = 子 widget 实际占用高度之和
adaptiveDpi = clamp(overflowRatio, 0.85, 1.0) × systemDpi
```

计算示例：

```
// 溢出：可用 600px，实际 720px，系统 DPI 2.0
overflowRatio = 600/720 = 0.833 → clamp → 0.85
adaptiveDpi   = 0.85 × 2.0 = 1.7

// 未溢出：可用 600px，实际 580px
overflowRatio = 600/580 = 1.034 → clamp → 1.0
adaptiveDpi   = 1.0 × 2.0 = 2.0
```

### 完整参考实现

```dart
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

const bool _kEnableFlexOverflow = bool.fromEnvironment(
  'ENABLE_FLEX_OVERFLOW', defaultValue: true,
);

class AdaptiveDpiColumn extends StatefulWidget {
  final List<Widget> children;
  final MainAxisAlignment mainAxisAlignment;
  final CrossAxisAlignment crossAxisAlignment;
  final VerticalDirection verticalDirection;

  const AdaptiveDpiColumn({
    required this.children,
    this.mainAxisAlignment = MainAxisAlignment.start,
    this.crossAxisAlignment = CrossAxisAlignment.center,
    this.verticalDirection = VerticalDirection.down,
    super.key,
  });

  @override
  State<AdaptiveDpiColumn> createState() => _AdaptiveDpiColumnState();
}

class _AdaptiveDpiColumnState extends State<AdaptiveDpiColumn> {
  double? _adaptiveDpi;

  @override
  void dispose() {
    _adaptiveDpi = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!kReleaseMode || !_kEnableFlexOverflow) {
      return Column(
        mainAxisAlignment: widget.mainAxisAlignment,
        crossAxisAlignment: widget.crossAxisAlignment,
        verticalDirection: widget.verticalDirection,
        children: widget.children,
      );
    }
    final systemDpi = MediaQuery.of(context).devicePixelRatio;
    return LayoutBuilder(builder: (context, constraints) {
      final actualSize = constraints.maxHeight;
      if (actualSize == double.infinity) {
        return Column(
          mainAxisAlignment: widget.mainAxisAlignment,
          crossAxisAlignment: widget.crossAxisAlignment,
          verticalDirection: widget.verticalDirection,
          children: widget.children,
        );
      }
      double allocatedSize = 0;
      for (final child in widget.children) {
        if (child is Expanded || child is Flexible || child is Spacer) continue;
        allocatedSize += _measureChild(child, constraints);
      }
      if (allocatedSize <= actualSize) {
        _adaptiveDpi = null;
        return Column(
          mainAxisAlignment: widget.mainAxisAlignment,
          crossAxisAlignment: widget.crossAxisAlignment,
          verticalDirection: widget.verticalDirection,
          children: widget.children,
        );
      }
      final overflowRatio = actualSize / allocatedSize;
      final clampedRatio = overflowRatio.clamp(0.85, 1.0);
      _adaptiveDpi = clampedRatio * systemDpi;
      return MediaQuery(
        data: MediaQuery.of(context).copyWith(devicePixelRatio: _adaptiveDpi!),
        child: Column(
          mainAxisAlignment: widget.mainAxisAlignment,
          crossAxisAlignment: widget.crossAxisAlignment,
          verticalDirection: widget.verticalDirection,
          children: widget.children,
        ),
      );
    });
  }

  double _measureChild(Widget child, BoxConstraints constraints) {
    final constrained = BoxConstraints(
      maxWidth: constraints.maxWidth, minHeight: 0, maxHeight: constraints.maxHeight,
    );
    final renderObject = child.createRenderObject(context);
    try {
      renderObject.layout(constrained, parentUsesSize: true);
      return renderObject.size.height;
    } finally {
      renderObject.dispose();
    }
  }
}
```

> 实际项目可按需简化 `_measureChild`（如用 `IntrinsicHeight` 或预先已知高度值）。

### 作用域与生命周期

| 阶段                    | 行为                                                       |
| ----------------------- | ---------------------------------------------------------- |
| 检测到溢出              | 计算 adaptiveDpi，通过 MediaQuery 覆盖当前页面子树 DPI     |
| 未溢出                  | DPI 保持系统默认值                                         |
| Column 销毁（页面退出） | 立即恢复系统默认 DPI（dispose 中 `_adaptiveDpi = null`）   |

核心原则：局部生效，不污染全局。

### ENABLE_FLEX_OVERFLOW 开关

| 开关状态       | 构建命令                                   | 行为                   |
| -------------- | ------------------------------------------ | ---------------------- |
| 未配置（默认） | `flutter build hap --release`              | 启用自适应方案         |
| 显式启用       | `--dart-define=ENABLE_FLEX_OVERFLOW=true`  | 启用（与默认一致）     |
| 显式关闭       | `--dart-define=ENABLE_FLEX_OVERFLOW=false` | 禁用，保持系统 DPI     |

### Debug / Release 模式区分

| 模式    | 行为              | 原因                     |
| ------- | ----------------- | ------------------------ |
| Debug   | 不启用，保留警告  | 便于调试定位             |
| Profile | 不启用（同 Debug）| 性能分析需真实渲染       |
| Release | 启用，自动缩放    | 保证生产环境用户体验     |

### 注意事项与限制

| 场景                         | 说明                                                         |
| ---------------------------- | ------------------------------------------------------------ |
| 仅适用顶层 Column            | 应放 `Scaffold.body`，内部嵌套子 Column 不替换               |
| Row 溢出不适用               | 横向溢出用 `SingleChildScrollView` 或 `FittedBox`            |
| Expanded/Flexible/Spacer     | 不计入固定占用，方案自动跳过                                 |
| 无限高度约束                 | `maxHeight == infinity` 时无法检测，自动跳过                 |
| 0.85 下限                    | 最多缩至 `0.85 × systemDpi`，保证可读性                      |
| 多 Column 页面               | 每页仅一个顶层 `AdaptiveDpiColumn`，多个会 DPI 覆盖冲突      |
| 动画/过渡                    | DPI 变化无过渡动画，需平滑可外包 `AnimatedContainer`        |

## Flutter 布局组件最佳实践

| 适配场景     | 推荐组件                   | 说明                               |
| ------------ | -------------------------- | ---------------------------------- |
| 等比缩放容器 | `AspectRatio`              | 固定宽高比                         |
| 百分比尺寸   | `FractionallySizedBox`     | 按比例占据父容器                   |
| 弹性分配空间 | `Expanded(flex: N)`        | 多区域比例分配                     |
| 自动换行排列 | `Wrap`                     | 标签/按钮组自适应换行              |
| 可滚动自适应 | `SingleChildScrollView`    | 小屏内容溢出时滚动                 |
| 条件渲染     | `Visibility`               | 大屏显示/小屏隐藏附属内容          |
| 全局约束     | `BoxConstraints(maxWidth)` | 防止大屏内容过度拉伸               |
| 视频填充策略 | `FittedBox`                | 侧面板 `contain`，全屏 `cover`     |
| 动态尺寸变化 | `AnimatedContainer`        | 评论面板高度动画过渡               |
| 触摸捕获     | `Listener`                 | 全屏模式下替代 GestureDetector     |
| 主题令牌     | `ThemeExtension`           | 自定义语义颜色适配 light/dark      |

## 常见适配问题与解决方案

### 内容截断

固定高度卡片在小屏被截断 → `Expanded`+`Spacer`、`shrinkWrap: true`、
`SingleChildScrollView`、`(screenHeight * 0.6).clamp(150.0, 400.0)`。

### 内容堆叠

底部固定按钮与上方内容重叠 → `Stack`+`Spacer` 留底、`LayoutBuilder` 动态算高度、
`SafeArea` 避让系统 UI。

### 弹窗截断

弹窗超出屏幕 → `deviceHeight * 0.3`、`windowPadding.top / devicePixelRatio`、
动态隐藏状态栏、`SingleChildScrollView`、关闭时 `SystemUiMode.edgeToEdge`。

### 折叠屏折痕避让

折痕区域异常 → 平台通道获取折痕位置、悬停态三区布局、`addPostFrameCallback` 延迟初始化。

### 网格列数不随屏幕变化

固定列数 → `getValue(bp, 2, 3, 4)`、`width > 600 ? 4 : 2`、`GridRow`+`SpanOption`。
