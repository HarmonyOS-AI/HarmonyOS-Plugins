<!--
Merged from flutter-purax-adaptation/references/ (identical copy also existed in
flutter-pura-x-max-ux-20260731/references/purax/).
Role: deep-dive reference material for foldable scenes PX-01..PX-05; read on demand
via scenarios/foldable-catalog.md. Internal relative links stay valid inside purax/.
Per references/index.md this material is reference-only and never overrides SKILL.md.
-->
# 折叠状态与断点检测指南

## 目标

使用 `hadss_adaptive_layout` 的 `BreakpointManager` 和 `hadss_avoid_area` 的 `AvoidAreaApi` 完成折叠状态、断点和安全区域的统一检测，作为 Flutter 折展页面的统一入口。

## 常用 API

### BreakpointManager (断点管理)

```dart
import 'package:hadss_adaptive_layout/hadss_adaptive_layout.dart';

// 获取当前断点
final bp = BreakpointManager.instance.currentBreakpoint;
// bp.widthBreakpoint → WidthBreakpoint.xs/sm/md/lg/xl
// bp.heightBreakpoint → HeightBreakpoint.sm/md/lg
// bp.width → 当前窗口宽度(dp)
// bp.height → 当前窗口高度(dp)

// 监听断点变化
BreakpointManager.instance.addListener((BreakpointData data) {
  setState(() {
    _currentWidthBreakpoint = data.widthBreakpoint;
  });
});

// 取消监听
BreakpointManager.instance.removeListener(_onBreakpointChanged);
```

### AvoidAreaApi (安全区域/折叠状态)

```dart
import 'package:hadss_avoid_area/hadss_avoid_area.dart';

// 获取窗口安全区域
final avoidArea = await AvoidAreaApi.getWindowAvoidArea();
// avoidArea.top → 顶部安全区高度（状态栏+刘海）
// avoidArea.bottom → 底部安全区（导航栏+手势条）
// avoidArea.left / avoidArea.right

// 监听安全区域变化
AvoidAreaApi.addAvoidAreaListener((AvoidArea avoidArea) {
  // 处理状态变化
});

AvoidAreaApi.removeAvoidAreaListener(_onAvoidAreaChanged);
```

## 断点体系

### 宽度断点

| 断点 | 范围 (dp) | 典型设备 |
|------|----------|---------|
| xs | < 320 | 极小屏 |
| sm | 320 - 600 | 手机竖屏、PuraX 折叠态外屏 |
| md | 600 - 840 | 手机横屏、PuraX 展开态、小平板 |
| lg | 840 - 1440 | 平板横屏、PuraX 桌面模式 |
| xl | > 1440 | 超宽窗口 |

### 高度断点

| 断点 | 范围 (dp) |
|------|----------|
| sm | 0 - 480 |
| md | 480 - 840 |
| lg | > 840 |

## 最小代码骨架

```dart
import 'package:flutter/material.dart';
import 'package:hadss_adaptive_layout/hadss_adaptive_layout.dart';

class AdaptivePage extends StatefulWidget {
  const AdaptivePage({super.key});
  @override
  State<AdaptivePage> createState() => _AdaptivePageState();
}

class _AdaptivePageState extends State<AdaptivePage> {
  WidthBreakpoint _widthBreakpoint = WidthBreakpoint.sm;
  int _crossAxisCount = 2;

  @override
  void initState() {
    super.initState();
    _widthBreakpoint = BreakpointManager.instance
        .currentBreakpoint.widthBreakpoint;
    _crossAxisCount = _mapBreakpointToColumns(_widthBreakpoint);
    BreakpointManager.instance.addListener(_onBreakpointChanged);
  }

  @override
  void dispose() {
    BreakpointManager.instance.removeListener(_onBreakpointChanged);
    super.dispose();
  }

  void _onBreakpointChanged(BreakpointData data) {
    final count = _mapBreakpointToColumns(data.widthBreakpoint);
    if (count != _crossAxisCount) {
      setState(() {
        _widthBreakpoint = data.widthBreakpoint;
        _crossAxisCount = count;
      });
    }
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
        childAspectRatio: 0.75,
      ),
      itemBuilder: (ctx, i) => _cards[i],
    );
  }
}
```

## 使用场景

| 场景 | 触发条件 | 推荐用法 | 为什么要判断 | 不判断的风险 |
| --- | --- | --- | --- | --- |
| 首次渲染布局决策 | 页面首次渲染前需决定断点分支 | `BreakpointManager.instance.currentBreakpoint` | 避免首帧先渲染错误布局再闪切 | 首帧抖动、结构跳变 |
| 折展过程中实时刷新 | 用户正在折/展开设备 | `BreakpointManager.instance.addListener(...)` | 状态会动态变化，需事件驱动刷新 | 布局滞后，内容跨铰链 |
| 半折叠状态感知 | 页面有"上内容下操作"等悬停结构 | `AvoidAreaApi.addAvoidAreaListener(...)` | 仅在半折叠态切到悬停布局 | 展开态误入悬停分支 |
| 页面退出清理监听 | 页面销毁或路由离开 | `removeListener` / `removeAvoidAreaListener` | 监听生命周期需与页面一致 | 监听残留、状态串扰、性能下降 |

## 约束

- 通用响应式布局优先使用窗口尺寸与断点；折叠状态用于折叠特性分支，不作为全局布局唯一决策条件。
- 监听必须在 `dispose()` 中取消，避免内存泄漏和状态串扰。

## 原生 Flutter 替代方案

当项目未引入 hadss 库时：

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
      itemBuilder: (ctx, i) => _cards[i],
    );
  },
)
```
