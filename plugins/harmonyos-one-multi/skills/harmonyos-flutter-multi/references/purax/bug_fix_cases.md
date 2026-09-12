<!--
Merged from flutter-purax-adaptation/references/ (identical copy also existed in
flutter-pura-x-max-ux-20260731/references/purax/).
Role: deep-dive reference material for foldable scenes PX-01..PX-05; read on demand
via scenarios/foldable-catalog.md. Internal relative links stay valid inside purax/.
Per references/index.md this material is reference-only and never overrides SKILL.md.
-->
# 折展问题修复案例库

- [场景 1：悬停态布局未生效](#场景-1悬停态布局未生效)
- [场景 2：GridView 断点适配失效](#场景-2gridview-断点适配失效)
- [场景 3：铰链遮挡控制栏](#场景-3铰链遮挡控制栏)
- [场景 4：断点切换时布局抖动](#场景-4断点切换时布局抖动)
- [场景 5：开合后连续性断档](#场景-5开合后连续性断档)

---

## 场景 1：悬停态布局未生效

### 问题描述

折叠到半折叠后仍沿用常态单屏布局，关键内容或操作区跨铰链。

典型表现：
- 进入悬停态后，页面仍显示单栏布局，没有分屏展示区与操作区
- 使用 Stack + Positioned 的页面控制栏被铰链遮挡

### 根因分析

- **未使用折叠感知组件**：使用普通 `Stack` 而非 `FolderStack`
- **hardcoded 位置**：`Positioned(bottom: 0)` 固定底部位置，不感知铰链

### 通用修复方案

**Bad case：**

```dart
// ❌ 普通 Stack，无铰链感知
Scaffold(
  body: Stack(
    children: [
      VideoPlayer(_controller),
      Positioned(bottom: 0, child: ControlBar()),
    ],
  ),
)
```

**Good case：**

```dart
// ✅ FolderStack 自动处理铰链避让
import 'package:hadss_avoid_area/hadss_avoid_area.dart';

FolderStack(
  upperItems: ['video_player'],
  children: [
    Container(
      key: const ValueKey('video_player'),
      child: VideoPlayer(_controller),
    ),
    Positioned(bottom: 0, child: ControlBar()),
  ],
)
```

---

## 场景 2：GridView 断点适配失效

### 问题描述

页面在不同屏幕尺寸下 GridView 列数不变。

典型表现：
- 折叠态 2 列正常，展开后仍为 2 列，卡片过大挤压
- 硬编码 `crossAxisCount: 2`

### 根因分析

- `SliverGridDelegateWithFixedCrossAxisCount` 的 `crossAxisCount` 硬编码
- 缺少 `BreakpointManager` 监听，布局不响应窗口变化

### 通用修复方案

**Bad case：**

```dart
// ❌ 硬编码列数
GridView.builder(
  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
    crossAxisCount: 2,
  ),
  itemBuilder: (ctx, i) => ProductCard(products[i]),
)
```

**Good case (hadss)：**

```dart
// ✅ 断点驱动动态列数
class ProductGrid extends StatefulWidget {
  @override
  State<ProductGrid> createState() => _ProductGridState();
}

class _ProductGridState extends State<ProductGrid> {
  int _crossAxisCount = 2;

  @override
  void initState() {
    super.initState();
    _crossAxisCount = _getColumnCount(
      BreakpointManager.instance.currentBreakpoint.widthBreakpoint,
    );
    BreakpointManager.instance.addListener(_onBreakpointChanged);
  }

  @override
  void dispose() {
    BreakpointManager.instance.removeListener(_onBreakpointChanged);
    super.dispose();
  }

  void _onBreakpointChanged(BreakpointData data) {
    setState(() => _crossAxisCount = _getColumnCount(data.widthBreakpoint));
  }

  int _getColumnCount(WidthBreakpoint bp) {
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
      itemBuilder: (ctx, i) => ProductCard(products[i]),
    );
  }
}
```

**Good case (原生 Flutter)：**

```dart
// ✅ LayoutBuilder 响应式列数
LayoutBuilder(
  builder: (context, constraints) {
    final w = constraints.maxWidth;
    final cols = w < 320 ? 1 : w < 600 ? 2 : w < 840 ? 3 : w < 1200 ? 4 : 5;
    return GridView.builder(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: cols,
      ),
      itemBuilder: (ctx, i) => ProductCard(products[i]),
    );
  },
)
```

---

## 场景 3：铰链遮挡控制栏

见 [场景 1：悬停态布局未生效](#场景-1悬停态布局未生效)，根因相同。

---

## 场景 4：断点切换时布局抖动

### 问题描述

折叠/展开时布局出现短暂的错位、空白或内容溢出。

### 根因分析

- 直接监听 `MediaQuery.of(context).size.width` 做防抖不足
- 布局刷新与窗口尺寸变化不同步

### 通用修复方案

- 使用 `BreakpointManager` 而非直接监听 `MediaQuery` 宽度
- `BreakpointManager` 内部已处理防抖和过渡

---

## 场景 5：开合后连续性断档

### 问题描述

折展后滚动位置重置、输入内容丢失、视频播放进度跳变。

### 根因分析

- 折展时 Widget 完全重建，状态未保持
- 缺少跨折展状态快照和恢复机制

### 通用修复方案

见 `references/purax/fold_continuity.md` 的详细方案。

---

## 统一验证矩阵

- **状态维度**：展开、半折叠、折叠三态切换
- **断点维度**：sm → md → lg → sm 全断点覆盖
- **路径维度**：折叠→展开→折叠 与 折叠→悬停→折叠 两条链路
- **连续性维度**：滚动位置、输入内容、播放进度状态一致
- **生命周期维度**：页面进入/退出后无监听残留、无状态串扰
