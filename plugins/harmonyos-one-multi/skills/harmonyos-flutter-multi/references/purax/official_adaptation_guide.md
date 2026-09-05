<!--
Merged from flutter-purax-adaptation/references/ (identical copy also existed in
flutter-pura-x-max-ux-20260731/references/purax/).
Role: deep-dive reference material for foldable scenes PX-01..PX-05; read on demand
via scenarios/foldable-catalog.md. Internal relative links stay valid inside purax/.
Per references/index.md this material is reference-only and never overrides SKILL.md.
-->
# 华为官方 Flutter 多设备适配指导

> 来源：华为开发者论坛官方帖子
> - [Flutter多设备适配开发指导](https://developer.huawei.com/consumer/cn/forum/topic/0208185731429807025)
> - [基于Flutter框架的Pura X Max应用适配指南](https://developer.huawei.com/consumer/cn/forum/topic/0207212776467660482)

## 一、响应式布局核心能力

### 1.1 断点系统

Flutter 断点机制结合 HarmonyOS 平台动态断点能力。在 HarmonyOS 平台下，断点值通过调用 ArkTS 接口直接获取；其他平台根据屏幕宽度计算。

| 断点名称 | 取值范围（px） | 典型设备 |
|---------|-------------|---------|
| xs | [0, 320） | 极小屏 |
| sm | [320, 600) | 手机竖屏 |
| md | [600, 840) | 手机横屏、小平板 |
| lg | [840, 1440) | 平板横屏 |
| xl | [1440, +∞） | 超宽窗口 |

**API 方法表：**

| 方法名 | 参数 | 返回值 | 说明 |
|-------|------|--------|------|
| `init()` | - | `Future<BreakpointData>` | 初始化断点，注册窗口尺寸变化监听 |
| `destroy()` | - | `void` | 销毁监听，清空回调 |
| `addBreakpointCallback` | `Function(BreakpointData)` | `bool` | 添加断点变化回调 |
| `removeBreakpointCallback` | `{Function? callback}` | `bool` | 删除回调（不传删除全部） |
| `setWidthBreakpointRange` | `WidthBreakpointRange` | `void` | 设置横向断点区间 |
| `setHeightBreakpointRange` | `HeightBreakpointRange` | `void` | 设置纵向断点区间 |

**初始化示例（Provider 模式）：**

```dart
void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(ChangeNotifierProvider(
    create: (_) => RouteManager(),
    child: const MyApp(),
  ));
}

class RouteManager extends ChangeNotifier {
  WidthBreakpoint _widthBreakpoint = WidthBreakpoint.unKnow;

  RouteManager() { _initBreakpoint(); }

  Future<void> _initBreakpoint() async {
    final data = await BreakpointManager().init();
    _widthBreakpoint = data.widthBreakpoint;
    BreakpointManager().addBreakpointCallback((data) {
      _widthBreakpoint = data.widthBreakpoint;
      notifyListeners();
    });
  }
}
```

### 1.2 栅格系统（GridRow/GridCol）

对标 ArkUI 的 GridRow/GridCol。12 列栅格，按断点分配列宽。

| 属性 | 说明 | 类型 |
|------|------|------|
| `gridCols` | GridCol 列表 | `List<GridCol>` |
| `columns` | 列数（默认 12） | `int` |
| `gutter` | 列间距（水平+垂直） | `Gutter` |
| `margin` | 相对窗口/父容器的边距 | `EdgeInsetsGeometry` |
| `range` | 断点数列 | `BreakpointRange` |

**典型场景：视频首页推荐影片**

```dart
GridRow(
  gridCols: items.map((item) => GridCol(
    span: SpanOption(xs: 6, sm: 6, md: 4, lg: 3, xl: 3),
    child: MovieCard(item),
  )).toList(),
  columns: 12,
  gutter: const Gutter(x: 10, y: 8),
  range: BreakpointRange(list: [320, 600, 840, 1440, 2000]),
)
```

### 1.3 导航分栏（NavigationSplitContainer）

对标 ArkUI Navigation 组件，支持单栏/双栏自适应切换。

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `navBarWidth` | `double` | 240 | 导航栏宽度 |
| `minContentWidth` | `double` | 360 | 最小主内容区宽度 |
| `navBarWidthRange` | `List<double>` | [240, 432] | 导航栏最小/最大宽度（最大不超过 40% 组件宽度） |
| `mode` | `NavigationSplitMode` | auto | 显示模式：stack/split/auto |
| `navBarPosition` | `NavBarPosition` | start | 导航栏位置 |
| `navigationPane` | `Widget` | - | 左侧导航内容 |
| `mainContent` | `Widget` | - | 主内容区 |
| `onNavBarStateChange` | `Function(bool)` | null | 分栏状态变化回调 |
| `onNavigationModeChange` | `Function(mode)` | null | 单双栏切换回调 |

**典型场景：IM 聊天首页**

```dart
NavigationSplitContainer(
  navBarWidth: 320,
  mode: screenType == WidthBreakpoint.sm
    ? NavigationSplitMode.stack
    : NavigationSplitMode.split,
  navigationPane: ConversationList(),
  mainContent: ChatDetail(),
  onNavBarStateChange: (isVisible) {
    setState(() => navBarIsShow = isVisible);
  },
)
```

### 1.4 自适应显隐（DisplayPriorityBox）

子组件按优先级显隐，空间不足时隐藏低优先级组件。

| 属性 | 类型 | 说明 |
|------|------|------|
| `direction` | `Axis` | 排列方向 |
| `displayPriorityList` | `List<DisplayPriorityObject>` | 优先级对象列表 |
| `mainAxisAlignment` | `MainAxisAlignment` | 主轴对齐 |
| `crossAxisAlignment` | `CrossAxisAlignment` | 交叉轴对齐 |

**典型场景：音乐播放控制栏**

```dart
DisplayPriorityBox(
  direction: Axis.horizontal,
  displayPriorityList: [
    DisplayPriorityObject(displayPriority: 2, child: PreviousButton()),
    DisplayPriorityObject(displayPriority: 2, child: PlayPauseButton()),
    DisplayPriorityObject(displayPriority: 3, child: FavoriteButton()),
    DisplayPriorityObject(displayPriority: 99, child: MoreButton()),
  ],
)
```

## 二、三大典型场景示例

| 场景 | 关键组件 | 适配要点 |
|------|---------|---------|
| **视频首页** | GridRow/GridCol, BreakpointManager | 栅格断点联动、Banner 图片断点切换、底部/侧边页签断点切换 |
| **IM 聊天首页** | NavigationSplitContainer, BreakpointManager | 分栏导航自适应、单栏双栏自动切换 |
| **音乐首页** | DisplayPriorityBox, GridRow/GridCol | 自适应显隐控制、栅格断点列表 |

### 场景 1：视频首页 —— 底部/侧边页签

```dart
Scaffold(
  body: Row(
    children: [
      if (screenType == WidthBreakpoint.lg || screenType == WidthBreakpoint.xl)
        SizedBox(width: 80, child: SideBar()),
      Expanded(child: MainContent()),
    ],
  ),
  bottomNavigationBar: (screenType == WidthBreakpoint.lg || screenType == WidthBreakpoint.xl)
    ? null
    : BottomNavigationBar(...),
)
```

### 场景 2：IM 聊天 —— 顶部页签折行

```dart
if (screenType == WidthBreakpoint.sm || screenType == WidthBreakpoint.xs) {
  return SmallTopBar();  // 折行显示
} else if (screenType == WidthBreakpoint.md) {
  return MediumTopBar();
} else {
  return LargeTopBar();  // 单行显示
}
```

### 场景 3：音乐首页 —— Banner 断点图片

```dart
if (screenType == WidthBreakpoint.sm) {
  return const BannerForSm();
} else if (screenType == WidthBreakpoint.md) {
  return BannerForMd();
}
return BannerForLg();  // 大图
```

## 三、Pura X Max 设备完整适配指南

> 来源：华为开发者论坛官方帖子 [基于Flutter框架的Pura X Max应用适配指南](https://developer.huawei.com/consumer/cn/forum/topic/0207212776467660482)

### 3.1 硬件规格

#### 折叠态屏幕规格

| 旋转角度 | 0° | 90° | 180° | 270° |
|---------|-----|-----|------|------|
| 方向 | 竖屏 PORTRAIT | 横屏 LANDSCAPE | 反向竖屏 | 反向横屏 |
| 分辨率 (px) | 1264×1848 | 1848×1264 | 1264×1848 | 1848×1264 |
| 分辨率 (vp) | **459×672** | **672×459** | 459×672 | 672×459 |
| 横纵断点 | **sm × lg** | md × sm | sm × lg | md × sm |

#### 展开态屏幕规格

| 旋转角度 | 0° | 90° | 180° | 270° |
|---------|-----|-----|------|------|
| 方向 | 竖屏 PORTRAIT | 横屏 LANDSCAPE | 反向竖屏 | 反向横屏 |
| 分辨率 (px) | 1828×2584 | 2584×1828 | 1828×2584 | 2584×1828 |
| 分辨率 (vp) | 664×939 | **939×664** | 664×939 | 939×664 |
| 横纵断点 | md × lg | **lg × sm** | md × lg | lg × sm |

**关键数据：**
- 折叠态展开后宽度从 **459vp** 变为 **939vp**（增加约 2x）
- 折叠态断点组合：sm × lg（**较宽外屏**，宽高比约 0.68）
- 展开态断点组合（横屏）：lg × sm（平板级宽度）
- 外屏 vs 内屏比例：折叠态 10:14，展开态 14:10

### 3.2 折叠状态

| 状态 | FoldStatus | FoldDisplayMode | 说明 |
|------|-----------|----------------|------|
| 折叠态 | `FOLD_STATUS_FOLDED` | `FOLD_DISPLAY_MODE_MAIN` | 仅外屏显示 |
| 悬停态 | `FOLD_STATUS_HALF_FOLDED` | `FOLD_DISPLAY_MODE_FULL` | 半折叠，需折痕避让 |
| 展开态 | `FOLD_STATUS_EXPANDED` | `FOLD_DISPLAY_MODE_FULL` | 内屏全屏 |

### 3.3 相机适配

折叠态和展开态均配置前置+后置相机，镜头安装角度不同：
- 后置镜头安装角度：90°
- 前置镜头安装角度：270°
- 开发相机功能需考虑**摄像头切换**与**预览流重置**。不同折叠状态下可用相机和位置会变化。

### 3.4 窗口适配

#### 全屏模式
应用启动时默认全屏模式。

#### 分屏模式

**折叠态分屏：**

| 分屏方式 | 比例 | 窗口尺寸 (vp) | 断点 |
|---------|------|------------|------|
| 上下 1:1 | 50% | 459×312 | sm × sm |
| 上下 1:2 | 33% | 459×208 | sm × sm |
| 上下 2:1 | 67% | 459×416 | sm × md |

**展开态分屏：**

| 分屏方式 | 比例 | 窗口尺寸 (vp) | 断点 |
|---------|------|------------|------|
| 左右 1:1 | 50% | 465×664 | sm × lg |
| 左右 1.4:1 | 58% | 543×664 | sm × lg |
| 上下 1:1 | 50% | 664×445 | md × sm |
| 上下 2:1 | 67% | 664×593 | md × sm |

#### 悬浮窗模式

| 设备状态 | 类型 | 窗口尺寸 (vp) | 断点 |
|---------|------|------------|------|
| 折叠态 | 纵向 | 459×672 | sm × lg |
| 折叠态 | 横向 | 459×258 | sm × sm |
| 展开态 | 纵向 | 459×750 | sm × lg |
| 展开态 | 横向 | 459×258 | sm × sm |

### 3.5 显示方向

| 设备状态 | 默认旋转策略 | 说明 |
|---------|------------|------|
| 折叠态 | UNSPECIFIED | 仅支持竖屏 PORTRAIT |
| 展开态 | AUTO_ROTATION_RESTRICTED | 支持四个方向旋转（竖屏/横屏/反向竖屏/反向横屏） |

**推荐逻辑：** 展开态界面推荐支持横竖屏自动旋转，以提供更灵活的使用体验。

### 3.6 沉浸式与避让区

Pura X Max 的避让区在以下场景会发生变化：
- 窗口模式切换（全屏/悬浮窗/分屏）
- 窗口方向变化（横竖屏切换）
- 折叠屏状态切换（展开/折叠）

### 3.7 典型布局模式

| 布局模式 | 典型场景 | 实现方案 |
|---------|---------|---------|
| **重复布局** | 列表、瀑布流、轮播、网格 | flex + 断点、staggered_grid_view + 断点、PageView + 断点、grid + 断点 |
| **分栏布局** | 侧边栏、单/双栏 | CustomScrollView + 断点、Column + 断点 |
| **挪移布局** | 图文组合、底部/侧边导航 | Flex + 断点 |
| **缩进布局** | 大屏居中单列列表 | Center + 断点 |

### 3.8 悬停态适配

Pura X Max 展开态时，悬停态可在桌面平稳放置。这种状态下：
- 需要对**中间折痕区域进行避让**
- 对**上下两个界面进行悬停适配**，重新布局
- 适用于视频通话、播放视频、拍照和听歌等不需要频繁交互的场景

### 3.9 常见问题

**Q1: 如何区分 Pura X Max 外屏与直板机？**
- 问题：两者处于同一断点区间（横向 sm + 纵向 lg）
- 方案：额外判断宽高比是否大于 **9/18**（即 0.5），大于则为 Pura X Max 宽外屏

**Q2: 如何实现不同折叠状态下的页面布局？**
- 方案：推荐使用**断点**进行页面布局的适配。根据 UX 设计，在不同断点下开发不同页面布局，实现方法参考通过断点刷新 UI。

## 四、示例代码地址

- [adaptive_layout_sample](https://gitcode.com/openharmony-sig/flutter_multidevice_layout_scenepkg/tree/master/samples/adaptive_layout_sample)
- [Flutter 多设备适配完整方案库](https://gitcode.com/openharmony-sig/flutter_multidevice_layout_scenepkg)
