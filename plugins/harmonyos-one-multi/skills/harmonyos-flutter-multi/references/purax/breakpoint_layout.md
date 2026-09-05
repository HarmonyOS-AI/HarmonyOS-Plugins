<!--
Merged from flutter-purax-adaptation/references/ (identical copy also existed in
flutter-pura-x-max-ux-20260731/references/purax/).
Role: deep-dive reference material for foldable scenes PX-01..PX-05; read on demand
via scenarios/foldable-catalog.md. Internal relative links stay valid inside purax/.
Per references/index.md this material is reference-only and never overrides SKILL.md.
-->
# 断点响应式布局适配指南

## 目标

使用 `hadss_adaptive_layout` 的断点和布局组件，实现 Flutter 页面在不同屏幕尺寸下的自适应布局。

## 常用组件一览

| 组件 | 用途 | 何时使用 |
|------|------|---------|
| `BreakpointManager` | 断点监听 | 获取当前断点 + 监听断点变化 |
| `GridRow` + `GridCol` + `SpanOption` | 12 列栅格 | 卡片网格、仪表盘等 |
| `NavigationSplitContainer` | 列表-详情双栏 | 邮件、聊天、笔记等列表-详情场景 |
| `SideBarContainer` | 侧边栏导航 | 设置、管理后台等固定导航场景 |
| `DisplayPriorityBox` | 优先级显隐 | 工具栏空间不足时按优先级隐藏 |

## 模式 1：GridView 断点适配

将硬编码 `crossAxisCount` 替换为断点驱动的动态列数：

```dart
import 'package:hadss_adaptive_layout/hadss_adaptive_layout.dart';

class AdaptiveGrid extends StatefulWidget {
  @override
  State<AdaptiveGrid> createState() => _AdaptiveGridState();
}

class _AdaptiveGridState extends State<AdaptiveGrid> {
  int _crossAxisCount = 2;

  @override
  void initState() {
    super.initState();
    _crossAxisCount = _mapBreakpointToColumns(
      BreakpointManager.instance.currentBreakpoint.widthBreakpoint,
    );
    BreakpointManager.instance.addListener((data) {
      final count = _mapBreakpointToColumns(data.widthBreakpoint);
      if (count != _crossAxisCount) {
        setState(() => _crossAxisCount = count);
      }
    });
  }

  int _mapBreakpointToColumns(WidthBreakpoint bp) {
    switch (bp) {
      case WidthBreakpoint.xs: return 1;
      case WidthBreakpoint.sm: return 2;
      case WidthBreakpoint.md: return 3;
      case WidthBreakpoint.lg: return 4;
      case WidthBreakpoint.xl: return 5;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: _crossAxisCount,
      ),
      itemBuilder: (ctx, i) => cards[i],
    );
  }
}
```

**原生 Flutter 方案：**

```dart
LayoutBuilder(
  builder: (context, constraints) {
    final width = constraints.maxWidth;
    final crossAxisCount = width < 320 ? 1
        : width < 600 ? 2
        : width < 840 ? 3
        : width < 1200 ? 4
        : 5;
    return GridView.builder(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
      ),
      itemBuilder: (ctx, i) => cards[i],
    );
  },
)
```

## 模式 2：列表-详情双栏

使用 `NavigationSplitContainer(mode: NavigationSplitMode.auto)`，自动在 600dp 阈值切换单栏/双栏：

```dart
import 'package:hadss_adaptive_layout/hadss_adaptive_layout.dart';

NavigationSplitContainer(
  mode: NavigationSplitMode.auto,
  navBarWidth: 320,
  navBar: ConversationListPage(
    selectedId: _selectedId,
    onSelect: (id) => setState(() => _selectedId = id),
  ),
  content: _selectedId != null
      ? ChatDetailPage(chatId: _selectedId!)
      : EmptyPlaceholder(),
)
```

- `< 600dp` — 单栏 stack 模式（折叠态手机）
- `≥ 600dp` — 双栏 split 模式（展开态、平板）

## 模式 3：侧边栏导航

```dart
SideBarContainer(
  type: SideBarContainerType.auto,
  sideBar: NavigationMenu(),
  content: _currentPage,
)
```

- `embed` — 侧边栏始终内嵌
- `overlay` — 侧边栏悬浮
- `auto` — 宽屏用 embed，窄屏用 overlay

## 模式 4：栅格布局

```dart
GridRow(
  children: items.map((item) => GridCol(
    span: SpanOption(
      xs: 12,  // 手机全宽
      sm: 6,   // 手机横屏半宽
      md: 4,   // 平板 1/3
      lg: 3,   // 大屏 1/4
      xl: 2,   // 超大屏 1/6
    ),
    child: CardWidget(item),
  )).toList(),
)
```

## 断点映射参考值

| WidthBreakpoint | 宽度范围 | 推荐列数 | 推荐导航模式 |
|----------------|---------|---------|------------|
| xs | < 320dp | 1 | 单栏 |
| sm | 320-600dp | 2 | 单栏 |
| md | 600-840dp | 3 | 双栏 split |
| lg | 840-1440dp | 4 | 双栏 + 侧边栏 |
| xl | > 1440dp | 5-6 | 多栏 |
