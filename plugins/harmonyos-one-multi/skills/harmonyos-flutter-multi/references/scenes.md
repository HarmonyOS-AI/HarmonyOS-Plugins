<!--
Merged from ohos-multi-device-adaptation/scenes.md.
Role: detailed 16-scene adaptation guide behind scenarios/multi-device-catalog.md.
Link mapping: references/split-view-guide.md -> ../ohos-platform/split-view-framework.md;
references/platform-and-channels.md -> ../ohos-platform/platform-view-and-channels.md;
references/dpi-guide.md -> ./dpi-guide.md; SKILL.md breakpoint/strategy sections ->
../core/breakpoint-system.md.
-->
# OHos 多设备场景适配详细指南

本文档覆盖 HarmonyOS Flutter 框架多设备开发指导中的 16 个场景，每个场景包含断点逻辑、关键能力、实现要点和代码片段。

## 断点体系说明

各场景的断点阈值来源于华为多设备开发指导文档，可能与标准断点体系略有差异。
标准 5 级宽度断点（xs/sm/md/lg/xl）和 3 级高度断点定义见
[SKILL.md 断点体系](../core/breakpoint-system.md#断点体系)。

通用断点-值映射模式（3 值映射 5 断点）和十大适配策略同样见 SKILL.md。

**关键参考文档：**
- 分栏功能完整指南：[`references/split-view-guide.md`](../ohos-platform/split-view-framework.md)
- PlatformView 与 Channel 通信：[`references/platform-and-channels.md`](../ohos-platform/platform-view-and-channels.md)
- 多设备自适应DPI指导：[`references/dpi-guide.md`](./dpi-guide.md)

---

## 目录

1. [分栏场景](#1-分栏场景)
2. [区域避让场景](#2-区域避让场景)
3. [弹出框场景](#3-弹出框场景)
4. [模态弹窗场景](#4-模态弹窗场景)
5. [弹幕适配场景](#5-弹幕适配场景)
6. [瀑布流场景](#6-瀑布流场景)
7. [网格布局场景](#7-网格布局场景)
8. [图文混排场景](#8-图文混排场景)
9. [自由多窗场景](#9-自由多窗场景)
10. [背景氛围场景](#10-背景氛围场景)
11. [功能交互挂件场景](#11-功能交互挂件场景)
12. [交互归一场景](#12-交互归一场景)
13. [导航&指南针场景](#13-导航指南针场景)
14. [人脸识别场景](#14-人脸识别场景)
15. [扫一扫场景](#15-扫一扫场景)
16. [视频通话场景](#16-视频通话场景)

---

## 1. 分栏场景

> **完整配置说明、8种路由方案兼容性、注意事项和常见问题排查**
> 见 [`references/split-view-guide.md`](../ohos-platform/split-view-framework.md)。

### 场景概述

宽屏上采用主从分栏（左入口 + 右内容栈），窄屏回退为单栏全屏栈。

### 断点逻辑

| 断点 | 布局 |
|------|------|
| sm (≤600) | 单栏全屏 RouteStack |
| md (>600) | 左 MainArea + 分割条 + 右 contentArea，左栏宽度 0.4×screenWidth |
| lg | 同 md，区域更大 |
| xl | 同 lg，全屏栈模式（allScreen） |

### 两种实现方案

**方案 A：使用工程内置 SplitView（推荐）**

配置 `split_config.json` 即可，框架自动处理 Overlay 分配、pop 拦截、清栈。

**方案 B：应用层 go_router + ShellRoute**

```dart
final _router = GoRouter(
  initialLocation: '/home',
  routes: [
    ShellRoute(
      builder: (context, state, child) {
        final wide = MediaQuery.of(context).size.width >= 600;
        return wide
          ? _SplitShell(child: child, location: GoRouter.of(context).location)
          : _PortraitRoot(child: child);
      },
      routes: [
        GoRoute(path: '/home', builder: (_, __) => const HomePage()),
        GoRoute(path: '/home/a', builder: (_, __) => const APage()),
      ],
    ),
  ],
);
```

### 关键要点

- 左栏宽度比例 0.4-0.5，支持拖拽调整
- 特定页面（如视频播放）可配置全屏，退出时恢复分栏
- 比例 ≥ 0.5 时导航可用双列网格，否则单列列表
- 全屏页面使用 `SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersive)`

### 常见问题

- 阈值与业务断点不一致，旋转后未刷新 → 统一使用 600vp 阈值
- 分割线拖拽未限制比例 → clamp 到 0.2-0.8
- 弹窗在分栏中焦点异常 → 工程已内置 MirrorBarrier 焦点恢复机制

---

## 2. 区域避让场景

### 场景概述

确保应用内容在各种设备下不被系统 UI（状态栏、导航栏、挖孔、AI Bar、窗口按钮）遮挡。

### 断点逻辑

| 断点 | 避让重点 |
|------|---------|
| sm | 竖屏手机：避让状态栏、导航栏、挖孔区 |
| md | 横屏平板：避让挖孔区 |
| lg | 折叠屏：避让状态栏、导航栏、挖孔区 |
| xl | PC：避让窗口控制按钮 |

### 关键能力

- `SafeArea`：自动避让系统 UI
- `MediaQuery.of(context).padding`：获取安全边距
- `AnnotatedRegion<SystemUiOverlayStyle>`：设置状态栏样式
- `Listener`：确保手势事件在最上层响应
- `SystemChrome.setEnabledSystemUIMode`：控制全屏模式

### 实现要点

```dart
@override
Widget build(BuildContext context) {
  final safePadding = _isFullScreen
    ? EdgeInsets.zero
    : MediaQuery.of(context).padding;

  return AnnotatedRegion<SystemUiOverlayStyle>(
    value: _isFullScreen ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
    child: Scaffold(
      body: SafeArea(
        top: !_isFullScreen,
        bottom: !_isFullScreen,
        left: !_isFullScreen,
        right: !_isFullScreen,
        child: Stack(
          children: [
            // 主内容
            Positioned.fill(child: _buildContent()),
            // 退出按钮 - 使用 Listener 确保最上层响应
            Positioned(
              left: 16 + (_isFullScreen ? 0 : safePadding.left),
              top: 16 + (_isFullScreen ? 32 : safePadding.top),
              child: Listener(
                behavior: HitTestBehavior.opaque,
                onPointerDown: (_) => _handleExit(),
                child: _buildBackButton(),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
```

### 常见问题

- 横竖屏切换时避让区域未更新 → `WidgetsBindingObserver.didChangeMetrics` 重新获取
- 分屏场景下避让区域计算错误 → 使用 `MediaQuery` 而非缓存值
- 不同设备避让 API 不一致 → 统一使用 `MediaQuery.padding`

---

## 3. 弹出框场景

### 场景概述

居中弹窗与底层栅格背景协同，弹窗尺寸分档，处理键盘上移。

### 断点逻辑

| 断点 | 栅格列数 | 弹窗宽度 | 弹窗高度 |
|------|---------|---------|---------|
| sm | 4 | 320 | 300 |
| md | 8 | 500 | 400 |
| lg | 12 | 600 | 500 |
| xl | 12 | 700 | 600 |

### 关键能力

- `showDialog` + `Dialog`
- `MediaQuery`（size、viewInsets、padding）
- `RoundedRectangleBorder`
- `SizedBox` / `Expanded`（flex 分区：标题 8% / 内容 80% / 按钮 12%）

### 实现要点

```dart
void _showDialog(BuildContext context) {
  final mq = MediaQuery.of(context);
  final usableHeight = mq.size.height
      - mq.padding.top - mq.padding.bottom - mq.viewInsets.bottom;
  final usableWidth = mq.size.width - mq.padding.left - mq.padding.right;
  final maxWidth = min(usableWidth * 0.8, 400.0);
  final dialogHeight = (usableHeight * 0.6).clamp(200.0, 500.0);

  // 折叠屏判定
  bool isLikelyHalfFolded = false;
  if (mq.size.width > mq.size.height) {
    final ratio = mq.size.width / mq.size.height;
    if (ratio > 1.8 && mq.size.width > 600) isLikelyHalfFolded = true;
  }

  // 响应式取值
  final radius = _getResponsiveValue(
    screenWidth: mq.size.width, base: 24.0, sm: 24.0, md: 24.0, lg: 12.0);

  showDialog(
    context: context,
    builder: (context) => Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radius)),
      child: SizedBox(
        width: maxWidth,
        height: dialogHeight,
        child: Column(
          children: [
            _buildTitle(),           // 8%
            Expanded(child: _buildContent()),  // 80%
            _buildButtons(),         // 12%
          ],
        ),
      ),
    ),
  );
}
```

### 常见问题

- 弹窗高度超过键盘弹出后可视区 → `min(目标高度, 窗口高度 - 避让 - 键盘)`
- 写死宽高导致旋转/分屏后比例失调 → 使用 `MediaQuery` 动态计算
- 关闭弹窗后键盘未收起 → `FocusScope.of(context).unfocus()`

---

## 4. 模态弹窗场景

### 场景概述

底部弹出的模态页面弹窗，支持拖拽调节高度档位，适配折叠屏悬停态和软键盘。

### 断点逻辑

| 断点 | 高度 | 特殊处理 |
|------|------|---------|
| sm | 60% | — |
| md | 非悬停 60%；悬停 40% | 悬停态距底部 55%，避让折痕 |
| lg | 60% | — |
| xl | 60% | — |

### 关键能力

- 自定义模态组件（`Stack` + `Positioned` + `Align`）
- `AnimatedPadding`（键盘避让动画）
- 拖拽档位逻辑（`DragStartDetails`/`DragUpdateDetails`/`DragEndDetails`）
- `HitTestBehavior.opaque`（点击透明区域关闭）

### 实现要点

```dart
// 档位吸附
MapEntry<int, double> _findNearestSnap(double value, List<double> snaps) {
  double closest = snaps.first;
  int closestIndex = 0;
  double minDiff = (value - closest).abs();
  for (int i = 1; i < snaps.length; i++) {
    final diff = (value - snaps[i]).abs();
    if (diff < minDiff) {
      minDiff = diff; closest = snaps[i]; closestIndex = i;
    }
  }
  return MapEntry(closestIndex, closest);
}

// 拖拽更新（含最低档下拉退出）
void _onDragUpdate(DragUpdateDetails details) {
  double newFraction = _fraction - details.delta.dy / screenHeight;
  if (_isAtMinOnDragStart && newFraction <= minFraction && details.delta.dy > 0) {
    _extraDragDownPixels += details.delta.dy;
    newFraction = minFraction;
  }
  newFraction = newFraction.clamp(minFraction, maxFraction);
  setState(() => _fraction = newFraction);
}

void _onDragEnd(DragEndDetails details) {
  if (_isAtMinOnDragStart && _fraction == minFraction
      && _extraDragDownPixels > _closeThresholdPixels) {
    Navigator.of(context).pop();
    return;
  }
  final nearest = _findNearestSnap(_fraction, snapFractions);
  setState(() { _fraction = nearest.value; _currentSnapIndex = nearest.key; });
}

// 软键盘避让
final keyboardHeight = mq.viewInsets.bottom;
final modalHeight = screenHeight * _fraction;
final availableHeight = (screenHeight - statusBarHeight - modalHeight).clamp(0.0, double.infinity);
final needLiftHeight = keyboardHeight > availableHeight ? availableHeight : keyboardHeight;

// 横屏低屏特殊处理
if (isLandscape && screenHeight <= 440) {
  needLiftHeight = screenHeight - modalHeight - 10;
}
```

### 常见问题

- 横竖屏切换时档位丢失 → 记录 `_lastOrientation`，切换后 `_findNearestSnap` 重新吸附
- 键盘弹出时按钮被挡 → 计算 `needLiftHeight`，`AnimatedPadding` 上移

---

## 5. 弹幕适配场景

### 场景概述

弹幕发送与显示，轨道数/字号/速度按断点自适应。

### 断点逻辑

| 参数 | xs | sm | md | lg | xl |
|------|----|----|----|----|-----|
| 轨道数 | 10 | 12 | 15 | 15 | 15 |
| 轨高 | 32 | 36 | 40 | 40 | 40 |
| 字号 | 12 | 14 | 16 | 18 | 20 |
| 输入框高 | 36 | 40 | 44 | 48 | 52 |
| 弹幕速度 | 1.5 | 2.0 | 2.5 | 3.0 | 3.5 |
| 最大弹幕数 | 10 | 15 | 20 | 25 | 30 |
| 生成间隔(ms) | 2000 | 1500 | 1000 | 800 | 600 |

### 宽度断点划分

```dart
static WidthBreakpoint _getWidthBreakpoint(double width) {
  if (width < 600) return WidthBreakpoint.xs;
  if (width < 840) return WidthBreakpoint.sm;
  if (width < 1200) return WidthBreakpoint.md;
  if (width < 1600) return WidthBreakpoint.lg;
  return WidthBreakpoint.xl;
}
```

### 高度断点划分（基于宽高比）

```dart
static HeightBreakpoint _getHeightBreakpoint(double aspectRatio) {
  if (aspectRatio < 0.8) return HeightBreakpoint.sm;
  if (aspectRatio < 1.2) return HeightBreakpoint.md;
  return HeightBreakpoint.lg;
}
```

### 容器高度比例

| 高度断点 | 容器高度占比 |
|---------|------------|
| sm | 0.3 |
| md | 0.4 |
| lg | 0.5 |

弹幕轨道最小高度 = 字号 × 2.5。

### 常见问题

- 横屏高度不足仍按十几条轨道 → 按高度断点减少轨道数
- 旋转后动画按旧屏宽 → 旋转时重置动画参数
- 键盘弹出时输入框被遮挡 → 输入区域上移

---

## 6. 瀑布流场景

### 场景概述

不等高卡片瀑布流，列数按断点自适应。

### 断点逻辑（列数）

| 断点 | 列数 |
|------|------|
| xs | 1 |
| sm | 2 |
| md | 3 |
| lg/xl | 4 |

### 关键能力

- `flutter_staggered_grid_view` 的 `MasonryGridView`
- `ResponsiveBreakpoints.widthOf(width)` / `heightOf(width, height)`
- `LayoutBuilder`

### 实现要点

```dart
LayoutBuilder(builder: (context, constraints) {
  final width = constraints.maxWidth;
  final widthBp = ResponsiveBreakpoints.widthOf(width);
  final crossAxisCount = _getCrossAxisCount(widthBp);

  return MasonryGridView.count(
    padding: const EdgeInsets.all(8),
    crossAxisCount: crossAxisCount,
    mainAxisSpacing: 8,
    crossAxisSpacing: 8,
    itemCount: items.length,
    itemBuilder: (context, index) => _WaterfallCard(item: items[index]),
  );
});

int _getCrossAxisCount(WidthBreakpoint widthBp) {
  switch (widthBp) {
    case WidthBreakpoint.xs: return 1;
    case WidthBreakpoint.sm: return 2;
    case WidthBreakpoint.md: return 3;
    case WidthBreakpoint.lg:
    case WidthBreakpoint.xl: return 4;
  }
}
```

### 栅格配置（可选）

```dart
GridRow(columns: { xs: 2, sm: 4, md: 8, lg: 12, xl: 12, xxl: 12 })
GridCol(span: { xs: 1, sm: 2, md: 3, lg: 4 })
```

---

## 7. 网格布局场景

### 场景概述

等高网格，行列数响应式变化。

### 断点逻辑（列数）

| 断点 | 列数 |
|------|------|
| sm | 2 |
| md | 4 |
| lg | 6 |
| xl | 8 |

### 关键能力

- `GridRow`：栅格容器，`columns` 定义总列数
- `GridCol`：子组件，`span` 控制占比
- `SingleChildScrollView` + `Column`（推荐实现方式）

### 实现要点

```dart
GridRow(columns: {
  xs: 2, sm: 4, md: 8, lg: 12, xl: 12, xxl: 12,
}, children: [
  GridCol(span: { xs: 1, sm: 2, md: 3, lg: 4 }, child: _buildCard()),
  // ...
])
```

### 适配要点

- 折叠屏折叠态遵循"双屏独立反馈"（从上下屏触发则从上下屏反馈）
- 展开态同单屏处理
- 网格行列数响应分栏区域、横竖屏切换、折叠屏开合、分屏窗口尺寸变化

---

## 8. 图文混排场景

### 场景概述

头图与正文组合，窄屏上下堆叠，宽屏左右分栏。

### 断点逻辑

| 断点 | 布局 | 图占比 | 文占比 | 图片 fit |
|------|------|--------|--------|---------|
| xs/sm | Column 上下 | 60% 高 | 40% 高 | cover |
| md | Row 左右 | flex:3 | flex:2 | contain |
| lg | 同 md | flex:3 | flex:2 | contain |
| xl | 同 md | flex:3 | flex:2 | contain |

### 关键能力

- 断点库 `hadss_adaptive_layout`（`BreakpointConstants.initialize`、`getCurrentWidthBreakpoint`、`addBreakpointCallback`）
- `Row`/`Column` + `Expanded(flex:)`
- `SingleChildScrollView`
- `MediaQuery.of(context).platformBrightness`（深浅色适配）

### 实现要点

```dart
@override
void didChangeDependencies() {
  super.didChangeDependencies();
  BreakpointConstants.initialize();
  _currentWidthBreakpoint = BreakpointConstants.getCurrentWidthBreakpoint();
  BreakpointConstants.addBreakpointCallback((data) {
    setState(() => _currentWidthBreakpoint = data);
  });
}

@override
Widget build(BuildContext context) {
  final isHorizontal = ScreenUtils.isHorizontalLayout(_currentWidthBreakpoint);
  return isHorizontal
    ? _buildHorizontalLayout(context)  // Row + Expanded
    : _buildVerticalLayout(context);   // Column + SingleChildScrollView
}
```

### 尺寸计算

- 小屏：图片满宽，高度 = 屏幕高 × 40%
- 大屏：图片宽 = 屏幕宽 × 90%，高度 = 屏幕高 × 70%

---

## 9. 自由多窗场景

### 场景概述

分屏、悬浮窗、折叠开合及 PC 多窗环境下，窗口在极窄到极宽间变化。

### 断点逻辑（标签形态）

| 断点 | 标签形态 | 视频区 | 网格列数 |
|------|---------|--------|---------|
| sm/md | 底栏标签（高约 76vp） | 非紧凑 | 2 列 |
| lg/xl | 左侧竖标签（宽约 96vp） | 紧凑、固定 3 列 | 3 列 |

### 关键能力

- 断点判断（`hadss_adaptive_layout` 或自行封装）
- `MediaQuery` 获取尺寸与内边距
- 自由多窗状态监听
- `setWindowDecorVisible` / `setWindowTitleButtonVisible`（沉浸式）

### 自由多窗状态监听

**API22+（v2）**：`isInFreeWindowMode`

**API21-（v1）**：

```typescript
export function observePcMode() {
  if (canIUse('SystemCapability.Applications.Settings.Core')) {
    settings.registerKeyObserver(getContext(), 'window_pcmode_switch_status',
      settings.domainName.USER_PROPERTY, () => { getPcMode(); });
  }
}

export function getPcMode() {
  if (canIUse('SystemCapability.Applications.Settings.Core')) {
    settings.getValue(getContext(), 'window_pcmode_switch_status',
      settings.domainName.USER_PROPERTY).then((data) => {
        AppStorage.setOrCreate('isPCMode', data === 'true');
      });
  }
}
```

### 自由多窗沉浸式适配

```typescript
function changeWindowDecor(context: Context, max: boolean, min: boolean, isClose: boolean) {
  let uiContext = context as common.UIAbilityContext;
  uiContext.windowStage.getMainWindow().then(mainWindow => {
    mainWindow.setWindowDecorVisible(max);             // 隐藏状态栏
    mainWindow.setWindowTitleButtonVisible(max, min, isClose); // 隐藏窗口按钮
  });
}
```

> **重要**：自由多窗沉浸式不能用 `setWindowLayoutFullScreen`，必须用 `setWindowDecorVisible`。

### Flutter 侧断点判断

```dart
final media = MediaQuery.of(context);
final widthBp = getWidthBreakpoint(media.size.width);
final isLarge = widthBp == WidthBreakpoint.widthLg
             || widthBp == WidthBreakpoint.widthXl;
if (isLarge) {
  // 大屏：左侧竖标签
} else {
  // 小屏：底栏标签
}
```

---

## 10. 背景氛围场景

### 场景概述

背景图片在各设备和横竖屏下不变形、不截断。

### 关键能力

- `LayoutBuilder` + `BoxConstraints`
- `Container` + `BoxDecoration` + `DecorationImage`
- `Image` 的 `fit` 属性（`BoxFit`）

### 实现要点

```dart
LayoutBuilder(builder: (context, constraints) {
  return Container(
    width: constraints.maxWidth,
    height: 260,
    decoration: BoxDecoration(
      image: DecorationImage(
        image: AssetImage('assets/background/background.png'),
        fit: BoxFit.fill,  // 或 BoxFit.cover
      ),
    ),
  );
})
```

### 适配要点

- 背景相对位置锚定窗口位置，响应折叠屏开合
- 适配分屏场景，背景尺寸随分屏窗口变化
- 全屏时背景需与状态栏、导航条避让

---

## 11. 功能交互挂件场景

### 场景概述

功能交互挂件（播放按钮、返回按钮等）UI 位置及尺寸多设备自适应。

### 断点逻辑

组件尺寸按 sm/md/lg/xl 递增。

### 适配点

1. **沉浸式切换**：`SystemChrome.setEnabledSystemUIMode` 切换 `immersiveSticky` / `edgeToEdge`
2. **挂件尺寸自适应**：`LayoutBuilder` 根据断点缩放
3. **软键盘适配**：底部挂件横屏时被键盘遮挡，需自适应调整

### 关键能力

- `SafeArea`（`maintainBottomViewPadding: true`）
- `SystemChrome.setEnabledSystemUIMode`
- `MethodChannel`（获取设备类型）
- `HardwareKeyboard`（ESC/Space 等硬件按键）
- `WidgetsBindingObserver.didChangeMetrics`（键盘检测）

### 自动全屏判断

```dart
bool _shouldAutoFullScreen(double width, double height) {
  return width < 400 && width == height;  // 正方形小窗口
}
```

### 原生设备类型获取

```dart
const platform = MethodChannel('samples.flutter.dev/device_info');
final String deviceType = await platform.invokeMethod('getDeviceType');
```

---

## 12. 交互归一场景

### 场景概述

将触摸、指针、滚轮等不同输入映射到统一交互语义。

### 断点逻辑

| 断点 | 交互能力 |
|------|---------|
| sm/md | 触摸交互（tap/long press/drag） |
| lg/xl | 增加指针悬停(hover)、滚轮切页、Ctrl 拖动 |

"类电脑"判定：逻辑宽 ≥ 1000 且高 ≥ 600。

### 关键能力

- `MouseRegion`（onEnter/onExit 悬浮高亮，cursor 设置）
- `GestureDetector`（onTap/onDoubleTap/onLongPress/onScaleUpdate）
- `LongPressDraggable`（拖拽：dragAnchorStrategy/feedback/childWhenDragging）
- `card_swiper` 插件（轻扫切页）
- `ScrollController` + `isScrollingNotifier`（滚动状态）
- `Transform`（缩放/旋转）
- `SystemMouseCursors`（光标样式）

### 实现要点

```dart
// 悬浮高亮
MouseRegion(
  cursor: SystemMouseCursors.grab,
  onEnter: (_) => setState(() => _hoverIndex = index),
  onExit: (_) => { if (_hoverIndex == index) setState(() => _hoverIndex = null) },
  child: _buildImg(highlight: _hoverIndex == index),
)

// 拖拽（关键：dragAnchorStrategy + 透明 feedback）
LongPressDraggable<String>(
  data: 'img-$index',
  dragAnchorStrategy: (draggable, context, position) {
    final box = context.findRenderObject() as RenderBox;
    return position - box.localToGlobal(Offset.zero);
  },
  feedback: Material(
    type: MaterialType.transparency,
    child: _buildImg(highlight: true),
  ),
  childWhenDragging: _buildImg(highlight: false),
  child: MouseRegion(...),
)

// 滚动监听
WidgetsBinding.instance.addPostFrameCallback((_) {
  if (!_controller.hasClients) return;
  _controller.position.isScrollingNotifier.addListener(() {
    final scrolling = _controller.position.isScrollingNotifier.value;
    if (scrolling) { /* 正在滚动 */ }
    else { /* 滚动结束 */ }
  });
});
```

### 适配要点

- 收窄窗口或档位回落时，指针能力自动关闭，避免小窗误触
- 滚轮切页仅在"类电脑"模式下启用

---

## 13. 导航&指南针场景

### 场景概述

地图底图 + 指南针 + 导航指针，传感器与双指手势协同。

### 断点逻辑

| 参数 | sm | md | lg | xl |
|------|----|----|----|-----|
| 网格圆直径基准 | ~320 | ~400 | ~480 | ~560 |
| 罗盘直径基准 | ~100 | ~120 | ~140 | ~160 |
| 说明字号 | ~14 | ~16 | ~18 | — |

### 关键能力

- **PlatformView**：`OhosView` 嵌入原生地图
- **MethodChannel**：双向通信
- **StreamController** + **Stream**：朝向数据流
- `Transform.rotate`：指南针旋转
- 原生侧：`@kit.MapKit`、`@kit.SensorServiceKit`、`geoLocationManager`

### 实现要点

```dart
// 嵌入原生地图
OhosView(
  viewType: 'com.mapview.ohos/mapView',
  onPlatformViewCreated: _onPlatformViewCreated,
  creationParams: const <String, dynamic>{'initParams': 'mapView'},
  creationParamsCodec: const StandardMessageCodec(),
)

// 创建后绑定 MethodChannel
void _onPlatformViewCreated(int id) {
  _channel = MethodChannel('com.mapview.ohos/mapView$id');
  _channel.setMethodCallHandler((call) {
    if (call.method == 'onHeadingChanged') {
      _headingController.add(double.parse(call.arguments));
    }
  });
}

// 指南针旋转
Transform.rotate(
  angle: -_compassRotation * pi / 180,
  child: Image.asset('assets/compass_arrow.png', width: 80, height: 80),
)
```

### 方向角度计算

- 指南针方向角 = `sensorZAngle - windowRotation`
- 位置标记旋转角 = `sensorZAngle - windowRotation + mapBearing + boundaryCompensation`
- 屏幕旋转：`display.getDefaultDisplaySync().rotation * 90`

### 适配要点

- 双指旋转时用手势驱动，非手势期间用传感器驱动（避免冲突）
- 传感器回调与手势不可同时 `setState`（会导致抖动）
- 断点变化时网格和罗盘直径需同步调整
- 资源清理：注销 sensor/location/display 监听 + 取消 Stream 订阅

---

## 14. 人脸识别场景

### 场景概述

活体检测界面，检测状态展示与安全释放。

### 断点逻辑

sm/md/lg/xl 行为一致（固定检测页结构），仅小屏间距调整。

### 关键能力

- `MethodChannel`（`com.facerecognition.ohos/faceRecognition`）
- 原生 `@kit.VisionKit`（`interactiveLiveness.startLivenessDetection`）
- 相机权限申请（`abilityAccessCtrl.requestPermissionsFromUser`）
- `MediaQuery.of(context).size.width`（< 600 调整间距）

### 实现要点

```dart
// Flutter 调用
final result = await _channel.invokeMethod('startDetection', {
  'isSilentMode': false,
  'actionsNum': 3,
});

// 检测区域样式切换
Container(
  decoration: BoxDecoration(
    shape: BoxShape.circle,
    color: faceDetected ? Colors.green : Colors.grey,
  ),
)

// 返回时安全释放
void _handleBack() {
  if (_isDetecting) {
    await _channel.invokeMethod('stopDetection');
  }
  Navigator.of(context).pop();
}
```

### 注意事项

- `routeMode` 须设为 `'push'`，避免活体检测页面替换 Flutter 页面导致白屏
- 原生回传结果用 `Map`：`resultMap.set('success', true); result.success(resultMap)`

---

## 15. 扫一扫场景

### 场景概述

实时扫码 + 图库解码，识别后绘制标记。

### 断点逻辑

| 断点 | 关闭按钮尺寸 | 位置 |
|------|------------|------|
| sm | 基础 | top/left 16 |
| md | 32×32 | top/left 20 |
| lg | 36×36 | top/left 24 |
| xl | 同 lg | 同 lg |

### 关键能力

- `mobile_scanner` 插件（`MobileScanner` + `onDetect`）
- `image_picker` 插件（图库选图）
- `MobileScannerController`（精细控制）
- `WidgetsBindingObserver`（生命周期管理）
- `StreamSubscription`（条形码事件监听）

### 实现要点

```dart
final MobileScannerController controller = MobileScannerController(autoStart: false);

@override
void didChangeAppLifecycleState(AppLifecycleState state) {
  if (state == AppLifecycleState.resumed) {
    _subscription = controller.barcodes.listen(_handleBarcode);
    controller.start();
  } else {
    _subscription?.cancel();
    controller.stop();
  }
}

@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addObserver(this);
  controller.start();
}

@override
void dispose() {
  WidgetsBinding.instance.removeObserver(this);
  _subscription?.cancel();
  controller.dispose();
  super.dispose();
}
```

### 适配要点

- 识别后去重入列并关闭扫描开关，避免短时间重复触发
- 图库识别优先用 `image_picker` + QR reader，无结果再走 JS 解码
- 结果标记用归一化中心点定位，缺失位置时回退右下角

---

## 16. 视频通话场景

### 场景概述

视频通话界面，摄像头画面避让、画中画(PiP)、折痕区域、分屏适配。

### 断点逻辑

| 断点 | 小窗口位置 |
|------|----------|
| sm | 右上角 |
| md/lg/xl | 自适应位置 |

### 关键能力

- **PlatformView**：`OhosView` 嵌入原生相机与远端视频
  - `CameraOhosView`（viewType: `com.videocall.ohos/cameraView`）：原生 XComponent + CameraKit
  - `RemoteVideoOhosView`（viewType: `com.videocall.ohos/remoteVideoView`）：原生 XComponent + AVPlayer
- **相机宽高比自适应**：`selectBestProfile` + cover 策略 + `setXComponentRect`
- **远端视频适配**：FIT 策略 + `FractionallySizedBox` 动态缩放
- **画中画 PiP**：`PipManager` 封装 `PiPWindow` API
- `WidgetsBindingObserver.didChangeMetrics`（屏幕变化重算）
- `SafeArea`（控制按钮避让）

### 实现要点

```dart
// 视频全屏 + 控制层安全区
Stack(children: [
  Container(
    width: double.infinity,
    height: double.infinity,
    child: CameraOhosView(viewType: 'com.videocall.ohos/cameraView'),
  ),
  Positioned.fill(
    child: SafeArea(child: _buildControls()),
  ),
])

// 远端视频动态缩放
FractionallySizedBox(
  widthFactor: _remoteVideoWidthPercent,
  heightFactor: _remoteVideoHeightPercent,
  child: RemoteVideoOhosView(viewType: 'com.videocall.ohos/remoteVideoView'),
)

// 响应式布局
final size = MediaQuery.of(context).size;
if (size.height < 600) {
  // 小屏：缩小 iconSize/margin
}
```

### PiP 状态流转

`ABOUT_TO_START → STARTED → ABOUT_TO_STOP → STOPPED`

Flutter 监听 `pipStateStream` 实现大小窗切换。

### 原生侧注册

```typescript
// EntryAbility.ets
this.addPlugin(new VideoCallPlugin());
// PlatformView 工厂注册
registry.registerViewFactory('com.videocall.ohos/cameraView', new CameraViewFactory());
registry.registerViewFactory('com.videocall.ohos/remoteVideoView', new RemoteVideoFactory());
```

---

## 附录：共性模式总结

所有场景的共性适配原则：

1. **断点面向窗口**：不以设备类型为依据，而是以窗口尺寸为依据
2. **LayoutBuilder 优先**：使用 `LayoutBuilder` 获取 constraints，而非硬编码尺寸
3. **MediaQuery 响应**：监听 `MediaQuery` 变化处理横竖屏、折叠开合、分屏
4. **SafeArea 避让**：始终包裹 `SafeArea`，全屏时动态关闭
5. **键盘避让**：使用 `viewInsets.bottom` + `AnimatedPadding`
6. **内容最大宽度约束**：大屏上限制内容最大宽度，防止过度拉伸（`BoxConstraints(maxWidth)`）
7. **内容优先级/渐进展示**：按可用空间决定显示哪些内容（`Visibility`）
8. **资源释放**：`dispose` 中取消 Stream 订阅、注销监听器、释放控制器
9. **原生通信**：统一通过 `MethodChannel`/`EventChannel` + Plugin 模式
10. **Column 溢出**：使用 `AdaptiveDpiColumn` 替代可能溢出的顶层 Column
11. **主题适配**：使用 `ThemeExtension` 定义语义化颜色令牌，支持 light/dark 切换
